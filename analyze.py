import os
import pickle
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pandas as pd
import matplotlib.pyplot as plt

# === 1) Config ===
BASE = Path("log/2025-10-29_01-12-54-858255/__session__")
SESSION_RANGE = range(0, 16)  # 0..15
CANDIDATE_REL_PATH = "0_direct_exp_gen"

# === 2) Helpers ===
def load_pickle_any(path: Path) -> Any:
    with open(path, "rb") as f:
        return pickle.load(f)

def try_load_session_pickle(session_dir: Path) -> Tuple[Path, Any]:
    p = session_dir / CANDIDATE_REL_PATH
    if p.exists() and p.is_file():
        try:
            obj = load_pickle_any(p)
            return p, obj
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

# === 3) Scan sessions, collect SOTA results + factors ===
records = []
session_feature_sets = {}
errors = []

if BASE.exists():
    for s in SESSION_RANGE:
        session_dir = BASE / str(s)
        if not session_dir.exists():
            errors.append(f"Session {s} missing dir: {session_dir}")
            continue
        p, obj = try_load_session_pickle(session_dir)
        if obj is None:
            errors.append(f"Session {s} missing pickle under {session_dir}")
            continue

        hypo, exp = extract_sota(obj)
        if exp is None:
            errors.append(f"Session {s} has no SOTA experiment")
            continue

        # Result metrics
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

        # Current factors
        curr_factors = factors_from_experiment(exp)
        curr_factor_names = [f["factor_name"] for f in curr_factors if f["factor_name"] is not None]
        session_feature_sets[s] = set(curr_factor_names)

        # Based chain (lineage)
        based = getattr(exp, "based_experiments", [])
        based_info = []
        for b in (based or []):
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
else:
    errors.append(f"Base path not found: {BASE}")

# === 4) DataFrames ===
df = pd.DataFrame(records).sort_values("session").reset_index(drop=True) if records else \
     pd.DataFrame(columns=["session","pickle_path","n_factors","factors","based_chain_len","based_chain"])

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
out_dir = Path("artifacts/sota_history")
out_dir.mkdir(parents=True, exist_ok=True)
df.to_csv(out_dir / "sota_sessions_summary.csv", index=False)
df_added.to_csv(out_dir / "sota_added_features_by_session.csv", index=False)

# === 6) Plot update path ===
plt.figure()
if not df_added.empty:
    x = df_added["session"].tolist()
    y = df_added["n_factors"].tolist()
    plt.step(x, y, where="post")
    plt.scatter(x, y)
    for _, r in df_added.iterrows():
        s = r["session"]; adds = r["added_features"]
        if adds:
            label = "+ " + ", ".join(adds)
            plt.annotate(label, (s, r["n_factors"]), xytext=(5, 5), textcoords="offset points", fontsize=8)
    plt.title("SOTA Update Path: Cumulative Feature Count by Session")
    plt.xlabel("Session Index"); plt.ylabel("Number of Features")
else:
    plt.title("SOTA Update Path: No sessions parsed")
    plt.xlabel("Session Index"); plt.ylabel("Number of Features")
    plt.text(0.5, 0.5, "No SOTA data found under the base path.", ha="center")
plt.tight_layout()
plt.savefig(out_dir / "sota_update_path.png", dpi=150)
plt.show()

print("Saved to:", out_dir)
print("Errors (if any):", errors[:10])