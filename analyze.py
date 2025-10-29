# %%
import pickle
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# I/O paths (read from previous step outputs if present)
out_dir = Path("/mnt/data/sota_history")
summary_csv = out_dir / "sota_sessions_summary.csv"
added_csv = out_dir / "sota_added_features_by_session.csv"

# If not present, try artifacts fallback (in case user ran locally with different path)
if not summary_csv.exists():
    alt = Path("artifacts/sota_history/sota_sessions_summary.csv")
    if alt.exists():
        summary_csv = alt
if not added_csv.exists():
    alt = Path("artifacts/sota_history/sota_added_features_by_session.csv")
    if alt.exists():
        added_csv = alt

# Load
df = pd.read_csv(summary_csv) if summary_csv.exists() else pd.DataFrame()
df_added = pd.read_csv(added_csv) if added_csv.exists() else pd.DataFrame()

# Ensure lists if they were saved as strings
def _safe_eval_list(x):
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        # crude parse for list-like string
        x = x.strip()
        if x.startswith('[') and x.endswith(']'):
            try:
                import ast
                v = ast.literal_eval(x)
                return v if isinstance(v, list) else []
            except Exception:
                return []
    return []

if not df_added.empty and "added_features" in df_added.columns:
    df_added["added_features"] = df_added["added_features"].apply(_safe_eval_list)

# Sort by session if present
if not df.empty and "session" in df.columns:
    df = df.sort_values("session")
if not df_added.empty and "session" in df_added.columns:
    df_added = df_added.sort_values("session")

# --- Build combined plot with cumulative features + IR + annualized return ---
plt.close("all")
fig, ax_left = plt.subplots()

if not df_added.empty:
    # Left y-axis: cumulative number of features
    x = df_added["session"].tolist()
    y_feat = df_added["n_factors"].tolist()
    ax_left.step(x, y_feat, where="post", label="Feature count")
    ax_left.scatter(x, y_feat)
    ax_left.set_xlabel("Session Index")
    ax_left.set_ylabel("Number of Features")
    ax_left.set_title("SOTA Update Path: Cumulative Features + IR & Annualized Return")

    # Light annotations: only annotate when <= 2 adds, else "+N"
    for _, r in df_added.iterrows():
        adds = r["added_features"] if "added_features" in r else []
        if isinstance(adds, float):  # NaN guard
            continue
        if len(adds) == 0:
            continue
        label = f"+{len(adds)}" if len(adds) > 2 else "+ " + ", ".join(adds)
        ax_left.annotate(label, (r["session"], r["n_factors"]),
                         xytext=(5, 6), textcoords="offset points", fontsize=8, rotation=15)

# Right y-axis: IR & Annualized Return (with/without cost)
ax_right = ax_left.twinx()

if not df.empty:
    # Columns may or may not exist depending on pipeline; guard each one
    col_ir_wc = "1day.excess_return_with_cost.information_ratio"
    col_ir_wo = "1day.excess_return_without_cost.information_ratio"
    col_ann_wc = "1day.excess_return_with_cost.annualized_return"
    col_ann_wo = "1day.excess_return_without_cost.annualized_return"

    # Align by session index
    sessions = df["session"] if "session" in df.columns else range(len(df))

    plotted_any = False
    if col_ir_wc in df.columns:
        ax_right.plot(sessions, df[col_ir_wc], marker="o", linestyle="-", label="IR (with cost)")
        plotted_any = True
    if col_ir_wo in df.columns:
        ax_right.plot(sessions, df[col_ir_wo], marker="o", linestyle="--", label="IR (w/o cost)")
        plotted_any = True
    if col_ann_wc in df.columns:
        ax_right.plot(sessions, df[col_ann_wc], marker="s", linestyle="-.", label="Annualized Return (with cost)")
        plotted_any = True
    if col_ann_wo in df.columns:
        ax_right.plot(sessions, df[col_ann_wo], marker="s", linestyle=":", label="Annualized Return (w/o cost)")
        plotted_any = True

    if plotted_any:
        ax_right.set_ylabel("IR / Annualized Return")
        # Build a single legend combining both axes
        lines_l, labels_l = ax_left.get_legend_handles_labels()
        lines_r, labels_r = ax_right.get_legend_handles_labels()
        ax_right.legend(lines_l + lines_r, labels_l + labels_r, loc="best")

# Improve spacing
fig.tight_layout()

plot_path = out_dir / "sota_update_with_ir_and_return.png"
# If out_dir doesn't exist (e.g., using artifacts path), fall back
if not out_dir.exists():
    out_dir.mkdir(parents=True, exist_ok=True)
fig.savefig(plot_path, dpi=150)
plt.show()

plot_path