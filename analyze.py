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

# === 6) Plot update path ===
plt.close("all")
fig = plt.figure(constrained_layout=True)
if not df_added.empty:
    x = df_added["session"].tolist()
    y = df_added["n_factors"].tolist()
    plt.step(x, y, where="post")
    plt.scatter(x, y)
    # 为了避免文字过多挤不下：仅在有新增且新增条目<=3时标注，更多就省略为“+N”
    for _, r in df_added.iterrows():
        s = r["session"]; adds = r["added_features"]
        if adds:
            label = f"+{len(adds)}" if len(adds) > 3 else "+ " + ", ".join(adds)
            plt.annotate(label, (s, r["n_factors"]), xytext=(5, 5), textcoords="offset points", fontsize=8)
    plt.title("SOTA Update Path: Cumulative Feature Count by Session")
    plt.xlabel("Session Index"); plt.ylabel("Number of Features")
else:
    plt.title("SOTA Update Path: No sessions parsed (no SOTA experiments found)")
    plt.xlabel("Session Index"); plt.ylabel("Number of Features")
    plt.text(0.5, 0.5, "No SOTA data available under the base path.", ha="center")

plot_path = out_dir / "sota_update_path.png"
plt.savefig(plot_path, dpi=150)
plt.show()

# Expose artifact paths
(summary_csv, added_csv, plot_path)