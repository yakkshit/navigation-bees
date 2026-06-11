#!/usr/bin/env python3
# ============================================================
# Tracking quality check
# Scans every video folder in bee_results, reports how many
# frames the bee was actually detected in (missing == 0).
# Output: a summary table printed + saved as a CSV.
# ============================================================

import pandas as pd
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment configuration
env_path = Path(__file__).parent.parent / ".env.local"
if env_path.exists():
    load_dotenv(env_path)
elif (Path(__file__).parent.parent / ".env").exists():
    load_dotenv(Path(__file__).parent.parent / ".env")

# Use OUTPUT_DIR from .env, fall back to hardcoded path
RESULTS_DIR = Path(os.getenv("OUTPUT_DIR", "/Users/fundayildiz/Desktop/bee_results"))
# ---------------------------------------------------

rows = []

for video_dir in sorted(RESULTS_DIR.iterdir()):
    if not video_dir.is_dir():
        continue

    data_dir = video_dir / "data"
    if not data_dir.exists():
        rows.append({"video": video_dir.name, "id_files": 0,
                     "total_frames": 0, "detected": 0, "pct": 0.0,
                     "note": "no data folder"})
        continue

    id_files = sorted(data_dir.glob("*_id*.csv"))
    if not id_files:
        rows.append({"video": video_dir.name, "id_files": 0,
                     "total_frames": 0, "detected": 0, "pct": 0.0,
                     "note": "no id csv"})
        continue

    # A frame counts as "detected" if ANY id file saw the bee there
    detected_frames = set()
    total_frames = 0
    for f in id_files:
        try:
            d = pd.read_csv(f, usecols=["frame", "missing"])
            total_frames = max(total_frames, len(d))
            seen = d.loc[d["missing"] == 0, "frame"].astype(int)
            detected_frames.update(seen.tolist())
        except Exception as e:
            print(f"  ! could not read {f.name}: {e}")

    n_det = len(detected_frames)
    pct = round(100 * n_det / total_frames, 1) if total_frames else 0.0
    rows.append({"video": video_dir.name, "id_files": len(id_files),
                 "total_frames": total_frames, "detected": n_det,
                 "pct": pct, "note": ""})

summary = pd.DataFrame(rows).sort_values("pct").reset_index(drop=True)

# Save
out = RESULTS_DIR / "tracking_quality_summary.csv"
summary.to_csv(out, index=False)

# Print
pd.set_option("display.max_rows", None)
print(summary.to_string(index=False))
print()
print(f"Saved summary to: {out}")
print()
print("=== Overview ===")
print(f"Videos checked:        {len(summary)}")
print(f"Mean detection %:      {summary['pct'].mean():.1f}%")
print(f"Videos below 10%:      {(summary['pct'] < 10).sum()}")
print(f"Videos with >1 id file:{(summary['id_files'] > 1).sum()}  (= ID fragmentation)")
