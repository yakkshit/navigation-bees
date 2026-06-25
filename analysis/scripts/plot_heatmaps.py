#!/usr/bin/env python3
"""
Paper-style heatmaps for Bumblebee Path Integration
=====================================================
Reproduces Figure 6B/6C style from Patel et al. (2022):
  - Dark navy background
  - Hot colormap (black→red→orange→yellow→white)
  - White dashed arena boundary circles
  - Per-condition + all-conditions combined views
"""

import json
import re
import warnings
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Circle
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path
from scipy.ndimage import gaussian_filter

warnings.filterwarnings("ignore")
matplotlib.use("Agg")

# ─── paths ────────────────────────────────────────────────────────────────────
V_OUTPUTS   = Path("/Users/yakkshit/Downloads/project/hiwi2/p1/V_OUTPUTS")
CACHE_PATH  = Path("/Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee_task/circle_config_cache.json")
RESULTS_DIR = Path("/Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee_task/analysis/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ─── constants ────────────────────────────────────────────────────────────────
INNER_R_CM   = 21.0
OUTER_R_CM   = 42.0
CM_PER_PIXEL = 0.1546

# ─── colormap matching paper: dark navy → red → orange → yellow → white ───────
PAPER_CMAP = LinearSegmentedColormap.from_list(
    "paper_heat",
    [
        (0.00, "#050520"),   # background: dark navy
        (0.05, "#0a0a50"),   # very dark blue
        (0.15, "#1a1aaa"),   # medium blue
        (0.30, "#5500dd"),   # blue-violet
        (0.45, "#cc0000"),   # red
        (0.60, "#ff6600"),   # orange
        (0.75, "#ffcc00"),   # yellow
        (0.90, "#ffff88"),   # pale yellow
        (1.00, "#ffffff"),   # white (hottest)
    ],
    N=512,
)
PAPER_CMAP.set_under("#050520")  # below min stays dark

# ─── helpers ──────────────────────────────────────────────────────────────────

def load_cache():
    if CACHE_PATH.exists():
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}

def parse_folder_name(name):
    n = name.strip()
    dt_key = n[:19]
    cue = "LR" if re.search(r'\bLR\b', n, re.I) else ("TB" if re.search(r'\bTB\b', n, re.I) else None)
    p_match = re.search(r'P\s*([0-9]+(?:\.[0-9]+)?)', n, re.I)
    P = float(p_match.group(1)) if p_match else np.nan
    return dict(dt_key=dt_key, cue=cue, P=P)

def get_center_cm(dt_key, cache):
    for k in [dt_key, dt_key + ".mp4", dt_key + ".mkv"]:
        if k in cache:
            cx_px, cy_px = cache[k]
            return cx_px * CM_PER_PIXEL, cy_px * CM_PER_PIXEL
    short = dt_key[:16]
    for k in cache:
        if k.startswith(short):
            return cache[k][0] * CM_PER_PIXEL, cache[k][1] * CM_PER_PIXEL
    return None

def load_trajectory(id0_file, cx_cm, cy_cm):
    try:
        df = pd.read_csv(id0_file, low_memory=False)
        x_col = next((c for c in ["X (cm)", "X#wcentroid (cm)"] if c in df.columns), None)
        y_col = next((c for c in ["Y (cm)", "Y#wcentroid (cm)"] if c in df.columns), None)
        if not x_col or not y_col:
            return None
        valid = df[(df["missing"] == 0) & np.isfinite(df[x_col]) & np.isfinite(df[y_col])].copy()
        if valid.empty:
            return None
        valid["x"] = valid[x_col] - cx_cm
        valid["y"] = valid[y_col] - cy_cm
        valid["r"] = np.hypot(valid["x"], valid["y"])
        valid["speed"] = valid["SPEED (cm/s)"].clip(0, 50) if "SPEED (cm/s)" in valid.columns else np.nan
        valid["t"] = np.arange(len(valid))  # time index
        return valid.reset_index(drop=True)
    except Exception:
        return None

def draw_arena_dark(ax, inner_r=INNER_R_CM, outer_r=OUTER_R_CM):
    """Draw arena circles on a dark background axis."""
    ax.add_patch(Circle((0, 0), inner_r, fill=False, edgecolor="white",
                         linewidth=1.5, linestyle="--", zorder=5, alpha=0.6))
    ax.add_patch(Circle((0, 0), outer_r, fill=False, edgecolor="white",
                         linewidth=2.0, linestyle="--", zorder=5, alpha=0.8))
    # feeder marker at centre
    ax.plot(0, 0, "o", color="white", ms=6, zorder=6, markeredgewidth=1.5,
            markeredgecolor="white", markerfacecolor="#050520")

def compute_heatmap(traj_list, extent, bins, blur_sigma=1.5, clip_r=None):
    """Stack all trajectories into a 2D histogram, apply Gaussian blur."""
    all_x, all_y = [], []
    for traj in traj_list:
        if traj is None:
            continue
        if clip_r is not None:
            traj = traj[traj["r"] <= clip_r]
        all_x.extend(traj["x"].values)
        all_y.extend(traj["y"].values)
    if len(all_x) < 5:
        return None
    H, _, _ = np.histogram2d(all_x, all_y, bins=bins,
                              range=[[extent[0], extent[1]], [extent[2], extent[3]]])
    H = gaussian_filter(H.astype(float), sigma=blur_sigma)
    return H

# ─── load all experiments ─────────────────────────────────────────────────────

def load_all():
    cache = load_cache()
    groups = {"LR_low_P": [], "LR_high_P": [], "TB_low_P": [], "TB_high_P": [], "all": []}

    print("Loading experiments for heatmaps...")
    folders = sorted([f for f in V_OUTPUTS.iterdir() if f.is_dir() and not f.name.startswith(".")])
    n_loaded = 0

    for folder in folders:
        meta = parse_folder_name(folder.name)
        data_dir = folder / "data"
        if not data_dir.exists():
            continue
        id0_file = next((f for f in data_dir.glob("*id0_new.csv")), None)
        if not id0_file:
            continue
        center = get_center_cm(meta["dt_key"], cache)
        if center is None:
            continue
        traj = load_trajectory(id0_file, *center)
        if traj is None or len(traj) < 10:
            continue

        n_loaded += 1
        cue = meta["cue"]
        P   = meta["P"]
        groups["all"].append(traj)

        if cue and not np.isnan(P):
            key = f"{cue}_{'high' if P >= 4 else 'low'}_P"
            if key in groups:
                groups[key].append(traj)

    print(f"  Loaded {n_loaded} experiments")
    for k, v in groups.items():
        print(f"  {k}: {len(v)} trajectories")
    return groups


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE A — Paper-style ALL-conditions heatmap (like Fig 6B)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_combined_heatmap(groups):
    """Single heatmap of ALL bees — replicates Fig 6B style."""
    EXTENT = [-OUTER_R_CM*1.2, OUTER_R_CM*1.2]
    BINS   = 200

    fig, axes = plt.subplots(1, 2, figsize=(14, 6.5))
    fig.patch.set_facecolor("#050520")

    titles = [
        ("all", "All Experiments — Full Trajectories", None),
        ("all", "All Experiments — Within Arena (r ≤ 42 cm)", OUTER_R_CM),
    ]

    for ax, (group_key, title, clip_r) in zip(axes, titles):
        ax.set_facecolor("#050520")
        traj_list = groups[group_key]

        H = compute_heatmap(traj_list, EXTENT * 2, BINS, blur_sigma=1.8, clip_r=clip_r)
        if H is not None:
            H_norm = H / H.max()
            im = ax.imshow(
                H_norm.T,
                origin="lower",
                extent=EXTENT + EXTENT,
                cmap=PAPER_CMAP,
                vmin=0.02,
                vmax=1.0,
                aspect="equal",
                interpolation="bilinear",
            )
            cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
            cbar.set_label("Density", color="white", fontsize=10)
            cbar.ax.yaxis.set_tick_params(color="white")
            plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")
            cbar.outline.set_edgecolor("white")

        draw_arena_dark(ax)
        ax.set_xlim(*EXTENT); ax.set_ylim(*EXTENT)
        ax.set_aspect("equal")
        ax.set_title(title, color="white", fontsize=11, fontweight="bold", pad=8)
        ax.set_xlabel("x (cm)", color="white", fontsize=10)
        ax.set_ylabel("y (cm)", color="white", fontsize=10)
        ax.tick_params(colors="white", labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor("#334")

        # labels
        ax.text(0, -OUTER_R_CM * 0.95, f"n = {len(traj_list)} bees",
                ha="center", va="top", color="white", fontsize=9, alpha=0.8)

    fig.suptitle("Positional Density Heatmaps — All Bees",
                 color="white", fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "heatmap_all_bees.png", dpi=200,
                facecolor="#050520", bbox_inches="tight")
    plt.close()
    print("  ✓ heatmap_all_bees.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE B — Per-condition heatmaps (2×2 grid)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_per_condition_heatmaps(groups):
    """2×2 grid replicating Fig 6C style per condition."""
    EXTENT = [-OUTER_R_CM*1.2, OUTER_R_CM*1.2]
    BINS   = 150

    cond_info = [
        ("LR_low_P",  "Cue: LR — Low Pollen (P < 4 mg)"),
        ("LR_high_P", "Cue: LR — High Pollen (P ≥ 4 mg)"),
        ("TB_low_P",  "Cue: TB — Low Pollen (P < 4 mg)"),
        ("TB_high_P", "Cue: TB — High Pollen (P ≥ 4 mg)"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(13, 13))
    fig.patch.set_facecolor("#050520")
    axes_flat = axes.flatten()

    for ax, (cond, title) in zip(axes_flat, cond_info):
        ax.set_facecolor("#050520")
        traj_list = groups.get(cond, [])
        n = len(traj_list)

        H = compute_heatmap(traj_list, EXTENT * 2, BINS, blur_sigma=1.5, clip_r=OUTER_R_CM * 1.15)

        if H is not None and H.max() > 0:
            H_norm = H / H.max()
            im = ax.imshow(
                H_norm.T,
                origin="lower",
                extent=EXTENT + EXTENT,
                cmap=PAPER_CMAP,
                vmin=0.02,
                vmax=1.0,
                aspect="equal",
                interpolation="bilinear",
            )
            cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02, shrink=0.8)
            cbar.set_label("Density", color="white", fontsize=9)
            cbar.ax.yaxis.set_tick_params(color="white")
            plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")
            cbar.outline.set_edgecolor("white")
        else:
            ax.text(0, 0, f"No data\n(n={n})", ha="center", va="center",
                    color="white", fontsize=12, alpha=0.6)

        draw_arena_dark(ax)
        ax.set_xlim(*EXTENT); ax.set_ylim(*EXTENT)
        ax.set_aspect("equal")
        ax.set_title(f"{title}\n(n = {n})", color="white", fontsize=10, fontweight="bold", pad=6)
        ax.set_xlabel("x (cm)", color="white", fontsize=9)
        ax.set_ylabel("y (cm)", color="white", fontsize=9)
        ax.tick_params(colors="white", labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor("#334")

        # scale bar: 25 cm
        bar_x0 = OUTER_R_CM * 0.35
        ax.plot([bar_x0, bar_x0 + 25], [-OUTER_R_CM * 1.1, -OUTER_R_CM * 1.1],
                color="white", lw=2.5)
        ax.text(bar_x0 + 12.5, -OUTER_R_CM * 1.1 - 2, "25 cm",
                ha="center", va="top", color="white", fontsize=8)

    fig.suptitle("Positional Density Heatmaps by Experimental Condition",
                 color="white", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "heatmap_per_condition.png", dpi=200,
                facecolor="#050520", bbox_inches="tight")
    plt.close()
    print("  ✓ heatmap_per_condition.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE C — Time-colored trajectory overlays (like Fig 6A/G)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_trajectory_overlays(groups):
    """All trajectories overlaid, colored by time — paper Figure 3C / 6A style."""
    cond_info = [
        ("LR_low_P",  "Cue: LR — Low P"),
        ("LR_high_P", "Cue: LR — High P"),
        ("TB_low_P",  "Cue: TB — Low P"),
        ("TB_high_P", "Cue: TB — High P"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(13, 13))
    fig.patch.set_facecolor("#0a0a1a")
    axes_flat = axes.flatten()
    cmap = plt.cm.plasma  # dark→bright = start→end

    for ax, (cond, title) in zip(axes_flat, cond_info):
        ax.set_facecolor("#0a0a1a")
        traj_list = groups.get(cond, [])

        for traj in traj_list:
            if traj is None or len(traj) < 2:
                continue
            x, y = traj["x"].values, traj["y"].values
            n = len(x)
            # Plot segments coloured by position in time
            for i in range(0, n - 1, max(1, n // 300)):  # subsample for speed
                t_norm = i / max(n - 1, 1)
                color = cmap(t_norm)
                ax.plot(x[i:i+2], y[i:i+2], color=color, lw=0.6, alpha=0.55)

        # arena
        for r, ls, alpha in [(INNER_R_CM, "--", 0.5), (OUTER_R_CM, "-", 0.8)]:
            ax.add_patch(Circle((0, 0), r, fill=False, edgecolor="white",
                                 linewidth=1.5, linestyle=ls, zorder=5, alpha=alpha))
        ax.plot(0, 0, "o", color="white", ms=6, zorder=6,
                markeredgewidth=1.5, markeredgecolor="white", markerfacecolor="#0a0a1a")

        lim = OUTER_R_CM * 1.2
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
        ax.set_aspect("equal")
        ax.set_title(f"{title}  (n = {len(traj_list)})",
                     color="white", fontsize=11, fontweight="bold", pad=6)
        ax.set_xlabel("x (cm)", color="white", fontsize=9)
        ax.set_ylabel("y (cm)", color="white", fontsize=9)
        ax.tick_params(colors="white", labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor("#334")

        # scale bar
        ax.plot([15, 40], [-lim + 3, -lim + 3], color="white", lw=2.5)
        ax.text(27.5, -lim + 5, "25 cm", ha="center", va="bottom",
                color="white", fontsize=8)

    # colorbar for time
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=mcolors.Normalize(0, 1))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes_flat, fraction=0.015, pad=0.02)
    cbar.set_label("Trajectory time  (dark=start → bright=end)", color="white", fontsize=10)
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")
    cbar.outline.set_edgecolor("white")

    fig.suptitle("All Trajectories Overlaid — Time-Coloured (Plasma)",
                 color="white", fontsize=14, fontweight="bold")
    plt.savefig(RESULTS_DIR / "heatmap_trajectory_overlays.png", dpi=200,
                facecolor="#0a0a1a", bbox_inches="tight")
    plt.close()
    print("  ✓ heatmap_trajectory_overlays.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE D — LR vs TB side-by-side heatmap (publication panel)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_lr_vs_tb_heatmap(groups):
    """LR vs TB direct comparison — 1×2 panel."""
    EXTENT = [-OUTER_R_CM * 1.15, OUTER_R_CM * 1.15]
    BINS = 160

    fig, axes = plt.subplots(1, 2, figsize=(14, 6.5))
    fig.patch.set_facecolor("#050520")

    for ax, cue in zip(axes, ["LR", "TB"]):
        ax.set_facecolor("#050520")
        traj_list = groups.get(f"{cue}_low_P", []) + groups.get(f"{cue}_high_P", [])
        n = len(traj_list)

        H = compute_heatmap(traj_list, EXTENT * 2, BINS, blur_sigma=1.5,
                            clip_r=OUTER_R_CM * 1.1)
        if H is not None and H.max() > 0:
            H_norm = H / H.max()
            im = ax.imshow(H_norm.T, origin="lower", extent=EXTENT + EXTENT,
                           cmap=PAPER_CMAP, vmin=0.02, vmax=1.0,
                           aspect="equal", interpolation="bilinear")
            cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
            cbar.set_label("Density", color="white", fontsize=10)
            cbar.ax.yaxis.set_tick_params(color="white")
            plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")
            cbar.outline.set_edgecolor("white")
        else:
            ax.text(0, 0, "No data", ha="center", va="center", color="white", fontsize=12)

        draw_arena_dark(ax, INNER_R_CM, OUTER_R_CM)
        ax.set_xlim(*EXTENT); ax.set_ylim(*EXTENT)
        ax.set_aspect("equal")
        label = "Left-Right (LR)" if cue == "LR" else "Top-Bottom (TB)"
        ax.set_title(f"Polarization Cue: {label}\n(n = {n} experiments)",
                     color="white", fontsize=11, fontweight="bold", pad=8)
        ax.set_xlabel("x (cm)", color="white", fontsize=10)
        ax.set_ylabel("y (cm)", color="white", fontsize=10)
        ax.tick_params(colors="white", labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor("#334")

        # scale bar
        ax.plot([20, 45], [-OUTER_R_CM * 1.08, -OUTER_R_CM * 1.08], color="white", lw=2.5)
        ax.text(32.5, -OUTER_R_CM * 1.08 - 2.5, "25 cm", ha="center", va="top",
                color="white", fontsize=9)

    fig.suptitle("Positional Density: LR vs TB Polarization Cue",
                 color="white", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "heatmap_lr_vs_tb.png", dpi=200,
                facecolor="#050520", bbox_inches="tight")
    plt.close()
    print("  ✓ heatmap_lr_vs_tb.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE E — 3-row summary panel (like Fig 6: overlay + heatmap + radial)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_summary_panel(groups):
    """
    3-column × 2-row comprehensive panel:
    Row 1: overlay trajectory (home vector + search)
    Row 2: heatmap density
    For LR_low_P, TB_low_P, all-combined
    """
    EXTENT = [-OUTER_R_CM * 1.15, OUTER_R_CM * 1.15]
    BINS   = 130
    cmap_traj = plt.cm.plasma
    col_configs = [
        ("LR_low_P",  "LR Cue — Low Pollen"),
        ("TB_low_P",  "TB Cue — Low Pollen"),
        ("all",       "All Conditions"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.patch.set_facecolor("#050520")

    for col, (cond, title) in enumerate(col_configs):
        traj_list = groups.get(cond, [])
        n = len(traj_list)

        # ── Row 0: trajectory overlay ──────────────────────────────────────
        ax = axes[0][col]
        ax.set_facecolor("#0a0a20")
        for traj in traj_list:
            if traj is None or len(traj) < 2:
                continue
            x, y = traj["x"].values, traj["y"].values
            nn = len(x)
            step = max(1, nn // 200)
            for i in range(0, nn - 1, step):
                t_norm = i / max(nn - 1, 1)
                ax.plot(x[i:i+2], y[i:i+2], color=cmap_traj(t_norm),
                        lw=0.7, alpha=0.45)
        draw_arena_dark(ax)
        ax.set_xlim(*EXTENT); ax.set_ylim(*EXTENT)
        ax.set_aspect("equal")
        ax.set_title(f"{title}\n(n={n})", color="white", fontsize=10, fontweight="bold")
        ax.set_xlabel("x (cm)", color="white", fontsize=9)
        ax.set_ylabel("y (cm)", color="white", fontsize=9)
        ax.tick_params(colors="white", labelsize=7)
        for sp in ax.spines.values(): sp.set_edgecolor("#334")
        ax.plot([20, 45], [-OUTER_R_CM*1.08]*2, color="white", lw=2)
        ax.text(32.5, -OUTER_R_CM*1.08-2, "25 cm", ha="center", va="top",
                color="white", fontsize=8)

        # ── Row 1: heatmap ─────────────────────────────────────────────────
        ax = axes[1][col]
        ax.set_facecolor("#050520")
        H = compute_heatmap(traj_list, EXTENT*2, BINS, blur_sigma=1.5,
                            clip_r=OUTER_R_CM * 1.1)
        if H is not None and H.max() > 0:
            H_norm = H / H.max()
            im = ax.imshow(H_norm.T, origin="lower", extent=EXTENT+EXTENT,
                           cmap=PAPER_CMAP, vmin=0.02, vmax=1.0,
                           aspect="equal", interpolation="bilinear")
            cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02, shrink=0.9)
            cbar.set_label("Density", color="white", fontsize=8)
            cbar.ax.yaxis.set_tick_params(color="white")
            plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")
            cbar.outline.set_edgecolor("white")
        else:
            ax.text(0, 0, "No data", ha="center", va="center", color="white", fontsize=10)

        draw_arena_dark(ax)
        ax.set_xlim(*EXTENT); ax.set_ylim(*EXTENT)
        ax.set_aspect("equal")
        ax.set_title(f"Density Map — {title}", color="white", fontsize=10, fontweight="bold")
        ax.set_xlabel("x (cm)", color="white", fontsize=9)
        ax.set_ylabel("y (cm)", color="white", fontsize=9)
        ax.tick_params(colors="white", labelsize=7)
        for sp in ax.spines.values(): sp.set_edgecolor("#334")
        ax.plot([20, 45], [-OUTER_R_CM*1.08]*2, color="white", lw=2)
        ax.text(32.5, -OUTER_R_CM*1.08-2, "25 cm", ha="center", va="top",
                color="white", fontsize=8)

    # Time colorbar for row 0
    sm = plt.cm.ScalarMappable(cmap=cmap_traj)
    sm.set_array([])
    cbar2 = fig.colorbar(sm, ax=axes[0].tolist(), orientation="vertical",
                          fraction=0.012, pad=0.01)
    cbar2.set_label("Time (dark=start, bright=end)", color="white", fontsize=9)
    cbar2.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar2.ax.yaxis.get_ticklabels(), color="white")
    cbar2.outline.set_edgecolor("white")

    fig.suptitle("Bumblebee Search Trajectories & Positional Density — Paper Fig 6 Style",
                 color="white", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "heatmap_paper_fig6_style.png", dpi=200,
                facecolor="#050520", bbox_inches="tight")
    plt.close()
    print("  ✓ heatmap_paper_fig6_style.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIGURE F — Radial density profile (as function of r)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_radial_density(groups):
    """
    Radial density: fraction of time spent at each distance from centre.
    Shows concentric ring occupancy as a line plot.
    """
    r_bins = np.linspace(0, OUTER_R_CM * 1.2, 60)
    r_centers = (r_bins[:-1] + r_bins[1:]) / 2

    cond_info = [
        ("LR_low_P",  "#4FC3F7", "-",  "LR Low-P"),
        ("LR_high_P", "#0D47A1", "--", "LR High-P"),
        ("TB_low_P",  "#FF7043", "-",  "TB Low-P"),
        ("TB_high_P", "#B71C1C", "--", "TB High-P"),
    ]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#0a0a1a")
    ax.set_facecolor("#0f0f2a")

    for cond, color, ls, label in cond_info:
        traj_list = groups.get(cond, [])
        all_r = []
        for traj in traj_list:
            if traj is not None:
                all_r.extend(traj["r"].clip(0, OUTER_R_CM * 1.2).values)
        if not all_r:
            continue
        counts, _ = np.histogram(all_r, bins=r_bins)
        counts = counts / max(counts.sum(), 1)  # normalize to probability
        ax.plot(r_centers, counts, color=color, linewidth=2.0, linestyle=ls,
                label=f"{label} (n={len(traj_list)})", alpha=0.9)

    ax.axvline(INNER_R_CM, color="white", linestyle=":", lw=1.2, alpha=0.5, label="Inner r=21 cm")
    ax.axvline(OUTER_R_CM, color="white", linestyle="--", lw=1.5, alpha=0.7, label="Outer r=42 cm")

    ax.set_xlabel("Distance from feeder (cm)", color="white", fontsize=11)
    ax.set_ylabel("Fraction of time", color="white", fontsize=11)
    ax.set_title("Radial Density Profile by Condition",
                 color="white", fontsize=13, fontweight="bold")
    ax.tick_params(colors="white", labelsize=9)
    for sp in ax.spines.values(): sp.set_edgecolor("#445")
    leg = ax.legend(fontsize=9, facecolor="#1a1a3a", labelcolor="white",
                    edgecolor="#445", loc="upper right")
    ax.set_xlim(0, OUTER_R_CM * 1.2)
    ax.set_ylim(bottom=0)

    fig.suptitle("Time Spent at Each Distance from Feeder",
                 color="white", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "heatmap_radial_density.png", dpi=200,
                facecolor="#0a0a1a", bbox_inches="tight")
    plt.close()
    print("  ✓ heatmap_radial_density.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  Paper-Style Heatmaps (Patel et al. 2022, Fig 6 style)")
    print("=" * 60)

    groups = load_all()
    print(f"\nGenerating heatmap figures → {RESULTS_DIR}")

    plot_combined_heatmap(groups)
    plot_per_condition_heatmaps(groups)
    plot_trajectory_overlays(groups)
    plot_lr_vs_tb_heatmap(groups)
    plot_summary_panel(groups)
    plot_radial_density(groups)

    print("\n" + "=" * 60)
    print("  Done! 6 heatmap figures saved.")
    print("=" * 60)


if __name__ == "__main__":
    main()
