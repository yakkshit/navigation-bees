"""
MasterScript.py
---------------
Runs the full bumblebee tracking and analysis pipeline in order.
Author: Funda Yildiz
Date: 2026

Usage:
  Step 1 (TRex batch tracking) must be run separately:
    bash run_trex_batch.sh

  Step 2 onwards:
    python MasterScript.py
"""

import subprocess
import sys
import os

scripts_dir = os.path.dirname(os.path.abspath(__file__))

scripts = [
    ("check_tracking_quality.py", "Checking tracking quality across all videos"),
]

print("=" * 55)
print("  BUMBLEBEE PROJECT — Analysis Pipeline")
print("=" * 55)

for filename, description in scripts:
    path = os.path.join(scripts_dir, filename)
    print(f"\n>>> {description} ({filename})")
    result = subprocess.run([sys.executable, path])
    if result.returncode != 0:
        print(f"\n✗ Failed: {filename} (exit code {result.returncode})")
        print("  Pipeline stopped. Fix the error above and re-run.")
        sys.exit(1)
    print(f"✓ Done: {filename}")

print("\n" + "=" * 55)
print("  Pipeline complete.")
print("  Results → Output/Results/tracking_quality_summary.csv")
print("  Next    → open Scripts/bee_analysis.ipynb")
print("=" * 55)
