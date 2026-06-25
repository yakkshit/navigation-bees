#!/usr/bin/env python3
"""
Post-process TRex tracking CSVs: add arena circle events and write *_id0_new.csv.

Uses TRex-exported kinematic fields (see https://trex.run/docs/formats.html):
  - X/Y (cm), ANGLE, SPEED, missing, time, frame, num_pixels
  - BORDER_DISTANCE#pcentroid — distance to outer arena edge (cm) when cam mask is set
  - MIDLINE_OFFSET, VX/VY, tracklet_id, etc. are preserved unchanged

Arena geometry (circle_config.json / arena_config.py):
  - Inner circle: 42 cm diameter (21 cm radius)
  - Outer circle: 84 cm diameter (42 cm radius) — active tracking boundary

Outputs (original *_id0.csv is never modified):
  - data/{video}_id0_new.csv   — all TRex columns + event/zone columns
  - data/{video}_events.csv    — one row per detected transition event
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
import os

from arena_config import (
    find_column,
    load_circle_config,
    arena_center_cm,
)

SCRIPT_DIR = Path(__file__).parent
env_path = SCRIPT_DIR.parent / ".env.local"
if env_path.exists():
    load_dotenv(env_path)
elif (SCRIPT_DIR.parent / ".env").exists():
    load_dotenv(SCRIPT_DIR.parent / ".env")

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(SCRIPT_DIR.parent.parent / "V_OUTPUTS")))
INPUT_VIDEO_DIR = Path(os.getenv("INPUT_DIR", str(SCRIPT_DIR.parent.parent / "Videos")))

EVENT_TYPES = (
    "video_entry",
    "outer_entry",
    "inner_entry",
    "inner_exit",
    "outer_exit",
)


def parse_settings(settings_path: Path) -> dict:
    values = {"cm_per_pixel": 0.1546, "meta_real_width": 197.89}
    if not settings_path.exists():
        return values
    with open(settings_path) as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key, val = key.strip(), val.strip().strip('"')
            if key in ("cm_per_pixel", "meta_real_width"):
                try:
                    values[key] = float(val)
                except ValueError:
                    pass
    return values


def resolve_settings_path(video_dir: Path, csv_path: Path) -> Path:
    candidates = [
        video_dir / f"{video_dir.name}.settings",
        video_dir / f"{csv_path.stem.rsplit('_id', 1)[0]}.settings",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def compute_dist_to_center(df: pd.DataFrame, cfg: dict, cm_per_pixel: float, width: int, height: int, video_dir: Path | None = None) -> pd.Series:
    """Compute radial distance from arena centre for every row."""
    cols = list(df.columns)
    x_col = find_column(cols, "X (cm)", "X#pcentroid", "X#wcentroid", "X")
    y_col = find_column(cols, "Y (cm)", "Y#pcentroid", "Y#wcentroid", "Y")
    border_col = find_column(cols, "BORDER_DISTANCE#pcentroid", "BORDER_DISTANCE#wcentroid", "BORDER_DISTANCE")

    outer_r = cfg["outer_radius_cm"]
    cx_cm, cy_cm = arena_center_cm(width, height, cm_per_pixel, cfg, video_dir)

    dist = pd.Series(np.nan, index=df.index, dtype=float)

    if x_col and y_col:
        x = pd.to_numeric(df[x_col], errors="coerce")
        y = pd.to_numeric(df[y_col], errors="coerce")
        eucl = np.hypot(x - cx_cm, y - cy_cm)
        eucl = eucl.where(x.notna() & y.notna() & np.isfinite(x) & np.isfinite(y))
        dist = eucl

    if border_col is not None:
        border = pd.to_numeric(df[border_col], errors="coerce")
        valid_border = border.notna() & np.isfinite(border)
        border_dist = outer_r - border.loc[valid_border]
        dist = dist.fillna(border_dist)

    return dist


def detect_zone(prev_in: bool | None, curr_in: bool, debounce: int, streak: int) -> tuple[str | None, int]:
    """Return event name on confirmed zone transition."""
    if prev_in is None:
        return None, streak
    if curr_in == prev_in:
        return None, 0
    streak += 1
    if streak < debounce:
        return None, streak
    if curr_in and not prev_in:
        return "enter", debounce
    if not curr_in and prev_in:
        return "exit", debounce
    return None, streak


def process_dataframe(
    df: pd.DataFrame,
    cfg: dict,
    cm_per_pixel: float,
    width: int = 1280,
    height: int = 720,
    video_dir: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Add zone/event columns; return (enriched_df, events_df)."""
    out = df.copy()
    frame_col = find_column(list(out.columns), "frame") or "frame"
    time_col = find_column(list(out.columns), "time")
    x_col = find_column(list(out.columns), "X (cm)", "X#pcentroid", "X")
    y_col = find_column(list(out.columns), "Y (cm)", "Y#pcentroid", "Y")
    angle_col = find_column(list(out.columns), "ANGLE")
    speed_col = find_column(list(out.columns), "SPEED (cm/s)", "SPEED#pcentroid", "SPEED")
    missing_col = find_column(list(out.columns), "missing") or "missing"

    out = out.sort_values(frame_col).reset_index(drop=True)
    missing = pd.to_numeric(out[missing_col], errors="coerce").fillna(1).astype(int)
    detected = missing == 0

    inner_r = cfg["inner_radius_cm"]
    outer_r = cfg["outer_radius_cm"]
    debounce = int(cfg.get("event_debounce_frames", 2))
    gap_frames = int(cfg.get("visit_gap_frames", 8))

    dist = compute_dist_to_center(out, cfg, cm_per_pixel, width, height, video_dir)

    out["dist_to_center_cm"] = dist.round(4)
    out["in_inner_circle"] = ((dist <= inner_r) & detected).astype(int)
    out["in_outer_circle"] = ((dist <= outer_r) & detected).astype(int)
    out["arena_tracked"] = out["in_outer_circle"]
    out["outside_arena"] = (detected & (out["in_outer_circle"] == 0)).astype(int)

    # Position-based heading angle estimation
    n = len(out)
    heading_angles = np.full(n, np.nan)
    last_valid_angle = 0.0
    step = 3
    x_vals = pd.to_numeric(out[x_col], errors="coerce").values if x_col else np.full(n, np.nan)
    y_vals = pd.to_numeric(out[y_col], errors="coerce").values if y_col else np.full(n, np.nan)
    speed_vals = pd.to_numeric(out[speed_col], errors="coerce").values if speed_col else np.zeros(n)
    missing_vals = missing.values

    # Smooth the centroid positions to reduce noise/jitter before angle calculation.
    # We temporarily interpolate small gaps so the rolling average stays continuous.
    window_size = 5
    x_series = pd.Series(x_vals)
    y_series = pd.Series(y_vals)
    x_smooth = x_series.interpolate(method="linear", limit=5).rolling(window=window_size, min_periods=1, center=True).mean().values
    y_smooth = y_series.interpolate(method="linear", limit=5).rolling(window=window_size, min_periods=1, center=True).mean().values

    for i in range(n):
        if missing_vals[i] == 0:
            prev_idx = max(0, i - step)
            while prev_idx < i and missing_vals[prev_idx] != 0:
                prev_idx += 1
            
            dx = x_smooth[i] - x_smooth[prev_idx]
            dy = y_smooth[i] - y_smooth[prev_idx]
            
            if speed_vals[i] > 1.5 and np.isfinite(dx) and np.isfinite(dy) and (dx != 0 or dy != 0):
                last_valid_angle = np.arctan2(dy, dx)
            heading_angles[i] = last_valid_angle
        else:
            heading_angles[i] = np.nan
    out["HEADING_ANGLE"] = np.round(heading_angles, 4)

    event_col = pd.Series("", index=out.index, dtype=object)
    for et in EVENT_TYPES:
        out[f"is_{et}"] = 0

    events: list[dict] = []

    def row_values(i: int) -> dict:
        row = out.iloc[i]
        frame = int(row[frame_col]) if pd.notna(row[frame_col]) else i
        t = float(row[time_col]) if time_col and pd.notna(row[time_col]) else np.nan
        x_val = float(row[x_col]) if x_col and pd.notna(row[x_col]) and np.isfinite(row[x_col]) else np.nan
        y_val = float(row[y_col]) if y_col and pd.notna(row[y_col]) and np.isfinite(row[y_col]) else np.nan
        angle_val = float(row[angle_col]) if angle_col and pd.notna(row[angle_col]) and np.isfinite(row[angle_col]) else np.nan
        heading_val = float(row["HEADING_ANGLE"]) if "HEADING_ANGLE" in row.index and pd.notna(row["HEADING_ANGLE"]) else np.nan
        speed_val = float(row[speed_col]) if speed_col and pd.notna(row[speed_col]) and np.isfinite(row[speed_col]) else np.nan
        dist_val = float(dist.iat[i]) if pd.notna(dist.iat[i]) else np.nan
        return {
            "frame": frame,
            "time_s": round(t, 4) if np.isfinite(t) else np.nan,
            "X_cm": round(x_val, 4) if np.isfinite(x_val) else np.nan,
            "Y_cm": round(y_val, 4) if np.isfinite(y_val) else np.nan,
            "dist_to_center_cm": round(dist_val, 4) if np.isfinite(dist_val) else np.nan,
            "ANGLE_rad": round(angle_val, 4) if np.isfinite(angle_val) else np.nan,
            "HEADING_ANGLE_rad": round(heading_val, 4) if np.isfinite(heading_val) else np.nan,
            "SPEED_cm_s": round(speed_val, 4) if np.isfinite(speed_val) else np.nan,
        }

    def record(i: int, event_type: str):
        event_col.iat[i] = event_type if not event_col.iat[i] else f"{event_col.iat[i]};{event_type}"
        out.at[i, f"is_{event_type}"] = 1
        payload = row_values(i)
        payload["event"] = event_type
        events.append(payload)

    arena = out["arena_tracked"].astype(bool).tolist()
    inner = out["in_inner_circle"].astype(bool).tolist()
    n = len(out)

    video_entry_done = False
    in_visit = False
    outside_streak = 0
    inside_streak = 0
    prev_inner: bool | None = None
    inner_streak = 0

    for i in range(n):
        tracked = arena[i]
        in_in = inner[i] if tracked else False

        if tracked:
            outside_streak = 0
            inside_streak += 1
            if not in_visit and inside_streak >= debounce:
                in_visit = True
                if not video_entry_done:
                    record(i, "video_entry")
                    video_entry_done = True
                record(i, "outer_entry")
                if in_in:
                    record(i, "inner_entry")
                    prev_inner = True
                    inner_streak = debounce
                else:
                    prev_inner = False
                    inner_streak = 0
            elif in_visit and prev_inner is not None:
                trans, inner_streak = detect_zone(prev_inner, in_in, debounce, inner_streak)
                if trans == "enter":
                    record(i, "inner_entry")
                    inner_streak = debounce
                elif trans == "exit":
                    record(i, "inner_exit")
                    inner_streak = debounce
                prev_inner = in_in
        else:
            inside_streak = 0
            outside_streak += 1
            if in_visit and outside_streak >= gap_frames:
                record(i, "outer_exit")
                in_visit = False
                prev_inner = None
                inner_streak = 0

    if in_visit and n > 0:
        record(n - 1, "outer_exit")

    out["circle_event"] = event_col
    events_df = pd.DataFrame(events)
    return out, events_df


def get_video_dimensions(video_dir: Path, settings: dict) -> tuple[int, int]:
    width = int(settings.get("meta_real_width", 1280))
    height = 720
    settings_path = video_dir / f"{video_dir.name}.settings"
    if settings_path.exists():
        with open(settings_path) as f:
            for line in f:
                if line.strip().startswith("meta_source_path"):
                    _, val = line.split("=", 1)
                    src = Path(val.strip().strip('"'))
                    if src.exists():
                        try:
                            import cv2

                            cap = cv2.VideoCapture(str(src))
                            if cap.isOpened():
                                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or width
                                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or height
                            cap.release()
                        except Exception:
                            pass
                    break
    return width, height


def process_video_dir(video_dir: Path, cfg: dict | None = None) -> bool:
    cfg = cfg or load_circle_config(video_dir.name)
    data_dir = video_dir / "data"
    if not data_dir.exists():
        print(f"  ✗ no data/ in {video_dir.name}")
        return False

    id_csvs = sorted(data_dir.glob("*_id0.csv"))
    id_csvs = [p for p in id_csvs if not p.name.endswith("_id0_new.csv")]
    if not id_csvs:
        print(f"  ✗ no *_id0.csv in {video_dir.name}")
        return False

    csv_path = id_csvs[0]
    settings_path = resolve_settings_path(video_dir, csv_path)
    settings = parse_settings(settings_path)
    cm_per_pixel = settings["cm_per_pixel"]
    width, height = get_video_dimensions(video_dir, settings)

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"  ✗ read failed: {e}")
        return False

    enriched, events = process_dataframe(df, cfg, cm_per_pixel, width, height, video_dir)

    stem = csv_path.stem  # e.g. video_id0
    new_csv = data_dir / f"{stem}_new.csv"
    events_csv = data_dir / f"{csv_path.stem.rsplit('_id', 1)[0]}_events.csv"

    enriched.to_csv(new_csv, index=False)
    events.to_csv(events_csv, index=False)

    n_det = int((enriched["arena_tracked"] == 1).sum()) if "arena_tracked" in enriched.columns else 0
    n_total = len(enriched)
    pct = 100.0 * n_det / n_total if n_total else 0.0
    print(f"  ✓ {video_dir.name}")
    print(f"    → {new_csv.name} ({n_total} frames, arena tracked {n_det} = {pct:.1f}%)")
    print(f"    → {events_csv.name} ({len(events)} events)")
    if len(events):
        for _, ev in events.iterrows():
            print(f"      • {ev['event']:12s} frame {int(ev['frame']):6d}  t={ev['time_s']}s  d={ev['dist_to_center_cm']}cm")
    return True


def process_all(output_dir: Path | None = None, video_name: str | None = None) -> int:
    out_root = output_dir or OUTPUT_DIR
    cfg = load_circle_config()
    print(f"Arena: inner Ø{cfg['inner_diameter_cm']}cm, outer Ø{cfg['outer_diameter_cm']}cm")
    print(f"Output: {out_root}\n")

    if video_name:
        dirs = [d for d in out_root.iterdir() if d.is_dir() and video_name in d.name]
    else:
        dirs = sorted(d for d in out_root.iterdir() if d.is_dir() and (d / "data").exists())

    if not dirs:
        print("No video output folders found.")
        return 1

    ok = sum(process_video_dir(d, None) for d in dirs)
    print(f"\nDone: {ok}/{len(dirs)} video(s) post-processed.")
    return 0 if ok == len(dirs) else 1


def main():
    parser = argparse.ArgumentParser(description="Add arena circle events to TRex CSV output.")
    parser.add_argument("video_name", nargs="?", help="Process only folders matching this name")
    parser.add_argument("--output-dir", type=Path, default=None, help="Override OUTPUT_DIR")
    args = parser.parse_args()
    sys.exit(process_all(args.output_dir, args.video_name))


if __name__ == "__main__":
    main()
