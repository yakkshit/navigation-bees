#!/usr/bin/env python3
"""
Tracking quality check — scans TRex output folders and reports detection rates.

Prefers post-processed *_id0_new.csv (arena_tracked inside 84 cm outer circle).
Falls back to raw *_id0.csv (missing == 0).
"""

import pandas as pd
from pathlib import Path
import os
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env.local"
if env_path.exists():
    load_dotenv(env_path)
elif (Path(__file__).parent.parent / ".env").exists():
    load_dotenv(Path(__file__).parent.parent / ".env")

RESULTS_DIR = Path(os.getenv("OUTPUT_DIR", "/Users/yakkshit/Downloads/project/hiwi2/p1/V_OUTPUTS"))
OUTPUT_SUMMARY = Path(__file__).parent.parent / "Output" / "Results" / "tracking_quality_summary.csv"

rows = []

for video_dir in sorted(RESULTS_DIR.iterdir()):
    if not video_dir.is_dir():
        continue

    data_dir = video_dir / "data"
    if not data_dir.exists():
        rows.append({
            "video": video_dir.name, "source_csv": "", "total_frames": 0,
            "trex_detected": 0, "trex_pct": 0.0, "arena_tracked": 0,
            "arena_pct": 0.0, "inner_frames": 0, "events": 0, "note": "no data folder",
        })
        continue

    new_csvs = sorted(data_dir.glob("*_id0_new.csv"))
    raw_csvs = [p for p in sorted(data_dir.glob("*_id0.csv")) if not p.name.endswith("_id0_new.csv")]
    csv_path = new_csvs[0] if new_csvs else (raw_csvs[0] if raw_csvs else None)

    if csv_path is None:
        rows.append({
            "video": video_dir.name, "source_csv": "", "total_frames": 0,
            "trex_detected": 0, "trex_pct": 0.0, "arena_tracked": 0,
            "arena_pct": 0.0, "inner_frames": 0, "events": 0, "note": "no id csv",
        })
        continue

    try:
        d = pd.read_csv(csv_path)
    except Exception as e:
        rows.append({
            "video": video_dir.name, "source_csv": csv_path.name, "total_frames": 0,
            "trex_detected": 0, "trex_pct": 0.0, "arena_tracked": 0,
            "arena_pct": 0.0, "inner_frames": 0, "events": 0, "note": str(e),
        })
        continue

    total = len(d)
    trex_det = int((d["missing"] == 0).sum()) if "missing" in d.columns else 0
    trex_pct = round(100 * trex_det / total, 1) if total else 0.0

    if "arena_tracked" in d.columns:
        arena_det = int((d["arena_tracked"] == 1).sum())
    else:
        arena_det = trex_det
    arena_pct = round(100 * arena_det / total, 1) if total else 0.0

    inner_frames = int((d["in_inner_circle"] == 1).sum()) if "in_inner_circle" in d.columns else 0

    events_path = data_dir / f"{csv_path.stem.rsplit('_id0', 1)[0]}_events.csv"
    if not events_path.exists():
        base = csv_path.stem.replace("_id0_new", "").replace("_id0", "")
        events_path = data_dir / f"{base}_events.csv"
    n_events = 0
    if events_path.exists():
        try:
            n_events = len(pd.read_csv(events_path))
        except Exception:
            pass

    rows.append({
        "video": video_dir.name,
        "source_csv": csv_path.name,
        "total_frames": total,
        "trex_detected": trex_det,
        "trex_pct": trex_pct,
        "arena_tracked": arena_det,
        "arena_pct": arena_pct,
        "inner_frames": inner_frames,
        "events": n_events,
        "note": "",
    })

summary = pd.DataFrame(rows).sort_values("arena_pct").reset_index(drop=True)

OUTPUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
summary.to_csv(OUTPUT_SUMMARY, index=False)
summary.to_csv(RESULTS_DIR / "tracking_quality_summary.csv", index=False)

pd.set_option("display.max_rows", None)
print(summary.to_string(index=False))
print()
print(f"Saved summary to: {OUTPUT_SUMMARY}")
print(f"Also saved to:    {RESULTS_DIR / 'tracking_quality_summary.csv'}")
print()
print("=== Overview ===")
print(f"Videos checked:           {len(summary)}")
print(f"Mean TRex detection %:    {summary['trex_pct'].mean():.1f}%")
print(f"Mean arena tracked %:     {summary['arena_pct'].mean():.1f}%  (inside 84 cm outer circle)")
print(f"Videos below 10% arena:   {(summary['arena_pct'] < 10).sum()}")
