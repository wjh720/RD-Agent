# %%
import pickle
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pandas as pd
import matplotlib.pyplot as plt
from loguru import logger
import ast
from collections import OrderedDict
import json

exp_name = "2025-10-29_01-12-54-858255"
# === 1) Config ===
PICKLE_NAME = "0_direct_exp_gen"   # 仅此一种
BASE = Path(f"log/{exp_name}/__session__")
out_dir = Path(f"artifacts/sota_history/{exp_name}")

# === 2) Helpers ===
def try_load_session_pickle(session_dir: Path) -> Tuple[Path, Any]:
    p = session_dir / PICKLE_NAME
    if p.exists() and p.is_file():
        try:
            with open(p, "rb") as f:
                return p, pickle.load(f)
        except Exception:
            pass
    return None, None

def discover_sessions(base: Path) -> list[int]:
    """仅收集存在 0_direct_exp_gen 的数字目录"""
    sessions = []
    if not base.exists():
        return sessions
    for d in base.iterdir():
        if not d.is_dir():
            continue
        try:
            sidx = int(d.name)
        except ValueError:
            continue
        if (d / PICKLE_NAME).exists():
            sessions.append(sidx)
    sessions.sort()
    return sessions

# === 动态发现 sessions ===
SESSION_RANGE = discover_sessions(BASE)
logger.info(f"Discovered sessions: {SESSION_RANGE}")

# === 2) Helpers ===
def try_load_session_pickle(session_dir: Path) -> Tuple[Path, Any]:
    p = session_dir / PICKLE_NAME
    if p.exists() and p.is_file():
        try:
            with open(p, "rb") as f:
                return p, pickle.load(f)
        except Exception:
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

def collect_full_factors_with_order(exp_obj):
    """
    沿 lineage 以 DFS 顺序返回“去重后的有序列表”：
    先 based_experiments（祖先，按出现顺序），再当前 sub_tasks。
    返回: List[{"factor_name": str, "factor_formulation": str}]
    """
    out = []
    seen = set()

    def _visit(e):
        # 先祖先
        for b in getattr(e, "based_experiments", []) or []:
            _visit(b)
        # 后当前
        for st in getattr(e, "sub_tasks", []) or []:
            name = getattr(st, "factor_name", getattr(st, "name", None))
            form = getattr(st, "factor_formulation", None)
            if name is not None and name not in seen:
                seen.add(name)
                out.append({"factor_name": name, "factor_formulation": form})
    _visit(exp_obj)
    return out  # 顺序 = lineage 的首次出现顺序

# 遍历 __session__ 计算“首次加入顺序”
added_in_order = []   # 全局新增顺序列表
added_set = set()     # 全局已加入集合，防止重复
first_sess_of = {}    # factor -> 首次出现的 session
form_when_added = {}  # factor -> 首次出现时的公式

sessions_with_sota = []
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
            continue
        sessions_with_sota.append(s)

        seq = collect_full_factors_with_order(exp)  # 本 session 的完整有序去重列表
        for item in seq:
            name = item["factor_name"]
            form = item["factor_formulation"]
            if name not in added_set:
                # 这个特征第一次出现在整个路线中
                added_set.add(name)
                first_sess_of[name] = s
                form_when_added[name] = form
                added_in_order.append({
                    "order": len(added_in_order) + 1,   # 全局加入顺序编号
                    "session_first_added": s,
                    "factor_name": name,
                    "factor_formulation": form
                })

# 落盘：按加入先后顺序输出
df_added_order = pd.DataFrame(added_in_order).sort_values("order").reset_index(drop=True)
add_order_csv  = out_dir / "sota_feature_add_order.csv"
add_order_json = out_dir / "sota_feature_add_order.json"
df_added_order.to_csv(add_order_csv, index=False, encoding="utf-8")
with open(add_order_json, "w", encoding="utf-8") as f:
    json.dump(added_in_order, f, ensure_ascii=False, indent=2)

logger.info(f"Saved (add order): {add_order_csv}")
logger.info(f"Saved (add order): {add_order_json}")

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

def _to_list(x):
    if isinstance(x, list):
        return x
    if isinstance(x, str) and x.startswith('['):
        try:
            return ast.literal_eval(x)
        except Exception:
            return []
    return []

def _to_based_chain_factors(x):
    """
    x 形如 '[{"n_factors": 3, "factors": ["a","b","c"]}, ...]'（CSV 中的字符串）
    解析后提取所有 'factors' 并拼成一个列表
    """
    vals = []
    if isinstance(x, list):
        it = x
    elif isinstance(x, str) and x.startswith('['):
        try:
            it = ast.literal_eval(x)
        except Exception:
            it = []
    else:
        it = []
    for d in it:
        if isinstance(d, dict) and "factors" in d and isinstance(d["factors"], list):
            vals.extend(d["factors"])
    return vals

plt.close("all")
figB, ax = plt.subplots(figsize=(14, 4))

if not df.empty:
    # 按 session 排序
    if "session" in df.columns:
        df_plot = df.sort_values("session").copy()
    else:
        # 没有 session 列就按行序
        df_plot = df.copy()
        df_plot["session"] = range(len(df_plot))

    cum = set()
    x2, y2, add_counts, added_lists = [], [], [], []

    for _, r in df_plot.iterrows():
        sess = int(r["session"])
        cur_factors = set(_to_list(r.get("factors", [])))
        chain_factors = set(_to_based_chain_factors(r.get("based_chain", "[]")))
        full = cur_factors | chain_factors        # 这一期 SOTA 的“完整特征集合”

        added = sorted(full - cum)
        removed = sorted(cum - full)              # 一般不会频繁出现，有就会扣减
        cum = full

        x2.append(sess)
        y2.append(len(cum))
        add_counts.append(len(added))
        added_lists.append(added)

    # 画图
    ax.step(x2, y2, where="post", label="Feature count")
    ax.scatter(x2, y2, s=25)

    # 仅标注 +N（避免拥挤）；如需具体名称，可把 added_lists[i] 打印到表格
    for sess, yv, n in zip(x2, y2, add_counts):
        if n > 0:
            ax.annotate(f"+{n}", (sess, yv), xytext=(4, 6),
                        textcoords="offset points", fontsize=8)

    ax.set_xlabel("Session Index")
    ax.set_ylabel("Number of Features")
    ax.set_title("SOTA Update Path: Cumulative Feature Count (reconstructed from lineage)")
    ax.legend(loc="best")

else:
    ax.set_title("SOTA Update Path: no data")
    ax.set_xlabel("Session Index")
    ax.set_ylabel("Number of Features")

figB.tight_layout()
figB_path = out_dir / "figure_feature_count.png"
figB.savefig(figB_path, dpi=150, bbox_inches="tight")

###
logger.info(f"Artifacts saved to {out_dir.resolve()}")