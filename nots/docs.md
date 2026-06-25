# Bumblebee Tracking Project Documentation

**Last Updated:** June 3, 2026  
**Project Goal:** Track individual bumblebees in video using TREX background subtraction + angle/posture analysis

---

## 🎯 Project Overview

This project tracks bumblebee movement and behavior in controlled video recordings. The pipeline:
1. **Records** video of a bee in an arena
2. **Detects** the bee using background subtraction (TREX)
3. **Tracks** position, angle (heading), speed, acceleration
4. **Analyzes** bee behavior (walking, stops, turns, etc.)
5. **Visualizes** results with tracked video + angle arrows

**Current Status:** 
- TREX tracking works ✅
- Generates tracked MP4 videos ✅
- Detection rate: ~36% (LOW — needs tuning)
- **NEW:** ROI-based tracking mode (in development)

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT VIDEOS                             │
│              (Videos/ folder, .mp4 files)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              TREX BATCH PROCESSOR                           │
│         (new_batch.sh + TREX binary)                       │
├─────────────────────────────────────────────────────────────┤
│ • Runs TREX tracking on each video                         │
│ • Background subtraction detection (detect_threshold=7)    │
│ • Outputs: .results, .csv, .settings files                 │
│ • Generates per-frame data (x, y, angle, speed, etc.)      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           TRACKED VIDEO GENERATOR                           │
│       (generate_tracked_video.py)                          │
├─────────────────────────────────────────────────────────────┤
│ • Reads enriched CSV (data/*_id0_new.csv)                  │
│ • Draws 84 cm outer (gray) and 42 cm inner (yellow) circles│
│ • Draws bee position (green circle = detected)             │
│ • Draws angle line (heading direction)                     │
│ • Displays speed & detection status                        │
│ • Outputs: *_tracked.mp4 (177 MB)                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│          ANALYSIS & QUALITY CHECK                          │
│    (check_tracking_quality.py, bee_analysis.ipynb)        │
├─────────────────────────────────────────────────────────────┤
│ • Detection rate (%): 8536/23680 frames = 36.0%           │
│ • Trajectory plots (where bee walked)                      │
│ • Speed/acceleration analysis                              │
│ • Frame-by-frame detection visualization                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              OUTPUT ARTIFACTS                               │
│              (V_OUTPUTS/ folder)                           │
├─────────────────────────────────────────────────────────────┤
│ • tracking_quality_summary.csv (per-video metrics)        │
│ • *_tracked.mp4 (visualization)                            │
│ • data/*_id0.csv (raw TRex)                                │
│ • data/*_id0_new.csv (arena events + zones)                │
│ • data/*_events.csv (entry/exit summary)                   │
│ • trex.log (debug info)                                    │
│ • average_*.png (background reference)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
bumblebee_task/
├── README.txt                          # Project overview
├── working.settings                    # TREX parameters (tuning file)
├── .env.local                          # Paths & TREX_CMD
│
├── Scripts/
│   ├── new_batch.sh                    # ⭐ Main entry point
│   │                                      (TREX + auto MP4 generation)
│   ├── run_trex_batch.sh               # Legacy TREX runner
│   ├── check_tracking_quality.py       # Summary statistics
│   ├── generate_tracked_video.py       # MP4 visualization
│   ├── bee_analysis.ipynb              # Jupyter analysis notebook
│   └── roi_tracker_gui.py              # NEW: ROI selection GUI
│
├── nots/
│   ├── docs.md                         # ⭐ THIS FILE
│   ├── TRex_Handover.pages
│   └── TRex_Handover.pdf
│
├── Data/                               # Input data
│   ├── first.settings
│   ├── InputData/
│   │   ├── Metadata/
│   │   └── Videos/
│
├── Output/                             # Legacy outputs
│   ├── Figures/
│   ├── Results/
│   └── trex_outputs/
```

---

## 🔄 Workflow Steps

### Step 1: Prepare Videos
```bash
# Place .mp4 video files in:
Videos/
  └─ 2025-06-03 14-57-02.mp4
  └─ (more videos...)
```

### Step 2: Run TREX Tracking
```bash
cd bumblebee_task/
bash Scripts/new_batch.sh
```

**What happens:**
- Loads `.env.local` (paths, TREX_CMD)
- Finds all `.mp4` files in `Videos/`
- For each video:
  1. Runs TREX with `working.settings` parameters
  2. Generates TREX output in `V_OUTPUTS/<video_name>/`
  3. **Auto-generates** tracked MP4 visualization
  4. Logs results to `V_OUTPUTS/batch_log.txt`

**Output folder structure:**
```
V_OUTPUTS/
└─ 2025-06-03 14-57-02/
   ├── 2025-06-03 14-57-02.results    (TREX binary results)
   ├── 2025-06-03 14-57-02.settings   (settings used)
   ├── 2025-06-03 14-57-02_tracked.mp4  ⭐ (visualization)
   ├── data/
   │  └─ 2025-06-03 14-57-02_id0.csv  (frame-by-frame data)
   ├── trex.log                        (TREX debug log)
   └── average_*.png                   (background reference)
```

### Step 3: Review Results
```bash
# View quality summary
cat V_OUTPUTS/tracking_quality_summary.csv

# Watch tracked video
open V_OUTPUTS/2025-06-03\ 14-57-02/2025-06-03\ 14-57-02_tracked.mp4

# Open analysis notebook
jupyter notebook bumblebee_task/Scripts/bee_analysis.ipynb
```

### Step 4 (NEW): ROI-Based Tracking
```bash
# Draw a circle/ROI on the video frame
python bumblebee_task/Scripts/roi_tracker_gui.py

# Then run TREX with ROI constraint
bash bumblebee_task/Scripts/new_batch.sh
```

---

## 🎯 Key Data Points per Frame

Each frame in the CSV contains:

| Column | Description | Example |
|--------|-------------|---------|
| `frame` | Frame number | 1260 |
| `X (cm)` | X position (cm) | 36.40 |
| `Y (cm)` | Y position (cm) | 40.30 |
| `ANGLE` | Heading (radians) | 0.39 |
| `SPEED (cm/s)` | Walking speed | 0.00 |
| `ACCELERATION#pcentroid (cm/s²)` | Acceleration | 0.00 |
| `missing` | Detection flag (0=detected, 1=missing) | 0.00 |
| `num_pixels` | Bee body size (pixels) | 26.00 |

**What is ANGLE?**
- **Definition:** Direction the bee's body is pointing (radians)
- **Range:** -π to +π (or 0 to 2π)
- **In the tracked video:** Green arrow shows this direction
- **Convention:** 0 = right, π/2 = up, π = left, -π/2 = down

---

## ⚙️ TREX Settings (working.settings)

Current settings tuning for bumblebees:

```ini
# Detection
detect_threshold = 7              # Background subtraction threshold (lower = more sensitive)
detect_size_filter = []           # No size filtering (detect all connected components)

# Tracking
track_background_subtraction = true   # Use background subtraction
track_max_individuals = 1         # Track exactly 1 bee
track_max_speed = 30              # Max speed in cm/s (bees move slow)
track_max_reassign_time = 120     # Relink broken tracks within 120ms
track_size_filter = [[0.08963, 0.89635]]  # Size bounds

# Physics
cm_per_pixel = 0.0612             # Calibration factor
calculate_posture = true          # Compute body angle

# Output
output_format = csv               # Export as CSV
```

**Current Issue:** Detection rate = 36% (LOW)
- **Root cause:** Background subtraction threshold too conservative
- **Solution ideas:**
  - Lower `detect_threshold` (try 3-5)
  - Check video lighting/contrast
  - Use `detect_size_filter` to reject noise
  - Increase `track_size_filter` bounds

---

## 🆕 ROI-Based Tracking (Proposed)

### Concept
Instead of tracking the entire video, user defines a circle/region where the bee is expected. Tracking only triggers when the bee **enters the ROI**.

### Workflow
1. **GUI Phase:**
   - Load first frame of video
   - User draws a circle on the arena
   - Marks circle center & radius
   - Saves ROI as JSON file

2. **TREX Phase:**
   - TREX runs normally, generates full tracking
   - Post-processing step filters frames:
     - Only keep frames where bee is **inside the ROI**
     - Discard frames outside (set `missing=1`)
   - Result: "conditional tracking"

3. **Output:**
   - Tracked MP4 shows only movement inside ROI
   - CSV has ROI-filtered `missing` flags

### Implementation Status
- **GUI Script:** `roi_tracker_gui.py` (creates ROI selector)
- **TREX Integration:** TREX runs normally, then post-process CSV
- **Advantage:** Simple, non-invasive (doesn't modify TREX itself)

**To use:**
```bash
python bumblebee_task/Scripts/roi_tracker_gui.py
# → Opens video, draws circle, saves roi_config.json
bash bumblebee_task/Scripts/new_batch.sh
# → TREX runs, then filters by ROI
```

---

## 📊 Current Tracking Quality

**Latest Run:** 2025-06-03 14-57-02

| Metric | Value |
|--------|-------|
| Total Frames | 23,680 |
| Detected Frames | 8,536 |
| Detection Rate | **36.0%** ⚠️ |
| Missing Frames | 15,144 |
| Avg Bee Size | ~30 pixels |
| Video Duration | ~394 seconds @ 60 FPS |
| Tracked MP4 Size | 177.5 MB |

**Assessment:**
- ❌ Detection rate is LOW (should be >70%)
- ❌ Many frames lost mid-track
- ✅ Bee is visible in video
- ✅ TREX runs without crashes
- ✅ Visualization works

**Next Steps:**
1. Tune `detect_threshold` parameter (lower = more sensitive)
2. Check video lighting/contrast against reference (average_*.png)
3. Adjust `track_size_filter` bounds
4. Test with reference video (2024-02-05_19-13-11-Trim_tracked.avi) to compare settings

---

## 🛠️ Troubleshooting

### Problem: "TREX executable not found"
**Solution:**
```bash
# Check if TREX is installed
ls /opt/miniconda3/envs/track/bin/TRex.app/Contents/MacOS/TRex

# Update .env.local with correct path
TREX_CMD=/opt/miniconda3/envs/track/bin/TRex.app/Contents/MacOS/TRex
```

### Problem: Low detection rate (<30%)
**Try:**
1. Reduce `detect_threshold` in `working.settings` (7 → 5 → 3)
2. Relax `track_size_filter` bounds
3. Check video brightness (use `average_*.png` as reference)
4. Compare with historical run that worked

### Problem: "MP4 generation failed"
**Check:**
```bash
cat V_OUTPUTS/2025-06-03\ 14-57-02/generate_tracked.log
```

---

## 📚 References

- **TREX Docs:** https://trex.run/docs/
- **Project Owner:** Funda Yildiz
- **Conda Environment:** `/opt/miniconda3/envs/track`
- **Python Version:** 3.11.5
- **Dependencies:** OpenCV, pandas, numpy, python-dotenv

---

## 📝 Change Log

| Date | Change |
|------|--------|
| 2026-06-03 | Created `new_batch.sh` with auto MP4 generation |
| 2026-06-03 | Added ROI tracker GUI proposal |
| 2026-06-03 | Created this documentation |
| 2026-06-02 | Initial TREX batch runs (36% detection) |

---

## ❓ FAQs

**Q: Why is detection so low?**
A: TREX uses background subtraction, which assumes a static background. If lighting changes or the bee is moving slowly, it can be missed.

**Q: Can I improve detection without TREX?**
A: The tracked MP4 visualization uses TREX data. To improve tracking, adjust TREX settings or pre-process the video (enhance contrast, etc.).

**Q: How do I use the ROI feature?**
A: Run `roi_tracker_gui.py` to draw a circle, then `new_batch.sh` will filter by that ROI.

**Q: What does "missing=1" mean?**
A: The bee was not detected in that frame. It's either lost, occluded, or the detection threshold was too high.

---

**Questions?** Check the TREX documentation or the original handover notes in `nots/TRex_Handover.pdf`.
