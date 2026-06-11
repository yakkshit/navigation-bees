# Bumblebee Tracking Architecture Guide

## System Components & Data Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        INPUT LAYER                                         │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  Videos/                                 Data/                           │
│  ├─ 2025-06-03 14-57-02.mp4  ←────────┐ ├─ working.settings            │
│  ├─ 2025-06-04 16-22-15.mp4           │ └─ first.settings             │
│  └─ (more .mp4 files...)              │                               │
│                                       │  .env.local                   │
│                                       │  ├─ INPUT_DIR                │
│                                       │  ├─ OUTPUT_DIR               │
│                                       │  ├─ SETTINGS_FILE            │
│                                       │  └─ TREX_CMD                 │
│                                       │                               │
└───────────────────────────┬───────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    TREX TRACKING LAYER                                    │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  new_batch.sh (Main Orchestrator)                                       │
│  ├─ For each video:                                                     │
│  │  ├─ Step 1: Run TREX binary                                         │
│  │  │   └─ Inputs: video + settings                                   │
│  │  │   └─ Detects bee using background subtraction                  │
│  │  │   └─ Outputs: CSV, .results, .settings                         │
│  │  │                                                                 │
│  │  ├─ Step 2: [OPTIONAL] Apply ROI filter (roi_filter.py)          │
│  │  │   └─ If roi_config.json exists → filter frames by circle      │
│  │  │   └─ Marks frames outside ROI as "missing=1"                  │
│  │  │                                                                 │
│  │  └─ Step 3: Generate tracked MP4 (generate_tracked_video.py)     │
│  │      └─ Reads filtered CSV                                        │
│  │      └─ Draws circles & angles on video                          │
│  │      └─ Outputs *_tracked.mp4                                    │
│  │                                                                 │
│  └─ Log results to batch_log.txt                                     │
│                                                                        │
│  TREX Binary (/opt/miniconda3/envs/track/bin/TRex.app/...)          │
│  ├─ Background Subtraction Detector                                 │
│  ├─ Individual Tracker (Kalman filter-based)                        │
│  └─ Feature Extractor (angle, speed, acceleration)                  │
│                                                                        │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                      OUTPUT LAYER                                         │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  V_OUTPUTS/                                                             │
│  │                                                                       │
│  ├─ batch_log.txt                (summary of runs)                     │
│  ├─ tracking_quality_summary.csv  (per-video stats)                   │
│  │                                                                       │
│  └─ 2025-06-03\ 14-57-02/                                             │
│     ├─ 2025-06-03 14-57-02.results       (TREX binary results)        │
│     ├─ 2025-06-03 14-57-02.settings      (settings used)             │
│     ├─ 2025-06-03 14-57-02_roi.json      (if ROI defined)            │
│     ├─ 2025-06-03 14-57-02_tracked.mp4   (⭐ visualization video)    │
│     │                                                                   │
│     ├─ data/                                                           │
│     │  ├─ 2025-06-03 14-57-02_id0.csv        (tracking data)         │
│     │  └─ 2025-06-03 14-57-02_id0_backup.csv (backup if ROI used)   │
│     │                                                                   │
│     ├─ trex.log                           (TREX debug output)         │
│     ├─ generate_tracked.log               (MP4 generation log)        │
│     └─ average_2025-06-03 14-57-02.png    (background reference)     │
│                                                                        │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    ANALYSIS LAYER                                         │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  check_tracking_quality.py                                             │
│  ├─ Reads: CSV files from data/                                        │
│  ├─ Computes:                                                          │
│  │  ├─ Detection rate (% of frames with bee found)                   │
│  │  ├─ Bee body size statistics                                      │
│  │  └─ Total duration & frame counts                                 │
│  └─ Outputs: tracking_quality_summary.csv                            │
│                                                                        │
│  bee_analysis.ipynb (Jupyter Notebook)                                │
│  ├─ Plots 1: Bee trajectory (X vs Y over time)                        │
│  ├─ Plots 2: Detection over time (missing vs detected)               │
│  ├─ Plots 3: Speed over time (walking speed curve)                    │
│  ├─ Plots 4: Acceleration over time                                   │
│  └─ Summary stats: mean speed, max speed, gaps in tracking            │
│                                                                        │
│  Custom Analysis Scripts (user-created)                              │
│  └─ Read CSV → compute custom metrics (turning angle, etc.)          │
│                                                                        │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Step-by-Step

### 🎬 Phase 1: Input Preparation
```
User places video file(s)
    ↓
Videos/2025-06-03\ 14-57-02.mp4
    ↓
Set paths in .env.local
    ↓
Ready for tracking
```

### 🔄 Phase 2: TREX Tracking
```
new_batch.sh loads configuration
    ↓
For each video:
    ├─ Activate conda env (track)
    ├─ Call TREX binary
    │   ├─ Input: video file + working.settings
    │   ├─ Process: background subtraction
    │   └─ Output: frame-by-frame tracking data
    │
    ├─ TREX generates:
    │   ├─ .results (binary format)
    │   ├─ .settings (actual settings used)
    │   ├─ data/*_id0.csv (frame-by-frame CSV)
    │   └─ trex.log (debug output)
    │
    └─ Done with TREX
```

### 🔍 Phase 3 (OPTIONAL): ROI Filtering
```
Check if roi_config.json exists
    ↓
If YES:
    ├─ Read ROI circle (center, radius)
    ├─ For each frame in CSV:
    │   ├─ If (x,y) inside circle: keep detection
    │   └─ If (x,y) outside circle: mark as missing=1
    ├─ Backup original CSV
    └─ Save filtered CSV
│
If NO:
    └─ Skip ROI filtering (use full frame)
```

### 🎬 Phase 4: MP4 Visualization
```
generate_tracked_video.py reads CSV
    ↓
Open source video (Videos/...)
    ↓
For each frame:
    ├─ Read CSV row for this frame
    ├─ Get bee position (x, y)
    ├─ Get bee angle (orientation)
    ├─ Draw on frame:
    │   ├─ Green circle (detected) OR red X (missing)
    │   ├─ Green arrow (angle line)
    │   ├─ Speed label
    │   └─ Frame counter
    ├─ Write to output video
    └─ Next frame
    ↓
Output: *_tracked.mp4 (177 MB)
```

### 📊 Phase 5: Quality Analysis
```
check_tracking_quality.py reads all CSVs
    ├─ For each video:
    │   ├─ Count frames: total
    │   ├─ Count frames: detected (missing==0)
    │   ├─ Calculate: detection % = detected/total
    │   └─ Get: bee size statistics
    │
    └─ Output: tracking_quality_summary.csv
        ├─ video name
        ├─ id_files count
        ├─ total_frames
        ├─ detected
        └─ pct (detection %)
```

---

## CSV Data Format

### Frame-by-Frame Columns
```
frame              → Frame number (0-indexed)
X (cm)            → X position (centimeters)
Y (cm)            → Y position (centimeters)
ANGLE             → Body orientation (radians: -π to +π)
SPEED (cm/s)      → Walking speed
ACCELERATION#pcentroid (cm/s²)  → Acceleration
ANGULAR_VELOCITY#centroid       → Body rotation speed
missing           → Detection flag (0=detected, 1=not detected/lost)
num_pixels        → Bee body size (pixels)
time              → Time in seconds from start
```

### Example Row (Detected)
```
frame=1260, X=36.40, Y=40.30, ANGLE=0.39, 
SPEED=0.00, missing=0, num_pixels=26
```
→ Bee at (36.40, 40.30) cm, heading ~22° (0.39 rad), stationary

### Example Row (Missing/Lost)
```
frame=1288, X=inf, Y=inf, ANGLE=inf, 
SPEED=inf, missing=1, num_pixels=inf
```
→ Bee not detected in this frame

---

## Configuration: working.settings

```ini
# DETECTION (how to find the bee)
detect_threshold = 7                # Lower = more sensitive (3-5 for struggling)
detect_type = background_subtraction
detect_size_filter = []             # No min/max size filtering

# TRACKING (how to follow the bee)
track_background_subtraction = true
track_max_individuals = 1           # Track exactly 1 bee
track_max_speed = 30                # Max bee speed (cm/s)
track_max_reassign_time = 120       # Reconnect broken tracks within 120ms
track_size_filter = [[0.08963, 0.89635]]  # Min/max bee size ratio

# PHYSICS & OUTPUT
cm_per_pixel = 0.0612               # Calibration (adjust per camera)
calculate_posture = true            # Compute angle
output_format = csv                 # Export as CSV
```

**Tuning Guide:**
- ↓ Detection too low? Try `detect_threshold = 5` (lower = more sensitive)
- ↓ Too much noise? Try `detect_size_filter = [[0.05, 0.95]]` (size bounds)
- ↓ Tracking breaks? Try `track_max_reassign_time = 300` (higher = more lenient)

---

## ROI-Based Tracking Workflow

### New Feature: Conditional Tracking by Circle

```
Step 1: User draws ROI
    └─ python roi_tracker_gui.py
       ├─ Load first video frame
       ├─ User clicks center point
       ├─ User drags to set radius
       └─ Save roi_config.json

Step 2: TREX runs normally
    └─ Full video tracked (all frames)

Step 3: ROI filter applied
    └─ python roi_filter.py
       ├─ Read roi_config.json (center, radius)
       ├─ For each frame:
       │  ├─ Check if (x,y) in circle
       │  ├─ If YES: keep detection
       │  └─ If NO: mark missing=1
       └─ Save filtered CSV

Step 4: MP4 shows only ROI activity
    └─ Tracked video only displays bee inside circle
       (Outside = red X / marked as missing)
```

**Advantage:** Non-invasive — doesn't modify TREX, post-processes results

---

## Performance Metrics

### Current System (as of 2026-06-03)

| Metric | Value | Status |
|--------|-------|--------|
| Videos processed | 1 | ✓ |
| TREX success rate | 100% (1/1) | ✓ |
| MP4 generation | ✓ 177.5 MB | ✓ |
| Detection rate | 36.0% | ⚠️ LOW |
| Avg processing time | ~1 min/video | ✓ |
| Output video size | ~2 MB/min | ✓ |

### Bottlenecks
- **Detection:** Low detection rate (36%) requires parameter tuning
- **MP4 encoding:** ~2-3 min for 394 sec video (real-time playback)
- **Memory:** Full frame storage + CSV in RAM (manageable)

### Scalability
- **Multiple videos:** Batch process with `new_batch.sh` (serial)
- **Parallelization:** Could process videos in parallel (future)
- **Storage:** ~2 GB per hour of 1080p video tracked

---

## Troubleshooting Reference

| Problem | Cause | Solution |
|---------|-------|----------|
| Low detection (<30%) | High threshold or poor lighting | Lower `detect_threshold`, check video contrast |
| TREX crashes | Python env not set up | Verify `TREX_CMD`, activate conda |
| MP4 has no annotations | CSV reading failed | Check CSV format, ensure `X (cm)` column exists |
| ROI filter not working | roi_config.json missing | Run `roi_tracker_gui.py` first |
| Very slow MP4 generation | Video codec bottleneck | Use faster codec (MJPG instead of mp4v) |

---

## Future Enhancements

1. **Real-time tracking display** — OpenCV window during TREX run
2. **Automatic parameter tuning** — Grid search for best `detect_threshold`
3. **Multi-bee tracking** — Change `track_max_individuals > 1`
4. **Behavior classification** — ML model to classify bee actions (walking, stopped, turning)
5. **Web dashboard** — Flask app to view results, manage videos
6. **GPU acceleration** — CUDA support for faster processing

---

## Quick Reference: Common Commands

```bash
# Run full pipeline
cd bumblebee_task/
bash Scripts/new_batch.sh

# View tracked video
open V_OUTPUTS/2025-06-03\ 14-57-02/2025-06-03\ 14-57-02_tracked.mp4

# Draw ROI circle
python Scripts/roi_tracker_gui.py

# Check quality summary
cat V_OUTPUTS/tracking_quality_summary.csv

# Analyze in Jupyter
jupyter notebook Scripts/bee_analysis.ipynb

# Debug: view TREX log
tail -50 V_OUTPUTS/2025-06-03\ 14-57-02/trex.log
```

---
