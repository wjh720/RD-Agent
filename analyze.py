# %%
import pickle
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pandas as pd
import matplotlib.pyplot as plt

exp_name = "2025-10-29_01-12-54-858255"
# === 1) Config ===
BASE = Path(f"log/{exp_name}/__session__")
SESSION_RANGE = range(0, 16)  # 0..15 inclusive
out_dir = Path(f"artifacts/sota_history/{exp_name}")

# 常见的落盘相对路径（逐一尝试，找到就用）
CANDIDATE_REL_PATHS = [
    "0_direct_exp_gen",        # e.g. __session__/15/0_direct_exp_gen
    "0/0_direct_exp_gen",      # e.g. __session__/15/0/0_direct_exp_gen
    "1/0_direct_exp_gen",      # 兼容其他流水线
    "exp/0_direct_exp_gen",    # 兼容其他流水线
]

# === 2) Helpers ===
def try_load_session_pickle(session_dir: Path) -> Tuple[Path, Any]:
    for rel in CANDIDATE_REL_PATHS:
        p = session_dir / rel
        if p.exists() and p.is_file():
            try:
                with open(p, "rb") as f:
                    return p, pickle.load(f)
            except Exception:
                pass
    return None, None

def extract_sota(data_obj) -> Tuple[Any, Any]:
    if not hasattr(data_obj, "trace"):
        return None, None
    try:
        return data_obj.trace.get_sota_hypothesis_and_experiment()
    except Exception:
        return None, None

def factors_from_experiment(exp_obj) -> List[Dict[str, Any]]:
    out = []
    if not hasattr(exp_obj, "sub_tasks") or exp_obj.sub_tasks is None:
        return out
    for st in exp_obj.sub_tasks:
        name = getattr(st, "factor_name", getattr(st, "name", None))
        form = getattr(st, "factor_formulation", None)
        out.append({"factor_name": name, "factor_formulation": form})
    return out

# === 3) Scan sessions, collect ONLY those with SOTA (skip the rest silently) ===
records = []
session_feature_sets = {}

if BASE.exists():
    for s in SESSION_RANGE:
        session_dir = BASE / str(s)
        if not session_dir.exists():
            continue
        p, obj = try_load_session_pickle(session_dir)
        if obj is None:
            continue

        hypo, exp = extract_sota(obj)
        if exp is None:
            # 直接跳过，没有 SOTA experiment 的 session
            continue

        # Result metrics（Series / dict / namespace 都兼容）
        result = getattr(exp, "result", None)
        result_series = None
        if result is not None:
            try:
                if isinstance(result, pd.Series):
                    result_series = result
                elif isinstance(result, dict):
                    result_series = pd.Series(result)
                else:
                    result_series = pd.Series(getattr(result, "__dict__", {}))
            except Exception:
                result_series = None

        # 当前因子
        curr_factors = factors_from_experiment(exp)
        curr_factor_names = [f["factor_name"] for f in curr_factors if f["factor_name"] is not None]
        session_feature_sets[s] = set(curr_factor_names)

        # 依赖链（如果有）
        based = getattr(exp, "based_experiments", []) or []
        based_info = []
        for b in based:
            b_factors = factors_from_experiment(b)
            b_names = [f["factor_name"] for f in b_factors if f["factor_name"] is not None]
            based_info.append({"n_factors": len(b_names), "factors": b_names})

        row = {
            "session": s,
            "pickle_path": str(p) if p else None,
            "n_factors": len(curr_factor_names),
            "factors": curr_factor_names,
            "based_chain_len": len(based_info),
            "based_chain": based_info,
        }
        if result_series is not None:
            for k, v in result_series.items():
                row[str(k)] = v
        records.append(row)

# === 4) DataFrames ===
df = pd.DataFrame(records).sort_values("session").reset_index(drop=True) if records else \
     pd.DataFrame(columns=["session","pickle_path","n_factors","factors","based_chain_len","based_chain"])

# 相邻 session 的 add/remove 统计
added_rows = []
prev_set = set()
for s in sorted(session_feature_sets.keys()):
    cur = session_feature_sets[s]
    added = sorted(cur - prev_set)
    removed = sorted(prev_set - cur)
    added_rows.append({
        "session": s,
        "n_factors": len(cur),
        "added_features": added,
        "removed_features": removed,
    })
    prev_set = cur

df_added = pd.DataFrame(added_rows) if added_rows else \
           pd.DataFrame(columns=["session","n_factors","added_features","removed_features"])

# === 5) Save artifacts ===
out_dir.mkdir(parents=True, exist_ok=True)
summary_csv = out_dir / "sota_sessions_summary.csv"
added_csv = out_dir / "sota_added_features_by_session.csv"
df.to_csv(summary_csv, index=False)
df_added.to_csv(added_csv, index=False)

# === 6A) IR & Annualized Return（双轴） ===
plt.close("all")
figA, ax1 = plt.subplots(figsize=(12, 6))

plotted = False
if not df.empty:
    # 排序并取横轴
    if "session" in df.columns:
        df = df.sort_values("session")
        x = df["session"].tolist()
    else:
        x = list(range(len(df)))

    # 左轴：IR
    col_ir_wc = "1day.excess_return_with_cost.information_ratio"
    col_ir_wo = "1day.excess_return_without_cost.information_ratio"
    if col_ir_wc in df.columns:
        ax1.plot(x, df[col_ir_wc], marker="o", linestyle="-", label="IR (with cost)")
        plotted = True
    if col_ir_wo in df.columns:
        ax1.plot(x, df[col_ir_wo], marker="o", linestyle="--", label="IR (w/o cost)")
        plotted = True

ax1.set_xlabel("Session Index")
ax1.set_ylabel("Information Ratio")

# 右轴：年化收益
ax2 = ax1.twinx()
col_ann_wc = "1day.excess_return_with_cost.annualized_return"
col_ann_wo = "1day.excess_return_without_cost.annualized_return"
if not df.empty:
    if col_ann_wc in df.columns:
        ax2.plot(x, df[col_ann_wc], marker="s", linestyle="-.", label="Ann. Ret (with cost)")
        plotted = True
    if col_ann_wo in df.columns:
        ax2.plot(x, df[col_ann_wo], marker="s", linestyle=":", label="Ann. Ret (w/o cost)")
        plotted = True
ax2.set_ylabel("Annualized Return")

if plotted:
    # 合并两个坐标轴的图例
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc="best")
    ax1.set_title("SOTA Metrics by Session: IR & Annualized Return")
else:
    ax1.set_title("SOTA Metrics: no data")

figA.tight_layout()
figA_path = out_dir / "figure_metrics_ir_return.png"
figA.savefig(figA_path, dpi=150, bbox_inches="tight")


# === 6B) 累计特征数（仅标注 +N，详细名单放表里） ===
plt.close("all")
figB, ax = plt.subplots(figsize=(14, 4))

if not df_added.empty:
    df_added = df_added.sort_values("session")
    x2 = df_added["session"].tolist()
    y2 = df_added["n_factors"].tolist()

    ax.step(x2, y2, where="post", label="Feature count")
    ax.scatter(x2, y2, s=25)

    # 仅显示 +N，避免文字遮挡；详细新增名单请在表格中查看
    for _, r in df_added.iterrows():
        adds = r.get("added_features", [])
        if isinstance(adds, float):  # 兼容 NaN
            continue
        n = len(adds) if isinstance(adds, list) else 0
        if n > 0:
            ax.annotate(f"+{n}", (r["session"], r["n_factors"]),
                        xytext=(4, 6), textcoords="offset points", fontsize=8)

    ax.set_xlabel("Session Index")
    ax.set_ylabel("Number of Features")
    ax.set_title("SOTA Update Path: Cumulative Feature Count (labels show +N added)")
    ax.legend(loc="best")
else:
    ax.set_title("SOTA Update Path: no data")
    ax.set_xlabel("Session Index")
    ax.set_ylabel("Number of Features")

figB.tight_layout()
figB_path = out_dir / "figure_feature_count.png"
figB.savefig(figB_path, dpi=150, bbox_inches="tight")