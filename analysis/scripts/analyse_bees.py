#!/usr/bin/env python3
"""
Bumblebee Path Integration Analysis
====================================
Reproduces figures from: Marie Jansen (2025) Bachelor's Thesis
Based on experimental design from: Patel et al. (2022)

Arena calibration:
  Inner circle diameter: 42 cm  → radius 21 cm  (feeder zone)
  Outer circle diameter: 84 cm  → radius 42 cm  (search zone)

Coordinate system after centering: origin = arena centre (feeder location)
"""

import re
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from matplotlib.patches import Circle, FancyArrowPatch
from matplotlib.gridspec import GridSpec
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy import stats
from pathlib import Path

warnings.filterwarnings("ignore")
matplotlib.use("Agg")

# ─────────────────── paths ────────────────────────────────────────────────────
V_OUTPUTS   = Path("/Users/yakkshit/Downloads/project/hiwi2/p1/V_OUTPUTS")
CACHE_PATH  = Path("/Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee_task/circle_config_cache.json")
RESULTS_DIR = Path("/Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee_task/analysis/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────── constants ────────────────────────────────────────────────
INNER_R_CM   = 21.0   # radius (inner circle = 42 cm diameter)
OUTER_R_CM   = 42.0   # radius (outer circle = 84 cm diameter)
CM_PER_PIXEL = 0.1546 # default calibration

# ─────────────────── style ────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.frameon": False,
    "legend.fontsize": 9,
    "figure.dpi": 150,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})

COND_COLORS = {
    "LR_low_P":  "#2196F3",  # blue
    "LR_high_P": "#0D47A1",  # dark blue
    "TB_low_P":  "#F44336",  # red
    "TB_high_P": "#B71C1C",  # dark red
    "unknown":   "#9E9E9E",  # grey
}

# ─────────────────── helpers ──────────────────────────────────────────────────

def load_cache():
    if CACHE_PATH.exists():
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}

def parse_folder_name(name: str) -> dict:
    """
    Extract metadata from folder name like:
      '2024-11-17 17-04-16.R13.LR.P0U8'
      '2025-02-27 17-35-32.W 36 LR P 0 U 8'
    Returns dict with keys: datetime_key, bee_id, cue, P_pollen, U_uncert
    """
    n = name.strip()
    # datetime key = first 19 chars (YYYY-MM-DD HH-MM-SS)
    dt_key = n[:19]

    # cue direction
    cue = None
    if re.search(r'\bLR\b', n, re.I):
        cue = "LR"
    elif re.search(r'\bTB\b', n, re.I):
        cue = "TB"

    # pollen amount P
    p_match = re.search(r'P\s*([0-9]+(?:\.[0-9]+)?)', n, re.I)
    P = float(p_match.group(1)) if p_match else np.nan

    # uncertainty U
    u_match = re.search(r'U\s*([0-9]+(?:\.[0-9]+)?)', n, re.I)
    U = float(u_match.group(1)) if u_match else np.nan

    # bee id (first word-like token after the datetime)
    remainder = n[20:].strip()
    bee_match = re.search(r'([RWGrwg]\s*\d+)', remainder)
    bee_id = bee_match.group(1).replace(" ", "") if bee_match else "unknown"

    return dict(dt_key=dt_key, bee_id=bee_id, cue=cue, P=P, U=U)


def get_center_cm(dt_key: str, cache: dict) -> tuple[float, float] | None:
    """Look up arena centre (pixels) from cache, convert to cm."""
    for k in [dt_key, dt_key + ".mp4", dt_key + ".mkv"]:
        if k in cache:
            cx_px, cy_px = cache[k]
            return cx_px * CM_PER_PIXEL, cy_px * CM_PER_PIXEL
    return None


def load_tracking(id0_file: Path, cx_cm: float, cy_cm: float) -> pd.DataFrame | None:
    """Load and centre trajectory from id0_new CSV."""
    try:
        df = pd.read_csv(id0_file, low_memory=False)
        x_col = next((c for c in ["X (cm)", "X#wcentroid (cm)"] if c in df.columns), None)
        y_col = next((c for c in ["Y (cm)", "Y#wcentroid (cm)"] if c in df.columns), None)
        if x_col is None or y_col is None:
            return None

        valid = df[
            (df["missing"] == 0) &
            np.isfinite(df[x_col]) &
            np.isfinite(df[y_col])
        ].copy()

        if valid.empty:
            return None

        valid["x"] = valid[x_col] - cx_cm
        valid["y"] = valid[y_col] - cy_cm
        valid["r"] = np.sqrt(valid["x"]**2 + valid["y"]**2)

        # speed
        if "SPEED (cm/s)" in valid.columns:
            valid["speed"] = valid["SPEED (cm/s)"].clip(0, 50)  # cap at 50 cm/s
        elif "SPEED#pcentroid (cm/s)" in valid.columns:
            valid["speed"] = valid["SPEED#pcentroid (cm/s)"].clip(0, 50)
        else:
            valid["speed"] = np.nan

        return valid.reset_index(drop=True)
    except Exception as e:
        return None


def load_events(events_file: Path) -> pd.DataFrame | None:
    try:
        df = pd.read_csv(events_file)
        return df if not df.empty else None
    except Exception:
        return None


def circular_mean_r(angles_deg: np.ndarray) -> tuple[float, float]:
    """Return (mean_angle_deg, mean_vector_length R) for array of angles."""
    rad = np.radians(angles_deg)
    s = np.mean(np.sin(rad))
    c = np.mean(np.cos(rad))
    mu = np.degrees(np.arctan2(s, c)) % 360
    R = np.sqrt(s**2 + c**2)
    return mu, R


def rayleigh_test(angles_deg: np.ndarray) -> tuple[float, float]:
    """Rayleigh test: returns (R, p-value)."""
    n = len(angles_deg)
    if n < 2:
        return 0.0, 1.0
    rad = np.radians(angles_deg)
    R_bar = np.sqrt(np.mean(np.cos(rad))**2 + np.mean(np.sin(rad))**2)
    R = n * R_bar
    z = R**2 / n
    p = np.exp(-z) * (1 + (2*z - z**2)/(4*n) - (24*z - 132*z**2 + 76*z**3 - 9*z**4)/(288*n**2))
    return R_bar, max(0.0, min(1.0, p))


def draw_arena(ax, inner_r=INNER_R_CM, outer_r=OUTER_R_CM, lw=1.2):
    """Draw concentric arena circles on an axis."""
    for r, ls, color in [(inner_r, "--", "#888"), (outer_r, "-", "#444")]:
        ax.add_patch(Circle((0, 0), r, fill=False, edgecolor=color,
                             linewidth=lw, linestyle=ls, zorder=3))
    # Feeder dot at centre
    ax.plot(0, 0, "s", color="#FFC107", ms=7, zorder=5, label="Feeder")


def add_polar_arena(ax):
    """Draw concentric circles on a polar axis."""
    ax.set_rticks([INNER_R_CM, OUTER_R_CM])
    ax.set_yticklabels([f"{INNER_R_CM:.0f}", f"{OUTER_R_CM:.0f}"], fontsize=7)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.yaxis.set_tick_params(labelsize=7)


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_all_experiments():
    """
    Scan V_OUTPUTS, parse metadata, load trajectories and events.
    Returns (records_df, trajectories_dict).
    """
    cache = load_cache()
    records = []
    trajectories = {}

    print("Loading experiments...")
    folders = sorted([f for f in V_OUTPUTS.iterdir() if f.is_dir() and not f.name.startswith(".")])

    for folder in folders:
        meta = parse_folder_name(folder.name)
        data_dir = folder / "data"
        if not data_dir.exists():
            continue

        # find files
        id0_file = next((f for f in data_dir.glob("*id0_new.csv")), None)
        events_file = next((f for f in data_dir.glob("*events.csv")), None)
        if not id0_file or not events_file:
            continue

        # find centre
        center = get_center_cm(meta["dt_key"], cache)
        if center is None:
            # fallback: try shorter key
            short = meta["dt_key"][:16]
            for k in cache:
                if k.startswith(short):
                    center = (cache[k][0] * CM_PER_PIXEL, cache[k][1] * CM_PER_PIXEL)
                    break
        if center is None:
            continue  # skip if no calibration

        cx_cm, cy_cm = center

        # load tracking
        traj = load_tracking(id0_file, cx_cm, cy_cm)
        if traj is None or len(traj) < 10:
            continue

        # load events
        evts = load_events(events_file)

        # ── Key metrics ──────────────────────────────────────────────
        # First outer-circle exit direction
        outer_exits = evts[evts["event"] == "outer_exit"] if evts is not None else pd.DataFrame()
        inner_exits = evts[evts["event"] == "inner_exit"] if evts is not None else pd.DataFrame()

        exit_angle_deg = np.nan
        if not outer_exits.empty:
            exit_frame = outer_exits.iloc[0]["frame"]
            row = traj[traj["frame"] <= exit_frame]
            if not row.empty:
                last = row.iloc[-1]
                exit_angle_deg = (np.degrees(np.arctan2(last["y"], last["x"])) + 360) % 360

        # first inner-exit direction
        inner_exit_angle_deg = np.nan
        if not inner_exits.empty:
            ef = inner_exits.iloc[0]["frame"]
            row = traj[traj["frame"] <= ef]
            if not row.empty:
                last = row.iloc[-1]
                inner_exit_angle_deg = (np.degrees(np.arctan2(last["y"], last["x"])) + 360) % 360

        # Path metrics
        path_len = float(np.sum(np.sqrt(np.diff(traj["x"])**2 + np.diff(traj["y"])**2))) if len(traj) > 1 else np.nan
        displacement = float(np.sqrt(traj["x"].iloc[-1]**2 + traj["y"].iloc[-1]**2)) if len(traj) > 0 else np.nan
        straightness = displacement / path_len if (path_len and path_len > 0) else np.nan
        mean_speed = float(traj["speed"].mean()) if "speed" in traj.columns else np.nan
        max_r = float(traj["r"].max())

        # Time in inner / outer (based on radius)
        n_frames = len(traj)
        n_inner  = int((traj["r"] <= INNER_R_CM).sum())
        n_outer_only = int(((traj["r"] > INNER_R_CM) & (traj["r"] <= OUTER_R_CM)).sum())
        n_outside = int((traj["r"] > OUTER_R_CM).sum())

        # condition label
        cue = meta["cue"] or "unknown"
        P   = meta["P"]
        U   = meta["U"]

        if not np.isnan(P):
            cond_label = f"{cue}_{'high' if P >= 4 else 'low'}_P"
        else:
            cond_label = "unknown"

        records.append({
            "folder": folder.name,
            "bee_id": meta["bee_id"],
            "cue": cue,
            "P": P,
            "U": U,
            "cx_cm": cx_cm,
            "cy_cm": cy_cm,
            "exit_angle_deg": exit_angle_deg,
            "inner_exit_angle_deg": inner_exit_angle_deg,
            "path_len_cm": path_len,
            "displacement_cm": displacement,
            "straightness": straightness,
            "mean_speed_cms": mean_speed,
            "max_radius_cm": max_r,
            "n_frames": n_frames,
            "pct_in_inner": 100 * n_inner / n_frames if n_frames > 0 else np.nan,
            "pct_in_outer_only": 100 * n_outer_only / n_frames if n_frames > 0 else np.nan,
            "pct_outside": 100 * n_outside / n_frames if n_frames > 0 else np.nan,
            "condition": cond_label,
        })
        trajectories[folder.name] = {"traj": traj, "cue": cue, "P": P, "U": U}

    df = pd.DataFrame(records)
    print(f"  Loaded {len(df)} experiments | "
          f"LR={( df.cue == 'LR').sum()}  TB={(df.cue == 'TB').sum()}")
    return df, trajectories


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE 1 — Representative Trajectories (4-panel)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_representative_trajectories(df, trajectories):
    """4-panel grid showing one representative trajectory per condition."""
    conditions = ["LR", "TB"]
    p_levels   = ["low", "high"]

    fig, axes = plt.subplots(2, 2, figsize=(9, 9))
    fig.suptitle("Representative Bumblebee Trajectories by Condition", fontsize=14, y=1.01)

    for row_i, cue in enumerate(conditions):
        for col_i, plevel in enumerate(p_levels):
            ax = axes[row_i][col_i]
            cond = f"{cue}_{plevel}_P"
            subset = df[df["condition"] == cond]

            # pick the trajectory with most valid frames
            best = None
            if not subset.empty:
                for _, rec in subset.iterrows():
                    t = trajectories.get(rec["folder"])
                    if t and len(t["traj"]) > 0:
                        if best is None or len(t["traj"]) > len(best["traj"]):
                            best = t

            draw_arena(ax)
            ax.set_xlim(-OUTER_R_CM*1.25, OUTER_R_CM*1.25)
            ax.set_ylim(-OUTER_R_CM*1.25, OUTER_R_CM*1.25)
            ax.set_aspect("equal")
            ax.set_xlabel("x (cm)")
            ax.set_ylabel("y (cm)")
            P_label = "P ≥ 4 mg" if plevel == "high" else "P < 4 mg"
            ax.set_title(f"Cue: {cue} | {P_label}  (n={len(subset)})")

            if best:
                traj = best["traj"]
                # colour path by progression (rainbow)
                n = len(traj)
                cmap = plt.cm.plasma
                for i in range(n - 1):
                    c = cmap(i / max(n-1, 1))
                    ax.plot(traj["x"].iloc[i:i+2], traj["y"].iloc[i:i+2],
                            color=c, lw=1.0, alpha=0.8)
                # mark start/end
                ax.plot(traj["x"].iloc[0], traj["y"].iloc[0], "go", ms=8, zorder=6, label="Start")
                ax.plot(traj["x"].iloc[-1], traj["y"].iloc[-1], "rs", ms=8, zorder=6, label="End")
                ax.legend(fontsize=8, loc="upper right")
            else:
                ax.text(0, 0, "No data", ha="center", va="center", fontsize=12, color="grey")

            ax.grid(False)

    sm = plt.cm.ScalarMappable(cmap=plt.cm.plasma, norm=mcolors.Normalize(0, 1))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes, orientation="vertical", fraction=0.02, pad=0.04)
    cbar.set_label("Time →  (start=dark, end=bright)")

    plt.savefig(RESULTS_DIR / "fig1_representative_trajectories.png")
    plt.close()
    print("  ✓ fig1_representative_trajectories.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE 2 — All Trajectories Overlaid per Condition
# ═══════════════════════════════════════════════════════════════════════════════

def plot_all_trajectories_by_condition(df, trajectories):
    """Overlay ALL trajectories per condition."""
    conds = df["condition"].unique()
    ncols = 3
    nrows = int(np.ceil(len(conds) / ncols))

    fig, axes = plt.subplots(nrows, ncols, figsize=(5*ncols, 5*nrows))
    axes = np.array(axes).flatten()
    fig.suptitle("All Trajectories Overlaid by Condition", fontsize=14)

    for i, cond in enumerate(sorted(conds)):
        ax = axes[i]
        subset = df[df["condition"] == cond]
        draw_arena(ax)
        ax.set_xlim(-OUTER_R_CM*1.25, OUTER_R_CM*1.25)
        ax.set_ylim(-OUTER_R_CM*1.25, OUTER_R_CM*1.25)
        ax.set_aspect("equal")
        ax.set_title(f"{cond}  (n={len(subset)})")
        ax.set_xlabel("x (cm)"); ax.set_ylabel("y (cm)")

        color = COND_COLORS.get(cond, "#555")
        for _, rec in subset.iterrows():
            t = trajectories.get(rec["folder"])
            if t:
                ax.plot(t["traj"]["x"], t["traj"]["y"], color=color, alpha=0.25, lw=0.7)

    # hide unused axes
    for j in range(len(conds), len(axes)):
        axes[j].set_visible(False)

    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "fig2_all_trajectories_by_condition.png")
    plt.close()
    print("  ✓ fig2_all_trajectories_by_condition.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE 3 — Polar Exit Direction Plots
# ═══════════════════════════════════════════════════════════════════════════════

def plot_polar_exit_directions(df):
    """Polar scatter + histogram of outer-exit directions per condition."""
    conds = sorted(df["condition"].unique())
    ncols = 3
    nrows = int(np.ceil(len(conds) / ncols))

    fig = plt.figure(figsize=(5*ncols, 5*nrows))
    fig.suptitle("Exit Direction from Outer Circle (Polar Histograms)", fontsize=14)

    for i, cond in enumerate(conds):
        ax = fig.add_subplot(nrows, ncols, i+1, projection="polar")
        subset = df[(df["condition"] == cond) & df["exit_angle_deg"].notna()]
        angles_rad = np.radians(subset["exit_angle_deg"].values)

        bins = np.linspace(0, 2*np.pi, 25)
        counts, _ = np.histogram(angles_rad, bins=bins)
        bin_centers = (bins[:-1] + bins[1:]) / 2
        width = 2 * np.pi / 24

        color = COND_COLORS.get(cond, "#555")
        ax.bar(bin_centers, counts, width=width, color=color, alpha=0.7,
               edgecolor="white", linewidth=0.5)

        # mean vector arrow
        if len(angles_rad) >= 3:
            mu_deg, R = circular_mean_r(subset["exit_angle_deg"].values)
            mu_rad = np.radians(mu_deg)
            _, p = rayleigh_test(subset["exit_angle_deg"].values)
            ax.annotate("", xy=(mu_rad, R * counts.max()),
                        xytext=(0, 0),
                        arrowprops=dict(arrowstyle="->", color="black", lw=2))
            sig_str = f"p={p:.3f}" if p >= 0.001 else "p<0.001"
            ax.set_title(f"{cond}\n(n={len(subset)}, R={R:.2f}, {sig_str})", fontsize=9)
        else:
            ax.set_title(f"{cond}\n(n={len(subset)})", fontsize=9)

        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)

    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "fig3_polar_exit_directions.png")
    plt.close()
    print("  ✓ fig3_polar_exit_directions.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE 4 — Polar Scatter Plots with Mean Vector
# ═══════════════════════════════════════════════════════════════════════════════

def plot_polar_scatter(df):
    """Individual exit angles plotted as dots on a polar plot per condition."""
    conds = sorted(df["condition"].unique())
    ncols = 3
    nrows = int(np.ceil(len(conds) / ncols))

    fig = plt.figure(figsize=(5*ncols, 5*nrows))
    fig.suptitle("Individual Exit Angles by Condition", fontsize=14)

    for i, cond in enumerate(conds):
        ax = fig.add_subplot(nrows, ncols, i+1, projection="polar")
        subset = df[(df["condition"] == cond) & df["exit_angle_deg"].notna()]

        if not subset.empty:
            angles_rad = np.radians(subset["exit_angle_deg"].values)
            r_vals = np.ones(len(angles_rad)) * OUTER_R_CM * 0.8 + np.random.uniform(-3, 3, len(angles_rad))
            color = COND_COLORS.get(cond, "#555")
            ax.scatter(angles_rad, r_vals, color=color, alpha=0.7, s=30, zorder=4)

            # mean vector
            if len(angles_rad) >= 3:
                mu_deg, R = circular_mean_r(subset["exit_angle_deg"].values)
                mu_rad = np.radians(mu_deg)
                _, p = rayleigh_test(subset["exit_angle_deg"].values)
                ax.annotate("", xy=(mu_rad, R * OUTER_R_CM),
                            xytext=(0, 0),
                            arrowprops=dict(arrowstyle="->", color="black", lw=2.5))
                sig_str = f"p={p:.3f}" if p >= 0.001 else "p<0.001"
                ax.set_title(f"{cond}\nn={len(subset)}, R={R:.2f}, {sig_str}", fontsize=9)
            else:
                ax.set_title(f"{cond}\nn={len(subset)}", fontsize=9)
        else:
            ax.set_title(f"{cond}\nNo data", fontsize=9)

        ax.set_ylim(0, OUTER_R_CM * 1.1)
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_rticks([INNER_R_CM, OUTER_R_CM])

    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "fig4_polar_scatter_exit_angles.png")
    plt.close()
    print("  ✓ fig4_polar_scatter_exit_angles.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE 5 — Density Heatmaps
# ═══════════════════════════════════════════════════════════════════════════════

def plot_density_heatmaps(df, trajectories):
    """2D kernel density heatmap of all positions per condition."""
    conds = sorted(df["condition"].unique())
    ncols = 3
    nrows = int(np.ceil(len(conds) / ncols))

    fig, axes = plt.subplots(nrows, ncols, figsize=(5*ncols, 5*nrows))
    axes = np.array(axes).flatten()
    fig.suptitle("Positional Density Heatmaps by Condition", fontsize=14)

    extent = [-OUTER_R_CM*1.2, OUTER_R_CM*1.2, -OUTER_R_CM*1.2, OUTER_R_CM*1.2]
    bins = 80

    for i, cond in enumerate(sorted(conds)):
        ax = axes[i]
        subset = df[df["condition"] == cond]
        all_x, all_y = [], []

        for _, rec in subset.iterrows():
            t = trajectories.get(rec["folder"])
            if t:
                traj = t["traj"]
                within = traj[traj["r"] <= OUTER_R_CM * 1.1]
                all_x.extend(within["x"].values)
                all_y.extend(within["y"].values)

        if len(all_x) > 50:
            h, xedges, yedges = np.histogram2d(all_x, all_y, bins=bins, range=[extent[:2], extent[2:]])
            h = h / h.max()  # normalize
            im = ax.imshow(h.T, origin="lower", extent=extent, cmap="YlOrRd",
                           vmin=0, vmax=1, aspect="equal")
            plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Relative density")
        else:
            ax.text(0, 0, "Insufficient data", ha="center", va="center", fontsize=10, color="grey")
            ax.set_xlim(*extent[:2]); ax.set_ylim(*extent[2:])
            ax.set_aspect("equal")

        draw_arena(ax)
        ax.set_title(f"{cond}  (n={len(subset)})")
        ax.set_xlabel("x (cm)"); ax.set_ylabel("y (cm)")

    for j in range(len(conds), len(axes)):
        axes[j].set_visible(False)

    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "fig5_density_heatmaps.png")
    plt.close()
    print("  ✓ fig5_density_heatmaps.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE 6 — Walking Speed Analysis
# ═══════════════════════════════════════════════════════════════════════════════

def plot_speed_analysis(df):
    """Box + strip plots of walking speed per condition and vs. P level."""
    valid = df[(df["mean_speed_cms"].notna()) & (df["condition"] != "unknown")]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Walking Speed Analysis", fontsize=14)

    # Left: boxplot per condition
    ax = axes[0]
    conds = sorted(valid["condition"].unique())
    data_by_cond = [valid[valid["condition"] == c]["mean_speed_cms"].values for c in conds]
    colors = [COND_COLORS.get(c, "#999") for c in conds]
    bps = ax.boxplot(data_by_cond, patch_artist=True, notch=False,
                     medianprops=dict(color="black", lw=2),
                     flierprops=dict(marker="o", ms=3, alpha=0.5))
    for patch, color in zip(bps["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax.set_xticks(range(1, len(conds)+1))
    ax.set_xticklabels(conds, rotation=30, ha="right")
    ax.set_ylabel("Mean walking speed (cm/s)")
    ax.set_title("Speed by Experimental Condition")

    # Right: scatter vs. P (pollen amount)
    ax = axes[1]
    p_valid = valid[valid["P"].notna()]
    for cue, color, marker in [("LR", "#2196F3", "o"), ("TB", "#F44336", "s")]:
        sub = p_valid[p_valid["cue"] == cue]
        if not sub.empty:
            ax.scatter(sub["P"], sub["mean_speed_cms"], color=color, marker=marker,
                       alpha=0.65, s=50, label=f"Cue: {cue}", zorder=3)
            # regression line
            if len(sub) >= 3:
                slope, intercept, r, p, _ = stats.linregress(sub["P"], sub["mean_speed_cms"])
                xfit = np.linspace(sub["P"].min(), sub["P"].max(), 100)
                ax.plot(xfit, slope*xfit + intercept, color=color, lw=1.5, linestyle="--", alpha=0.7)
                ax.text(sub["P"].max(), slope*sub["P"].max() + intercept,
                        f"r={r:.2f}", fontsize=8, color=color, va="bottom")

    ax.set_xlabel("Pollen amount (mg)")
    ax.set_ylabel("Mean walking speed (cm/s)")
    ax.set_title("Speed vs. Pollen Amount")
    ax.legend()

    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "fig6_speed_analysis.png")
    plt.close()
    print("  ✓ fig6_speed_analysis.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE 7 — Path Straightness / Tortuosity
# ═══════════════════════════════════════════════════════════════════════════════

def plot_path_straightness(df):
    valid = df[(df["straightness"].notna()) & (df["condition"] != "unknown")]
    conds = sorted(valid["condition"].unique())

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Path Straightness Analysis", fontsize=14)

    # Boxplot
    ax = axes[0]
    data_by_cond = [valid[valid["condition"] == c]["straightness"].values for c in conds]
    colors = [COND_COLORS.get(c, "#999") for c in conds]
    bps = ax.boxplot(data_by_cond, patch_artist=True,
                     medianprops=dict(color="black", lw=2),
                     flierprops=dict(marker="o", ms=3, alpha=0.5))
    for patch, color in zip(bps["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax.set_xticks(range(1, len(conds)+1))
    ax.set_xticklabels(conds, rotation=30, ha="right")
    ax.set_ylabel("Path straightness (d / L)")
    ax.set_title("Path Straightness by Condition")
    ax.axhline(1.0, color="grey", linestyle="--", lw=1, alpha=0.5, label="Perfect straight")
    ax.legend()

    # Scatter vs. P
    ax = axes[1]
    p_valid = valid[valid["P"].notna()]
    for cue, color, marker in [("LR", "#2196F3", "o"), ("TB", "#F44336", "s")]:
        sub = p_valid[p_valid["cue"] == cue]
        if not sub.empty:
            ax.scatter(sub["P"], sub["straightness"], color=color, marker=marker,
                       alpha=0.65, s=50, label=f"Cue: {cue}")
    ax.set_xlabel("Pollen amount (mg)")
    ax.set_ylabel("Path straightness (d / L)")
    ax.set_title("Path Straightness vs. Pollen Amount")
    ax.legend()

    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "fig7_path_straightness.png")
    plt.close()
    print("  ✓ fig7_path_straightness.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE 8 — Time Spent in Arena Zones
# ═══════════════════════════════════════════════════════════════════════════════

def plot_zone_time(df):
    valid = df[df["condition"] != "unknown"]
    conds = sorted(valid["condition"].unique())

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle("Time Spent in Arena Zones by Condition", fontsize=14)

    x = np.arange(len(conds))
    w = 0.25

    means_inner = [valid[valid["condition"] == c]["pct_in_inner"].mean() for c in conds]
    means_outer = [valid[valid["condition"] == c]["pct_in_outer_only"].mean() for c in conds]
    means_outside = [valid[valid["condition"] == c]["pct_outside"].mean() for c in conds]

    ax.bar(x - w, means_inner, width=w, label="Inner circle (r≤21 cm)", color="#4CAF50", alpha=0.8)
    ax.bar(x,      means_outer, width=w, label="Outer circle (21<r≤42 cm)", color="#FF9800", alpha=0.8)
    ax.bar(x + w,  means_outside, width=w, label="Outside arena (r>42 cm)", color="#F44336", alpha=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels(conds, rotation=30, ha="right")
    ax.set_ylabel("% of tracking time")
    ax.set_title("Zone Occupancy by Condition")
    ax.legend()
    ax.set_ylim(0, 100)

    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "fig8_zone_time.png")
    plt.close()
    print("  ✓ fig8_zone_time.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE 9 — Exit Direction vs. Pollen Amount (scatter)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_exit_angle_vs_P(df):
    valid = df[df["exit_angle_deg"].notna() & df["P"].notna()]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Exit Direction vs. Pollen Amount", fontsize=14)

    for i, cue in enumerate(["LR", "TB"]):
        ax = axes[i]
        sub = valid[valid["cue"] == cue]
        if sub.empty:
            ax.text(0.5, 0.5, "No data", transform=ax.transAxes, ha="center")
            ax.set_title(f"Cue: {cue}")
            continue

        sc = ax.scatter(sub["P"], sub["exit_angle_deg"],
                        c=sub["U"], cmap="viridis", alpha=0.7, s=60, zorder=3)
        plt.colorbar(sc, ax=ax, label="Uncertainty (U)")
        ax.set_xlabel("Pollen amount P (mg)")
        ax.set_ylabel("Exit angle (°)")
        ax.set_ylim(0, 360)
        ax.set_title(f"Cue: {cue}")
        ax.axhline(180, color="grey", linestyle="--", lw=1, alpha=0.5, label="180° (home direction)")
        ax.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "fig9_exit_angle_vs_pollen.png")
    plt.close()
    print("  ✓ fig9_exit_angle_vs_pollen.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE 10 — Search Radius vs. P and U
# ═══════════════════════════════════════════════════════════════════════════════

def plot_search_radius(df):
    valid = df[df["max_radius_cm"].notna() & df["P"].notna()]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Search Radius Analysis", fontsize=14)

    for i, (x_col, x_label) in enumerate([("P", "Pollen amount (mg)"), ("U", "Uncertainty (U)")]):
        ax = axes[i]
        sub = valid[valid[x_col].notna()]
        for cue, color, marker in [("LR", "#2196F3", "o"), ("TB", "#F44336", "s")]:
            csub = sub[sub["cue"] == cue]
            if not csub.empty:
                ax.scatter(csub[x_col], csub["max_radius_cm"], color=color, marker=marker,
                           alpha=0.6, s=50, label=f"Cue: {cue}", zorder=3)
                if len(csub) >= 3:
                    slope, intercept, r, p, _ = stats.linregress(csub[x_col].astype(float),
                                                                   csub["max_radius_cm"].astype(float))
                    xfit = np.linspace(csub[x_col].min(), csub[x_col].max(), 100)
                    ax.plot(xfit, slope*xfit + intercept, color=color, lw=1.5, linestyle="--")

        ax.axhline(OUTER_R_CM, color="black", linestyle="--", lw=1, alpha=0.5, label="Outer circle")
        ax.axhline(INNER_R_CM, color="grey", linestyle=":", lw=1, alpha=0.5, label="Inner circle")
        ax.set_xlabel(x_label)
        ax.set_ylabel("Max search radius (cm)")
        ax.set_title(f"Search Radius vs. {x_label}")
        ax.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "fig10_search_radius.png")
    plt.close()
    print("  ✓ fig10_search_radius.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE 11 — LR vs TB overall comparison (polar)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_lr_vs_tb_polar(df):
    """Paired polar plot: all LR exits vs all TB exits."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 5),
                              subplot_kw={"projection": "polar"})
    fig.suptitle("Overall Exit Direction: LR vs TB Polarization Cue", fontsize=14)

    for ax, cue, color in zip(axes, ["LR", "TB"], ["#2196F3", "#F44336"]):
        sub = df[(df["cue"] == cue) & df["exit_angle_deg"].notna()]
        angles_rad = np.radians(sub["exit_angle_deg"].values)

        bins = np.linspace(0, 2*np.pi, 25)
        counts, _ = np.histogram(angles_rad, bins=bins)
        bin_centers = (bins[:-1] + bins[1:]) / 2
        width = 2 * np.pi / 24

        ax.bar(bin_centers, counts, width=width, color=color, alpha=0.7,
               edgecolor="white", linewidth=0.5)

        if len(angles_rad) >= 3:
            mu_deg, R = circular_mean_r(sub["exit_angle_deg"].values)
            _, p = rayleigh_test(sub["exit_angle_deg"].values)
            mu_rad = np.radians(mu_deg)
            scale = counts.max() * R
            ax.annotate("", xy=(mu_rad, scale),
                        xytext=(0, 0),
                        arrowprops=dict(arrowstyle="->", color="black", lw=2.5))
            sig_str = f"p={p:.3f}" if p >= 0.001 else "p<0.001"
            ax.set_title(f"Cue: {cue}\nn={len(sub)}, R={R:.2f}, {sig_str}", pad=15)
        else:
            ax.set_title(f"Cue: {cue}\nn={len(sub)}", pad=15)

        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)

    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "fig11_lr_vs_tb_polar.png")
    plt.close()
    print("  ✓ fig11_lr_vs_tb_polar.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE 12 — Bee-by-Bee Trajectories (per unique bee ID)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_per_bee_trajectories(df, trajectories):
    """One subplot per unique bee, showing all its trajectories."""
    bees = sorted(df[df["bee_id"] != "unknown"]["bee_id"].unique())
    if len(bees) == 0:
        return

    # max 16 bees per figure
    bees = bees[:16]
    ncols = 4
    nrows = int(np.ceil(len(bees) / ncols))

    fig, axes = plt.subplots(nrows, ncols, figsize=(5*ncols, 5*nrows))
    axes = np.array(axes).flatten()
    fig.suptitle("Individual Bee Trajectories", fontsize=14)

    for i, bee in enumerate(bees):
        ax = axes[i]
        bee_df = df[df["bee_id"] == bee]
        draw_arena(ax)
        ax.set_xlim(-OUTER_R_CM*1.3, OUTER_R_CM*1.3)
        ax.set_ylim(-OUTER_R_CM*1.3, OUTER_R_CM*1.3)
        ax.set_aspect("equal")
        ax.set_title(f"Bee {bee}  (n={len(bee_df)})", fontsize=9)

        for _, rec in bee_df.iterrows():
            t = trajectories.get(rec["folder"])
            if t:
                color = COND_COLORS.get(rec["condition"], "#555")
                ax.plot(t["traj"]["x"], t["traj"]["y"], color=color, alpha=0.4, lw=0.8)

    for j in range(len(bees), len(axes)):
        axes[j].set_visible(False)

    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "fig12_per_bee_trajectories.png")
    plt.close()
    print("  ✓ fig12_per_bee_trajectories.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE 13 — Summary statistics table
# ═══════════════════════════════════════════════════════════════════════════════

def plot_summary_stats_table(df):
    """Render a summary statistics table as a figure."""
    valid = df[df["exit_angle_deg"].notna()]
    conds = sorted(valid["condition"].unique())

    rows = []
    for cond in conds:
        sub = valid[valid["condition"] == cond]
        mu_deg, R = circular_mean_r(sub["exit_angle_deg"].values) if len(sub) >= 2 else (np.nan, np.nan)
        _, p = rayleigh_test(sub["exit_angle_deg"].values) if len(sub) >= 2 else (np.nan, np.nan)
        rows.append({
            "Condition": cond,
            "n": len(sub),
            "Mean dir (°)": f"{mu_deg:.1f}" if not np.isnan(mu_deg) else "—",
            "Mean vec R": f"{R:.3f}" if not np.isnan(R) else "—",
            "Rayleigh p": f"{p:.4f}" if not np.isnan(p) else "—",
            "Sig.": "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns")) if not np.isnan(p) else "—",
            "Mean speed": f"{sub['mean_speed_cms'].mean():.2f}" if sub['mean_speed_cms'].notna().any() else "—",
            "Mean P": f"{sub['P'].mean():.2f}" if sub['P'].notna().any() else "—",
        })

    table_df = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(14, max(3, 0.5 * len(rows) + 2)))
    ax.axis("off")
    tbl = ax.table(
        cellText=table_df.values,
        colLabels=table_df.columns,
        cellLoc="center",
        loc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1, 1.8)

    # Header style
    for j in range(len(table_df.columns)):
        tbl[(0, j)].set_facecolor("#1976D2")
        tbl[(0, j)].set_text_props(color="white", fontweight="bold")

    # Alternating row colours
    for row_i in range(1, len(rows)+1):
        for col_j in range(len(table_df.columns)):
            tbl[(row_i, col_j)].set_facecolor("#E3F2FD" if row_i % 2 == 0 else "white")

    ax.set_title("Summary Statistics by Condition", fontsize=13, fontweight="bold", pad=10)
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "fig13_summary_statistics_table.png")
    plt.close()
    print("  ✓ fig13_summary_statistics_table.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE 14 — Exit angle distribution violin plots
# ═══════════════════════════════════════════════════════════════════════════════

def plot_exit_angle_violins(df):
    """Violin plot of exit angles per condition."""
    valid = df[df["exit_angle_deg"].notna() & (df["condition"] != "unknown")]
    conds = sorted(valid["condition"].unique())

    fig, ax = plt.subplots(figsize=(10, 5))
    data_by_cond = [valid[valid["condition"] == c]["exit_angle_deg"].values for c in conds]
    colors = [COND_COLORS.get(c, "#999") for c in conds]

    parts = ax.violinplot(data_by_cond, positions=range(len(conds)),
                          showmedians=True, showextrema=True)
    for pc, color in zip(parts["bodies"], colors):
        pc.set_facecolor(color)
        pc.set_alpha(0.7)

    ax.set_xticks(range(len(conds)))
    ax.set_xticklabels(conds, rotation=30, ha="right")
    ax.set_ylabel("Exit angle (°)")
    ax.set_ylim(0, 360)
    ax.set_yticks([0, 45, 90, 135, 180, 225, 270, 315, 360])
    ax.set_title("Exit Angle Distribution by Condition", fontsize=13, fontweight="bold")
    ax.axhline(180, color="black", linestyle="--", lw=1, alpha=0.4, label="180° (home)")
    ax.legend()
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "fig14_exit_angle_violins.png")
    plt.close()
    print("  ✓ fig14_exit_angle_violins.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE 15 — Trajectory length distributions
# ═══════════════════════════════════════════════════════════════════════════════

def plot_path_lengths(df):
    valid = df[df["path_len_cm"].notna() & (df["condition"] != "unknown")]
    conds = sorted(valid["condition"].unique())

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Path Length Analysis", fontsize=14)

    ax = axes[0]
    data_by_cond = [valid[valid["condition"] == c]["path_len_cm"].values for c in conds]
    colors = [COND_COLORS.get(c, "#999") for c in conds]
    bps = ax.boxplot(data_by_cond, patch_artist=True,
                     medianprops=dict(color="black", lw=2))
    for patch, color in zip(bps["boxes"], colors):
        patch.set_facecolor(color); patch.set_alpha(0.7)
    ax.set_xticks(range(1, len(conds)+1))
    ax.set_xticklabels(conds, rotation=30, ha="right")
    ax.set_ylabel("Total path length (cm)")
    ax.set_title("Path Length by Condition")

    ax = axes[1]
    p_valid = valid[valid["P"].notna()]
    for cue, color, marker in [("LR", "#2196F3", "o"), ("TB", "#F44336", "s")]:
        sub = p_valid[p_valid["cue"] == cue]
        if not sub.empty:
            ax.scatter(sub["P"], sub["path_len_cm"], color=color, marker=marker,
                       alpha=0.6, s=50, label=f"Cue: {cue}")
    ax.set_xlabel("Pollen amount (mg)")
    ax.set_ylabel("Total path length (cm)")
    ax.set_title("Path Length vs. Pollen Amount")
    ax.legend()

    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "fig15_path_lengths.png")
    plt.close()
    print("  ✓ fig15_path_lengths.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE 16 — Full dataset multi-panel overview
# ═══════════════════════════════════════════════════════════════════════════════

def plot_overview_dashboard(df, trajectories):
    """A single publication-quality multi-panel figure."""
    fig = plt.figure(figsize=(18, 14))
    gs = GridSpec(3, 4, figure=fig, hspace=0.45, wspace=0.4)

    # ── Top row: representative trajectories (LR low-P, LR high-P, TB low-P, TB high-P) ──
    cond_panel = [
        ("LR_low_P",  0, 0, "Cue LR, Low P"),
        ("LR_high_P", 0, 1, "Cue LR, High P"),
        ("TB_low_P",  0, 2, "Cue TB, Low P"),
        ("TB_high_P", 0, 3, "Cue TB, High P"),
    ]
    for cond, row, col, title in cond_panel:
        ax = fig.add_subplot(gs[row, col])
        subset = df[df["condition"] == cond]
        best = None
        for _, rec in subset.iterrows():
            t = trajectories.get(rec["folder"])
            if t and (best is None or len(t["traj"]) > len(best["traj"])):
                best = t
        draw_arena(ax)
        ax.set_xlim(-OUTER_R_CM*1.2, OUTER_R_CM*1.2)
        ax.set_ylim(-OUTER_R_CM*1.2, OUTER_R_CM*1.2)
        ax.set_aspect("equal")
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("x (cm)", fontsize=8); ax.set_ylabel("y (cm)", fontsize=8)
        if best:
            traj = best["traj"]
            n = len(traj)
            cmap = plt.cm.plasma
            for i in range(n-1):
                c = cmap(i / max(n-1,1))
                ax.plot(traj["x"].iloc[i:i+2], traj["y"].iloc[i:i+2],
                        color=c, lw=1.0, alpha=0.85)
        ax.tick_params(labelsize=7)

    # ── Middle row: polar histograms LR vs TB ──
    for i, (cue, color) in enumerate([("LR", "#2196F3"), ("TB", "#F44336")]):
        ax = fig.add_subplot(gs[1, i], projection="polar")
        sub = df[(df["cue"] == cue) & df["exit_angle_deg"].notna()]
        angles_rad = np.radians(sub["exit_angle_deg"].values)
        bins = np.linspace(0, 2*np.pi, 25)
        counts, _ = np.histogram(angles_rad, bins=bins)
        bin_centers = (bins[:-1] + bins[1:]) / 2
        width = 2*np.pi / 24
        ax.bar(bin_centers, counts, width=width, color=color, alpha=0.75, edgecolor="white")
        if len(angles_rad) >= 3:
            mu_deg, R = circular_mean_r(sub["exit_angle_deg"].values)
            _, p = rayleigh_test(sub["exit_angle_deg"].values)
            mu_rad = np.radians(mu_deg)
            ax.annotate("", xy=(mu_rad, R*counts.max()), xytext=(0,0),
                        arrowprops=dict(arrowstyle="->", color="black", lw=2))
            sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
            ax.set_title(f"Exit dirs: {cue}\nn={len(sub)}, R={R:.2f} {sig}", fontsize=9, pad=12)
        ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)

    # ── Middle row: speed and straightness boxplots ──
    for j, (metric, label) in enumerate([("mean_speed_cms", "Speed (cm/s)"),
                                          ("straightness", "Straightness (d/L)")]):
        ax = fig.add_subplot(gs[1, j+2])
        valid = df[(df[metric].notna()) & (df["condition"] != "unknown")]
        conds = sorted(valid["condition"].unique())
        data_by_cond = [valid[valid["condition"]==c][metric].values for c in conds]
        colors = [COND_COLORS.get(c, "#999") for c in conds]
        bps = ax.boxplot(data_by_cond, patch_artist=True,
                         medianprops=dict(color="black", lw=2),
                         flierprops=dict(marker="o", ms=2, alpha=0.4))
        for patch, color in zip(bps["boxes"], colors):
            patch.set_facecolor(color); patch.set_alpha(0.7)
        ax.set_xticks(range(1, len(conds)+1))
        ax.set_xticklabels([c.replace("_", "\n") for c in conds], fontsize=7, rotation=0)
        ax.set_ylabel(label, fontsize=9)
        ax.set_title(label, fontsize=9)
        ax.tick_params(labelsize=7)

    # ── Bottom row: heatmaps ──
    for j, cond in enumerate(["LR_low_P", "LR_high_P", "TB_low_P", "TB_high_P"]):
        ax = fig.add_subplot(gs[2, j])
        subset = df[df["condition"] == cond]
        all_x, all_y = [], []
        for _, rec in subset.iterrows():
            t = trajectories.get(rec["folder"])
            if t:
                traj = t["traj"]
                within = traj[traj["r"] <= OUTER_R_CM*1.1]
                all_x.extend(within["x"].values)
                all_y.extend(within["y"].values)
        extent = [-OUTER_R_CM*1.2, OUTER_R_CM*1.2, -OUTER_R_CM*1.2, OUTER_R_CM*1.2]
        if len(all_x) > 50:
            h, xe, ye = np.histogram2d(all_x, all_y, bins=60, range=[extent[:2], extent[2:]])
            h = h / h.max()
            ax.imshow(h.T, origin="lower", extent=extent, cmap="YlOrRd", vmin=0, vmax=1, aspect="equal")
        draw_arena(ax)
        ax.set_xlim(*extent[:2]); ax.set_ylim(*extent[2:])
        ax.set_aspect("equal")
        ax.set_title(f"Heatmap: {cond}\n(n={len(subset)})", fontsize=9)
        ax.set_xlabel("x (cm)", fontsize=8); ax.set_ylabel("y (cm)", fontsize=8)
        ax.tick_params(labelsize=7)

    fig.suptitle("Bumblebee Path Integration — Complete Overview", fontsize=16, fontweight="bold")
    plt.savefig(RESULTS_DIR / "fig16_overview_dashboard.png", dpi=200)
    plt.close()
    print("  ✓ fig16_overview_dashboard.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  SAVE SUMMARY CSV
# ═══════════════════════════════════════════════════════════════════════════════

def save_summary_csv(df):
    out = RESULTS_DIR / "summary_all_experiments.csv"
    df.drop(columns=["cx_cm", "cy_cm"], errors="ignore").to_csv(out, index=False)
    print(f"  ✓ summary_all_experiments.csv  ({len(df)} rows)")

    # Per-condition summary
    cond_rows = []
    for cond in sorted(df["condition"].unique()):
        sub = df[df["condition"] == cond]
        valid_exits = sub[sub["exit_angle_deg"].notna()]
        mu_deg, R = circular_mean_r(valid_exits["exit_angle_deg"].values) if len(valid_exits)>=2 else (np.nan, np.nan)
        _, p = rayleigh_test(valid_exits["exit_angle_deg"].values) if len(valid_exits)>=2 else (np.nan, np.nan)
        cond_rows.append({
            "condition": cond,
            "n_total": len(sub),
            "n_with_exit": len(valid_exits),
            "mean_dir_deg": round(mu_deg, 2) if not np.isnan(mu_deg) else np.nan,
            "mean_vector_R": round(R, 4) if not np.isnan(R) else np.nan,
            "rayleigh_p": round(p, 6) if not np.isnan(p) else np.nan,
            "mean_speed_cms": round(sub["mean_speed_cms"].mean(), 3),
            "mean_path_len_cm": round(sub["path_len_cm"].mean(), 2),
            "mean_straightness": round(sub["straightness"].mean(), 4),
            "pct_in_inner_mean": round(sub["pct_in_inner"].mean(), 2),
            "pct_in_outer_mean": round(sub["pct_in_outer_only"].mean(), 2),
            "pct_outside_mean": round(sub["pct_outside"].mean(), 2),
        })
    cond_df = pd.DataFrame(cond_rows)
    cond_df.to_csv(RESULTS_DIR / "summary_per_condition.csv", index=False)
    print(f"  ✓ summary_per_condition.csv  ({len(cond_rows)} conditions)")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  Bumblebee Path Integration Analysis")
    print("=" * 60)

    # Load data
    df, trajectories = load_all_experiments()

    if df.empty:
        print("ERROR: No data loaded. Check V_OUTPUTS path and file structure.")
        return

    print(f"\nCondition breakdown:")
    print(df["condition"].value_counts().to_string())
    print(f"\nCue breakdown:")
    print(df["cue"].value_counts().to_string())

    print(f"\nGenerating figures → {RESULTS_DIR}")

    save_summary_csv(df)

    print("\n[Trajectories]")
    plot_representative_trajectories(df, trajectories)
    plot_all_trajectories_by_condition(df, trajectories)
    plot_per_bee_trajectories(df, trajectories)

    print("\n[Polar / Direction]")
    plot_polar_exit_directions(df)
    plot_polar_scatter(df)
    plot_lr_vs_tb_polar(df)
    plot_exit_angle_vs_P(df)

    print("\n[Spatial / Density]")
    plot_density_heatmaps(df, trajectories)
    plot_zone_time(df)
    plot_search_radius(df)

    print("\n[Path metrics]")
    plot_speed_analysis(df)
    plot_path_straightness(df)
    plot_path_lengths(df)
    plot_exit_angle_violins(df)

    print("\n[Overview]")
    plot_summary_stats_table(df)
    plot_overview_dashboard(df, trajectories)

    print("\n" + "=" * 60)
    print(f"  Done!  All figures saved to:")
    print(f"  {RESULTS_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
