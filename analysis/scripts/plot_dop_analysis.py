#!/usr/bin/env python3
"""
DoP and Circular Trajectory Analysis for Bumblebee Path Integration
===================================================================
This script:
1. Maps P (polarized light) and U (unpolarized light) to physical DoP values.
2. Recalculates robust inner and outer circle exit angles from coordinate trajectories.
3. Classifies trials into Strong DoP (DoP >= 0.10) and Weak DoP (DoP < 0.10).
4. Generates:
   - Fig A: Linear plot of Homing Accuracy vs. DoP (straightness and angular deviation).
   - Fig B: Overlaid trajectories for each unique condition setting.
   - Fig C: Polar plots of LR vs. TB rotation comparison.
   - Fig D: Individual bee trajectory grids.
   - Fig E: 4-panel grid for bee R13.
5. Updates summary_all_experiments.csv and summary_per_condition.csv.
"""

import json
import re
import warnings
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch
from pathlib import Path
from scipy import stats

warnings.filterwarnings("ignore")
matplotlib.use("Agg")

# ─── PATHS ────────────────────────────────────────────────────────────────────
V_OUTPUTS   = Path("/Users/yakkshit/Downloads/project/hiwi2/p1/V_OUTPUTS")
CACHE_PATH  = Path("/Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee_task/circle_config_cache.json")
RESULTS_DIR = Path("/Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee_task/analysis/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
INNER_R_CM   = 21.0
OUTER_R_CM   = 42.0
CM_PER_PIXEL = 0.1546

# ─── STYLE ────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.size": 9,
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "figure.dpi": 150,
    "savefig.dpi": 200,
})

# ─── DOP LOOKUP TABLES ────────────────────────────────────────────────────────
DOP_TB = {
    (0.0, 1.0): 0.07, (0.7, 1.0): 0.07, (1.3, 1.0): 0.08, (1.5, 1.0): 0.08,
    (1.8, 1.0): 0.10, (2.5, 1.0): 0.12, (3.5, 1.0): 0.14, (4.4, 1.0): 0.15,
    (8.0, 1.0): 0.19, (0.4, 2.0): 0.04, (0.9, 2.0): 0.07, (1.5, 2.0): 0.05,
    (8.0, 2.0): 0.12, (0.0, 8.0): 0.07, (3.8, 8.0): 0.07, (4.3, 8.0): 0.07,
    (7.7, 8.0): 0.08, (8.0, 8.0): 0.07, (8.0, 0.0): 1.0,  (0.1, 8.0): 0.05,
    (0.0, 2.0): 0.04, (0.6, 2.0): 0.04, (4.2, 8.0): 0.05, (4.4, 8.0): 0.05,
    (2.0, 1.0): 0.10, (4.2, 1.0): 0.12, (1.1, 1.0): 0.08, (5.0, 0.0): 1.0
}

DOP_LR = {
    (0.7, 1.0): 0.06, (2.0, 1.0): 0.10, (2.5, 1.0): 0.12, (3.5, 1.0): 0.14,
    (4.2, 1.0): 0.12, (4.4, 1.0): 0.12, (8.0, 1.0): 0.19, (0.0, 2.0): 0.04,
    (0.6, 2.0): 0.04, (1.5, 2.0): 0.05, (0.1, 8.0): 0.05, (3.8, 8.0): 0.04,
    (4.2, 8.0): 0.05, (4.4, 8.0): 0.05, (8.0, 8.0): 0.05, (8.0, 0.0): 1.0,
    (0.0, 1.0): 0.07, (1.3, 1.0): 0.08, (1.5, 1.0): 0.08, (1.8, 1.0): 0.10,
    (0.4, 2.0): 0.04, (0.9, 2.0): 0.07, (0.0, 8.0): 0.07, (4.3, 8.0): 0.05,
    (7.7, 8.0): 0.05, (1.1, 1.0): 0.08, (5.0, 0.0): 1.0
}

def get_dop_value(cue, P, U):
    if np.isnan(P) or np.isnan(U):
        return 0.05
    if U == 0.0:
        return 1.00
    
    cue_upper = str(cue).upper()
    P_r, U_r = round(float(P), 1), round(float(U), 1)
    
    # lookup map selection
    mapping = DOP_LR if "LR" in cue_upper else DOP_TB
    
    if (P_r, U_r) in mapping:
        return mapping[(P_r, U_r)]
    
    # fallback to Euclidean distance in (P, U) space
    keys = list(mapping.keys())
    dists = [np.hypot(P_r - k[0], U_r - k[1]) for k in keys]
    closest_key = keys[np.argmin(dists)]
    return mapping[closest_key]

# ─── HELPER FUNCTIONS ─────────────────────────────────────────────────────────

def diff_angle(a, b):
    """Circular distance between two angles in degrees."""
    return np.minimum(np.abs(a - b), 360 - np.abs(a - b))

def circular_mean_vector(angles_deg):
    """Return (mean_angle_deg, mean_vector_length R)."""
    if len(angles_deg) == 0:
        return np.nan, np.nan
    rad = np.radians(angles_deg)
    s = np.mean(np.sin(rad))
    c = np.mean(np.cos(rad))
    mu = np.degrees(np.arctan2(s, c)) % 360
    R = np.sqrt(s**2 + c**2)
    return mu, R

def rayleigh_p_value(angles_deg):
    """Rayleigh test of uniformity p-value."""
    n = len(angles_deg)
    if n < 3:
        return 1.0
    _, R = circular_mean_vector(angles_deg)
    z = n * (R**2)
    p = np.exp(-z)
    return p

def load_cache():
    if CACHE_PATH.exists():
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}

def parse_folder_name(name):
    n = name.strip()
    dt_key = n[:19]
    cue = "LR" if re.search(r'\bLR\b', n, re.I) else ("TB" if re.search(r'\bTB\b', n, re.I) else "unknown")
    p_match = re.search(r'P\s*([0-9]+(?:\.[0-9]+)?)', n, re.I)
    P = float(p_match.group(1)) if p_match else np.nan
    u_match = re.search(r'U\s*([0-9]+(?:\.[0-9]+)?)', n, re.I)
    U = float(u_match.group(1)) if u_match else np.nan
    
    remainder = n[20:].strip()
    bee_match = re.search(r'([RWGrwg]\s*\d+)', remainder)
    bee_id = bee_match.group(1).replace(" ", "") if bee_match else "unknown"
    return dict(dt_key=dt_key, bee_id=bee_id, cue=cue, P=P, U=U)

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
        return valid.reset_index(drop=True)
    except Exception:
        return None

def draw_circular_arena(ax, inner_r=INNER_R_CM, outer_r=OUTER_R_CM, bg_color="white"):
    """Draw circular arena boundaries."""
    ax.add_patch(Circle((0, 0), inner_r, fill=False, edgecolor="#bbb", lw=1.0, ls="--", zorder=2))
    ax.add_patch(Circle((0, 0), outer_r, fill=False, edgecolor="#777", lw=1.2, ls="-", zorder=2))
    ax.plot(0, 0, "o", color="#FFA000", ms=5, zorder=5)  # Feeder
    ax.set_xlim(-outer_r * 1.15, outer_r * 1.15)
    ax.set_ylim(-outer_r * 1.15, outer_r * 1.15)
    ax.set_aspect("equal")
    ax.set_facecolor(bg_color)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.set_xticks([]); ax.set_yticks([])

# ─── DATA INGESTION & ROBUST CALCULATION ──────────────────────────────────────

def ingest_data():
    cache = load_cache()
    records = []
    trajectories = {}
    
    print("Ingesting tracked folders from V_OUTPUTS...")
    folders = sorted([f for f in V_OUTPUTS.iterdir() if f.is_dir() and not f.name.startswith(".")])
    
    for folder in folders:
        meta = parse_folder_name(folder.name)
        data_dir = folder / "data"
        if not data_dir.exists():
            continue
        
        id0_file = next((f for f in data_dir.glob("*id0_new.csv")), None)
        if not id0_file:
            continue
            
        dt_key = meta["dt_key"]
        center = None
        # lookup center
        for k in [dt_key, dt_key + ".mp4", dt_key + ".mkv"]:
            if k in cache:
                center = (cache[k][0] * CM_PER_PIXEL, cache[k][1] * CM_PER_PIXEL)
                break
        if center is None:
            short = dt_key[:16]
            for k in cache:
                if k.startswith(short):
                    center = (cache[k][0] * CM_PER_PIXEL, cache[k][1] * CM_PER_PIXEL)
                    break
        if center is None:
            continue
            
        traj = load_trajectory(id0_file, *center)
        if traj is None or len(traj) < 10:
            continue
            
        # Add distance to center if not present
        if "dist_to_center_cm" not in traj.columns:
            traj["dist_to_center_cm"] = traj["r"]
            
        # ── ROBUST EXIT ANGLES DIRECTLY FROM TRAJECTORY ──
        # 1. Inner circle crossing (r > 21 cm)
        inner_cross = traj[traj["dist_to_center_cm"] > INNER_R_CM]
        inner_exit_angle = np.nan
        if not inner_cross.empty:
            pt = inner_cross.iloc[0]
            inner_exit_angle = (np.degrees(np.arctan2(pt["y"], pt["x"])) + 360) % 360
            
        # 2. Outer circle crossing (r > 42 cm)
        outer_cross = traj[traj["dist_to_center_cm"] > OUTER_R_CM]
        outer_exit_angle = np.nan
        if not outer_cross.empty:
            pt = outer_cross.iloc[0]
            outer_exit_angle = (np.degrees(np.arctan2(pt["y"], pt["x"])) + 360) % 360
            
        # Path metrics
        path_len = float(np.sum(np.sqrt(np.diff(traj["x"])**2 + np.diff(traj["y"])**2))) if len(traj) > 1 else np.nan
        displacement = float(np.sqrt(traj["x"].iloc[-1]**2 + traj["y"].iloc[-1]**2)) if len(traj) > 0 else np.nan
        straightness = displacement / path_len if (path_len and path_len > 0) else np.nan
        mean_speed = float(traj["speed"].mean()) if "speed" in traj.columns else np.nan
        
        # DoP Mapping
        dop = get_dop_value(meta["cue"], meta["P"], meta["U"])
        dop_strength = "strong" if dop >= 0.10 else "weak"
        
        records.append({
            "folder": folder.name,
            "bee_id": meta["bee_id"],
            "cue": meta["cue"],
            "P": meta["P"],
            "U": meta["U"],
            "dop": dop,
            "dop_strength": dop_strength,
            "exit_angle_deg": outer_exit_angle,
            "inner_exit_angle_deg": inner_exit_angle,
            "path_len_cm": path_len,
            "displacement_cm": displacement,
            "straightness": straightness,
            "mean_speed_cms": mean_speed,
            "max_radius_cm": traj["r"].max()
        })
        trajectories[folder.name] = traj
        
    df = pd.DataFrame(records)
    print(f"Loaded {len(df)} trials successfully.")
    return df, trajectories

# ─── PLOT GENERATION ──────────────────────────────────────────────────────────

# ═══════════════════════════════════════════════════════════════════════════════
#  PLOT 1: Homing Accuracy vs. DoP (Linear Plot)
# ═══════════════════════════════════════════════════════════════════════════════
def plot_accuracy_vs_dop(df):
    """Plot straightness and angular deviation vs DoP."""
    print("Generating Homing Accuracy vs DoP linear plot...")
    
    # Exclude training trials (dop == 1.0) to see behavior under mixed stimulus
    test_df = df[df["dop"] < 1.0].copy()
    if test_df.empty:
        return
        
    # Expected target axis:
    # LR expected = 180 (nest)
    # TB expected = 90 or 270 (rotated fictive nest)
    # Let's calculate the deviation from fictive nest and real home
    deviations_home = []
    deviations_fictive = []
    
    for _, row in test_df.iterrows():
        ang = row["inner_exit_angle_deg"]
        cue = row["cue"]
        if np.isnan(ang):
            deviations_home.append(np.nan)
            deviations_fictive.append(np.nan)
            continue
            
        dev_h = diff_angle(ang, 180)
        deviations_home.append(dev_h)
        
        expected_fictive = 180 if cue == "LR" else 90
        dev_f = min(diff_angle(ang, expected_fictive), diff_angle(ang, expected_fictive + 180))
        deviations_fictive.append(dev_f)
        
    test_df["dev_home"] = deviations_home
    test_df["dev_fictive"] = deviations_fictive
    
    # Group by DoP and compute mean metrics
    grouped = test_df.groupby("dop").agg(
        mean_straightness=("straightness", "mean"),
        std_straightness=("straightness", "std"),
        mean_dev_home=("dev_home", "mean"),
        mean_dev_fictive=("dev_fictive", "mean"),
        count=("dop", "size")
    ).reset_index()
    
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    
    # Panel A: Straightness vs DoP
    ax = axes[0]
    ax.errorbar(grouped["dop"], grouped["mean_straightness"], 
                yerr=grouped["std_straightness"]/np.sqrt(grouped["count"]),
                fmt="-o", color="#1976D2", elinewidth=1.5, capsize=3, label="Mean Straightness")
    ax.set_xlabel("Degree of Polarization (DoP)")
    ax.set_ylabel("Mean Straightness (d/L)")
    ax.set_title("Path Straightness vs. DoP")
    ax.grid(True, linestyle=":", alpha=0.6)
    
    # Panel B: Angular Deviation vs DoP
    ax = axes[1]
    ax.plot(grouped["dop"], grouped["mean_dev_home"], "-o", color="#D32F2F", label="Deviation from Real Home (180°)")
    ax.plot(grouped["dop"], grouped["mean_dev_fictive"], "-s", color="#388E3C", label="Deviation from Fictive Target (LR 180° / TB 90°)")
    ax.set_xlabel("Degree of Polarization (DoP)")
    ax.set_ylabel("Mean Angular Deviation (degrees)")
    ax.set_title("Homing Accuracy vs. DoP")
    ax.legend(frameon=True, fontsize=8)
    ax.grid(True, linestyle=":", alpha=0.6)
    
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "homing_accuracy_vs_dop.png", dpi=200)
    plt.close()
    print("  ✓ homing_accuracy_vs_dop.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  PLOT 2: Summary Trajectory Plots per Condition Setting
# ═══════════════════════════════════════════════════════════════════════════════
def plot_condition_summaries(df, trajectories):
    """Generate summary overlaid trajectories for each unique setting."""
    print("Generating overlaid condition summaries...")
    cond_dir = RESULTS_DIR / "conditions"
    cond_dir.mkdir(exist_ok=True)
    
    # Group by setting: cue, P, U
    unique_settings = df.groupby(["cue", "P", "U"]).size().reset_index()
    
    for _, row in unique_settings.iterrows():
        cue = row["cue"]
        P, U = row["P"], row["U"]
        if np.isnan(P) or np.isnan(U):
            continue
            
        sub = df[(df["cue"] == cue) & (df["P"] == P) & (df["U"] == U)]
        dop = get_dop_value(cue, P, U)
        
        fig, ax = plt.subplots(figsize=(5, 5))
        draw_circular_arena(ax)
        
        for _, trial in sub.iterrows():
            traj = trajectories.get(trial["folder"])
            if traj is not None:
                ax.plot(traj["x"], traj["y"], lw=0.8, alpha=0.5, color="#1E88E5" if cue == "LR" else "#E53935")
                
                # plot exit coordinates if valid
                inner_cross = traj[traj["dist_to_center_cm"] > INNER_R_CM]
                if not inner_cross.empty:
                    pt = inner_cross.iloc[0]
                    ax.plot(pt["x"], pt["y"], "o", color="blue" if cue == "LR" else "red", ms=3, alpha=0.8)
                    
        ax.set_title(f"Cue: {cue} | p{P} u{U} | DoP = {dop:.2f}\n(n = {len(sub)} trials)")
        
        # save name clean
        safe_name = f"summary_{cue}_p{P}_u{U}.png".replace(".0", "").replace(" ", "")
        plt.savefig(cond_dir / safe_name, dpi=150, bbox_inches="tight")
        plt.close()
        
    print(f"  ✓ Saved condition summary overlays in {cond_dir}")


# ═══════════════════════════════════════════════════════════════════════════════
#  PLOT 3: Summary Polar Plots of LR vs. TB Rotation
# ═══════════════════════════════════════════════════════════════════════════════
def plot_polar_rotation_check(df):
    """Polar plot comparing LR vs TB exit direction under strong DoP."""
    print("Generating LR vs TB Polar rotation check plots...")
    
    strong_df = df[df["dop_strength"] == "strong"].copy()
    
    fig, axes = plt.subplots(1, 2, figsize=(10, 5), subplot_kw={'projection': 'polar'})
    
    for idx, cue in enumerate(["LR", "TB"]):
        ax = axes[idx]
        sub = strong_df[strong_df["cue"] == cue]
        angles = sub["inner_exit_angle_deg"].dropna().values
        
        # convert to radians for polar plot
        rad = np.radians(angles)
        
        # Plot polar histogram
        bars = ax.hist(rad, bins=16, bottom=1, color="#1976D2" if cue == "LR" else "#D32F2F", 
                       edgecolor="white", alpha=0.8)
        
        # calculate and draw mean vector arrow
        mu, R = circular_mean_vector(angles)
        p_val = rayleigh_p_value(angles)
        
        if not np.isnan(mu):
            arrow_len = R * max(bars[0]) if len(bars[0]) > 0 else R * 5
            ax.annotate("", xy=(np.radians(mu), arrow_len), xytext=(0, 0),
                        arrowprops=dict(facecolor="black", edgecolor="black", 
                                        arrowstyle="->", lw=2, zorder=5))
            
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_title(f"{cue} Cue (Strong DoP)\nMean Angle = {mu:.1f}° | R = {R:.2f}\nRayleigh p = {p_val:.4f}\nn = {len(angles)} exits",
                     fontsize=9, pad=10)
        
    plt.suptitle("Rotation Test: Homing Axis under 90° Stimulus Shift", fontsize=12, y=1.02)
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "polar_rotation_check.png", dpi=200, bbox_inches="tight")
    plt.close()
    print("  ✓ polar_rotation_check.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  PLOT 4: Individual Bee Trajectory Grids
# ═══════════════════════════════════════════════════════════════════════════════
def plot_individual_grids(df, trajectories):
    """Generate grids of circular plots per individual bee across conditions."""
    print("Generating individual bee trajectory grids...")
    ind_dir = RESULTS_DIR / "individual"
    ind_dir.mkdir(exist_ok=True)
    
    # filter to bees with at least 3 trials
    bee_counts = df["bee_id"].value_counts()
    eligible_bees = bee_counts[bee_counts >= 3].index
    
    for bee in eligible_bees:
        if bee == "unknown":
            continue
            
        sub = df[df["bee_id"] == bee].sort_values(["cue", "dop"])
        n_trials = len(sub)
        
        cols = 4
        rows = int(np.ceil(n_trials / cols))
        
        fig, axes = plt.subplots(rows, cols, figsize=(cols*2.5, rows*2.5))
        axes_flat = axes.flatten() if n_trials > 1 else [axes]
        
        for idx, (_, trial) in enumerate(sub.iterrows()):
            ax = axes_flat[idx]
            draw_circular_arena(ax)
            
            traj = trajectories.get(trial["folder"])
            if traj is not None:
                ax.plot(traj["x"], traj["y"], lw=0.8, color="#2196F3" if trial["cue"] == "LR" else "#F44336")
                
                # Highlight exit direction
                ang = trial["inner_exit_angle_deg"]
                if not np.isnan(ang):
                    ax.plot(INNER_R_CM * np.cos(np.radians(ang)), INNER_R_CM * np.sin(np.radians(ang)), 
                            "o", color="black", ms=4, zorder=5)
                    
            ax.set_title(f"DoP: {trial['dop']:.2f} ({trial['cue']})\nAngle: {trial['inner_exit_angle_deg']:.1f}°", 
                         fontsize=7)
            
        # turn off unused axes
        for idx in range(n_trials, len(axes_flat)):
            axes_flat[idx].set_axis_off()
            
        plt.suptitle(f"Individual Navigation Profiles — Bee: {bee}\n(Total: {n_trials} trials)", 
                     fontsize=12, y=1.02)
        plt.tight_layout()
        plt.savefig(ind_dir / f"bee_{bee}_trajectories.png", dpi=150, bbox_inches="tight")
        plt.close()
        
    print(f"  ✓ Saved individual bee profile grids in {ind_dir}")


# ═══════════════════════════════════════════════════════════════════════════════
#  PLOT 5: R13 Four-Panel Analysis (Low DoP, High DoP, LR, TB)
# ═══════════════════════════════════════════════════════════════════════════════
def plot_r13_grid(df, trajectories):
    """Dedicated 4-panel analysis grid for bee R13."""
    print("Generating dedicated R13 four-panel grid...")
    r13_df = df[df["bee_id"] == "R13"]
    if r13_df.empty:
        print("  ✗ Bee R13 data not found!")
        return
        
    fig, axes = plt.subplots(2, 2, figsize=(9, 9))
    
    # 1. Low DoP (DoP < 0.10)
    ax = axes[0][0]
    draw_circular_arena(ax)
    low_dop = r13_df[r13_df["dop_strength"] == "weak"]
    for _, row in low_dop.iterrows():
        t = trajectories.get(row["folder"])
        if t is not None:
            ax.plot(t["x"], t["y"], lw=0.7, color="#78909C", alpha=0.7)
            ang = row["inner_exit_angle_deg"]
            if not np.isnan(ang):
                ax.plot(INNER_R_CM * np.cos(np.radians(ang)), INNER_R_CM * np.sin(np.radians(ang)), 
                        "o", color="#37474F", ms=4, zorder=5)
    ax.set_title(f"R13 — Low DoP (DoP < 0.10)\nn = {len(low_dop)} trials")
    
    # 2. High DoP (DoP >= 0.10)
    ax = axes[0][1]
    draw_circular_arena(ax)
    high_dop = r13_df[r13_df["dop_strength"] == "strong"]
    for _, row in high_dop.iterrows():
        t = trajectories.get(row["folder"])
        if t is not None:
            ax.plot(t["x"], t["y"], lw=0.7, color="#FF7043", alpha=0.7)
            ang = row["inner_exit_angle_deg"]
            if not np.isnan(ang):
                ax.plot(INNER_R_CM * np.cos(np.radians(ang)), INNER_R_CM * np.sin(np.radians(ang)), 
                        "o", color="#D84315", ms=4, zorder=5)
    ax.set_title(f"R13 — High DoP (DoP ≥ 0.10)\nn = {len(high_dop)} trials")
    
    # 3. LR Cue
    ax = axes[1][0]
    draw_circular_arena(ax)
    lr_cue = r13_df[r13_df["cue"] == "LR"]
    for _, row in lr_cue.iterrows():
        t = trajectories.get(row["folder"])
        if t is not None:
            ax.plot(t["x"], t["y"], lw=0.7, color="#29B6F6", alpha=0.7)
            ang = row["inner_exit_angle_deg"]
            if not np.isnan(ang):
                ax.plot(INNER_R_CM * np.cos(np.radians(ang)), INNER_R_CM * np.sin(np.radians(ang)), 
                        "o", color="#0277BD", ms=4, zorder=5)
    ax.set_title(f"R13 — LR Cue (Expected: 180° / 0°)\nn = {len(lr_cue)} trials")
    
    # 4. TB Cue
    ax = axes[1][1]
    draw_circular_arena(ax)
    tb_cue = r13_df[r13_df["cue"] == "TB"]
    for _, row in tb_cue.iterrows():
        t = trajectories.get(row["folder"])
        if t is not None:
            ax.plot(t["x"], t["y"], lw=0.7, color="#EC407A", alpha=0.7)
            ang = row["inner_exit_angle_deg"]
            if not np.isnan(ang):
                ax.plot(INNER_R_CM * np.cos(np.radians(ang)), INNER_R_CM * np.sin(np.radians(ang)), 
                        "o", color="#C2185B", ms=4, zorder=5)
    ax.set_title(f"R13 — TB Cue (Expected: 90° / 270°)\nn = {len(tb_cue)} trials")
    
    plt.suptitle("Dedicated Navigational Profiles: Bee R13", fontsize=13, y=1.01)
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "bee_r13_four_panel.png", dpi=200, bbox_inches="tight")
    plt.close()
    print("  ✓ bee_r13_four_panel.png")

# ─── UPDATE CSV SUMMARIES ─────────────────────────────────────────────────────

def update_csv_summaries(df):
    """Write corrected summary tables to results folder."""
    print("Exporting updated CSV summaries...")
    
    # 1. Export summary_all_experiments.csv
    df.to_csv(RESULTS_DIR / "summary_all_experiments.csv", index=False)
    print(f"  ✓ summary_all_experiments.csv ({len(df)} rows)")
    
    # 2. Export summary_per_condition.csv (aggregated by cue and DoP strength)
    test_df = df[df["dop"] < 1.0].copy()
    
    cond_rows = []
    for (cue, dop_strength), sub in test_df.groupby(["cue", "dop_strength"]):
        angles = sub["inner_exit_angle_deg"].dropna().values
        mu, R = circular_mean_vector(angles)
        p_val = rayleigh_p_value(angles)
        
        cond_rows.append({
            "condition": f"{cue}_{dop_strength}_DoP",
            "cue": cue,
            "dop_strength": dop_strength,
            "n_total": len(sub),
            "n_with_exit": len(angles),
            "mean_dir_deg": round(mu, 2) if not np.isnan(mu) else np.nan,
            "mean_vector_R": round(R, 4) if not np.isnan(R) else np.nan,
            "rayleigh_p": round(p_val, 6),
            "mean_speed_cms": round(sub["mean_speed_cms"].mean(), 3),
            "mean_path_len_cm": round(sub["path_len_cm"].mean(), 2),
            "mean_straightness": round(sub["straightness"].mean(), 4)
        })
        
    cond_df = pd.DataFrame(cond_rows)
    cond_df.to_csv(RESULTS_DIR / "summary_per_condition.csv", index=False)
    print(f"  ✓ summary_per_condition.csv ({len(cond_df)} rows)")

# ─── MAIN RUNNER ──────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  DoP & Trajectory Analysis Execution")
    print("=" * 60)
    
    df, trajectories = ingest_data()
    if df.empty:
        print("ERROR: No data loaded!")
        return
        
    update_csv_summaries(df)
    
    plot_accuracy_vs_dop(df)
    plot_condition_summaries(df, trajectories)
    plot_polar_rotation_check(df)
    plot_individual_grids(df, trajectories)
    plot_r13_grid(df, trajectories)
    
    print("\n" + "=" * 60)
    print("  Done! All DoP & trajectory figures saved.")
    print("=" * 60)

if __name__ == "__main__":
    main()
