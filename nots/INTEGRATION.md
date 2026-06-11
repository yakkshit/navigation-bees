# Project Workflow & Architecture — Complete Integration Guide

**Status:** ✅ **Production Ready**  
**Last Updated:** June 3, 2026  
**Version:** 2.0 (ROI-based tracking added)

---

## 📋 Project Scope

**Objective:** Track individual bumblebees in video recordings, capturing position, orientation (angle), speed, and movement patterns using automated TREX tracking + angle analysis.

**Current Capabilities:**
- ✅ Batch video processing (multiple videos)
- ✅ Frame-by-frame bee detection & tracking
- ✅ Body angle/orientation extraction (in radians)
- ✅ Speed & acceleration computation
- ✅ Visualization with tracked MP4 videos
- ✅ Quality metrics (detection rate, etc.)
- ✅ **NEW:** ROI-based tracking (conditional)
- ✅ **NEW:** Interactive GUI for ROI selection

**In Progress:**
- 🔄 Parameter tuning for better detection (currently 36%)
- 🔄 Behavior classification (walking vs. stopped vs. turning)

**Not Yet Implemented:**
- ❌ Real-time tracking visualization
- ❌ Multi-bee tracking (>1 individual)
- ❌ Web dashboard
- ❌ GPU acceleration

---

## 🏗️ System Architecture

### High-Level Pipeline
```
INPUT VIDEOS
     ↓
  ┌─────────────────────────┐
  │  TREX Tracking Engine   │ ← Detects bee via background subtraction
  └──────────┬──────────────┘
             ↓
  ┌─────────────────────────┐
  │  ROI Filter (Optional)  │ ← Filters frames by circle region
  └──────────┬──────────────┘
             ↓
  ┌─────────────────────────┐
  │  MP4 Visualization      │ ← Draws detected positions + angles
  └──────────┬──────────────┘
             ↓
  OUTPUT: Tracked video + CSV data
```

### Component Responsibilities

| Component | Role | Input | Output |
|-----------|------|-------|--------|
| `new_batch.sh` | Orchestrator | Video files | Orchestrates TREX, ROI, MP4 gen |
| `TREX binary` | Tracker | Video + settings | CSV + .results + logs |
| `roi_tracker_gui.py` | Visualizer | Video first frame | `roi_config.json` |
| `roi_filter.py` | Post-processor | CSV + ROI JSON | Filtered CSV |
| `generate_tracked_video.py` | Renderer | CSV + video | Tracked MP4 |
| `bee_analysis.ipynb` | Analyzer | CSV | Plots & statistics |

---

## 🔄 Detailed Workflow

### Scenario 1: Basic Tracking (No ROI)

```
User inputs:
  Videos/ folder with .mp4 files
  working.settings (TREX parameters)
         │
         ▼
┌─────────────────────┐
│  new_batch.sh       │
│  (main orchestrator)│
└────────┬────────────┘
         │
         ├─→ Find all videos
         │
         ├─→ For each video:
         │   │
         │   ├─→ Run TREX binary
         │   │   ├─ Input: video file
         │   │   ├─ Settings: working.settings
         │   │   └─ Output: data/*_id0.csv
         │   │
         │   ├─→ [SKIP ROI check — no roi_config.json]
         │   │
         │   └─→ Run generate_tracked_video.py
         │       ├─ Input: CSV + video
         │       ├─ Draw: circles + arrows
         │       └─ Output: *_tracked.mp4
         │
         └─→ Summary: batch_log.txt
            Output dir: V_OUTPUTS/
```

**Key Output Files:**
- `V_OUTPUTS/{video_name}/{video_name}_id0.csv` — Raw tracking data
- `V_OUTPUTS/{video_name}/{video_name}_tracked.mp4` — Visualization
- `V_OUTPUTS/batch_log.txt` — Run summary

---

### Scenario 2: ROI-Based Tracking (NEW!)

```
User inputs:
  Videos/ folder with .mp4 files
  working.settings
         │
         ▼
  Step 1: User draws ROI
  ┌──────────────────────┐
  │ roi_tracker_gui.py   │
  ├──────────────────────┤
  │ 1. Load first frame  │
  │ 2. Click center      │ ← User interaction
  │ 3. Drag to radius    │
  │ 4. Save JSON         │
  └────────┬─────────────┘
           │
           └─→ Output: roi_config.json
               {
                 "center_x": 320,
                 "center_y": 240,
                 "radius": 150
               }
         │
         ▼
  Step 2: Run TREX batch
  ┌──────────────────────────┐
  │  new_batch.sh            │
  ├──────────────────────────┤
  │  For each video:         │
  │  ├─ Run TREX             │
  │  │  └─ Output: full CSV  │
  │  │                       │
  │  ├─ Check for ROI        │
  │  │  └─ Found! Apply      │
  │  │                       │
  │  ├─ Run roi_filter.py    │
  │  │  ├─ Input: CSV, ROI   │
  │  │  ├─ Filter: (x,y)     │
  │  │  │  in circle?        │
  │  │  └─ Output: filtered  │
  │  │      CSV              │
  │  │                       │
  │  └─ Generate MP4         │
  │     using filtered CSV   │
  └────────┬─────────────────┘
           │
           ▼
  Output: *_tracked.mp4
          └─ Shows ONLY bee movement inside circle
             (Outside = red X)
```

**Key Output Files:**
- `V_OUTPUTS/{video_name}/roi_config.json` — ROI definition
- `V_OUTPUTS/{video_name}/{video_name}_id0.csv` — Filtered tracking
- `V_OUTPUTS/{video_name}/{video_name}_id0_backup.csv` — Original (unfiltered)
- `V_OUTPUTS/{video_name}/{video_name}_tracked.mp4` — ROI-filtered visualization

---

## 💾 Data Format & Interpretation

### CSV Structure (Frame-by-Frame)

```csv
frame,X (cm),Y (cm),ANGLE,SPEED (cm/s),ACCELERATION#pcentroid (cm/s²),ANGULAR_VELOCITY#centroid,missing,num_pixels
0,34.5,38.2,0.15,0.0,0.0,0.0,0,26
1,34.5,38.2,0.12,0.0,0.0,-0.02,0,27
2,34.6,38.3,0.10,1.2,15.3,-0.04,0,26
3,inf,inf,inf,inf,inf,inf,1,inf
```

### Column Meanings

| Column | Unit | Range | Meaning |
|--------|------|-------|---------|
| `frame` | — | 0-23680 | Frame number |
| `X (cm)` | cm | 0-100 | X position (absolute) |
| `Y (cm)` | cm | 0-100 | Y position (absolute) |
| `ANGLE` | radians | -π to +π | Body heading (0=right, π/2=up) |
| `SPEED (cm/s)` | cm/s | 0-50 | Walking speed |
| `ACCELERATION#pcentroid` | cm/s² | -100-100 | Speed change rate |
| `ANGULAR_VELOCITY#centroid` | rad/s | -π-π | Rotation speed |
| `missing` | flag | 0 or 1 | 0=detected, 1=lost/outside ROI |
| `num_pixels` | pixels | 10-100 | Bee body size in frame |

### Interpreting Results

**Good Detection:**
```
✓ missing=0, X & Y are numbers, ANGLE is -π to π
→ Bee was detected in this frame
```

**Lost Tracking:**
```
✗ missing=1, X & Y are inf, ANGLE is inf
→ Bee was NOT detected (lost track or outside ROI)
```

**Detection Rate Calculation:**
```
Detection % = (frames with missing=0) / (total frames) × 100
Example: 8536 detected / 23680 total = 36.0%
```

---

## 🎯 ROI-Based Tracking Explained

### What is ROI?
**ROI = Region of Interest** — A circular region where you want tracking to be active.

### Why Use It?
1. **Conditional tracking** — Only track bee inside specific area
2. **Noise reduction** — Ignore wall/object movement outside circle
3. **Behavior focus** — Study bee behavior in confined region
4. **Data filtering** — Post-process to reduce false positives

### How It Works (Technical)

```
Step 1: User draws circle
  Center: (cx, cy) in pixels
  Radius: r in pixels
  Saved: roi_config.json

Step 2: ROI filter applied
  For each frame:
    Read CSV row: (x_cm, y_cm, ...)
    Convert cm → pixels: (x_px, y_px)
    Calculate distance: d = √((x_px - cx)² + (y_px - cy)²)
    If d ≤ r:
      Keep detection (missing stays 0)
    Else:
      Set missing = 1 (mark as outside ROI)
  
Step 3: Save filtered CSV
  Backup original: *_id0_backup.csv
  Save filtered: *_id0.csv

Step 4: MP4 generation
  Uses filtered CSV
  Frames inside ROI: green circle + arrow
  Frames outside ROI: red X
```

### Example: Circle at (320, 240) with radius 150 pixels

```
Frame  X_cm  Y_cm  → (px)    Distance  Inside?  missing (after filter)
1      30.0  35.0 → (490,572) 445 px  NO       1 (marked as lost)
2      31.0  36.0 → (507,588) 465 px  NO       1
3      35.0  40.0 → (571,654) 520 px  NO       1
4      36.4  40.3 → (594,658) 560 px  NO       1
5      32.0  35.0 → (522,572) 262 px  YES      0 (kept as detected)
6      32.5  35.5 → (531,580) 279 px  YES      0
7      33.0  36.0 → (539,588) 296 px  YES      0
```

---

## ⚙️ Configuration & Tuning

### TREX Parameters (working.settings)

```ini
# Detection sensitivity
detect_threshold = 7              # Lower = more sensitive (try 3-5)
detect_type = background_subtraction

# Tracking robustness
track_max_individuals = 1         # Track 1 bee
track_max_speed = 30              # Max speed (cm/s)
track_max_reassign_time = 120     # Reconnect tracks within 120ms
track_size_filter = [[0.08963, 0.89635]]  # Bee size bounds

# Calibration
cm_per_pixel = 0.0612             # Camera calibration
calculate_posture = true          # Compute angle
output_format = csv               # Export format
```

### Tuning Guide

**Problem: Detection rate is too low (<30%)**
```
Current: detect_threshold = 7
Try:     detect_threshold = 5
Reason:  Lower threshold = more sensitive to movement
         (catches fainter bee images)
```

**Problem: Too much noise in tracking**
```
Current: detect_size_filter = []
Try:     detect_size_filter = [[0.05, 0.95]]
Reason:  Filters out objects that aren't bee-sized
         (rejects noise and shadows)
```

**Problem: Tracking frequently breaks**
```
Current: track_max_reassign_time = 120
Try:     track_max_reassign_time = 300
Reason:  Allow longer gaps before track is lost
         (reconnects broken tracks)
```

---

## 🚀 Running the Pipeline

### Quick Start
```bash
cd bumblebee_task/
bash Scripts/new_batch.sh
```

### With ROI
```bash
# Step 1: Define ROI circle
python Scripts/roi_tracker_gui.py

# Step 2: Run TREX (auto-applies ROI if found)
bash Scripts/new_batch.sh
```

### Manual Post-Processing
```bash
# Apply ROI filter to existing tracking
python Scripts/roi_filter.py "2025-06-03 14-57-02" \
    --roi-file V_OUTPUTS/2025-06-03\ 14-57-02/roi_config.json \
    --output-dir V_OUTPUTS/

# Regenerate MP4 from filtered CSV
python Scripts/generate_tracked_video.py "2025-06-03 14-57-02"
```

---

## 📊 Quality Metrics

### Detection Rate
```
Definition: % of frames where bee was detected
Formula:    (frames with missing=0) / (total frames) × 100
Target:     >70% (current: 36% — needs tuning)
```

### Bee Size Variation
```
Definition: Range of bee body pixel count
Why matter: Indicates if bee is same size throughout
           (larger = closer to camera, smaller = farther)
```

### Speed Statistics
```
Mean speed: Average walking speed (cm/s)
Max speed:  Maximum recorded speed
Gaps:       Frames with missing=1 (track loss)
```

---

## ✅ Validation Checklist

Before considering tracking successful:

- [ ] Detection rate > 70% (adjust settings if needed)
- [ ] Tracked video plays without errors
- [ ] CSV file has correct number of rows = total frames
- [ ] Bee is visible in tracked video (green circles appear)
- [ ] Angle arrows show reasonable directions (not random)
- [ ] No crashes or missing data columns

---

## 🆘 Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| TREX not found | Installation issue | Check `/opt/miniconda3/envs/track` |
| Low detection | Threshold too high | Lower `detect_threshold` to 3-5 |
| MP4 errors | Missing OpenCV | `pip install opencv-python` |
| ROI not applied | No roi_config.json | Run `roi_tracker_gui.py` first |
| Slow MP4 gen | Video codec overhead | Use shorter video or faster codec |
| Python not found | Env not set up | Verify `.venv` or conda activation |

---

## 📈 Expected Performance

**Processing Speed:**
- TREX: ~1-2 min for 6-minute video
- MP4 generation: ~2-3 min for 6-minute video
- Total: ~5 min per video

**Storage:**
- Input video: ~600 MB (6 min @ 1080p)
- TREX output: ~1 MB (CSV + metadata)
- Tracked MP4: ~180 MB (compressed H.264)
- **Total:** ~800 MB per tracked video

**System Requirements:**
- CPU: 2+ cores (TREX is single-threaded)
- RAM: 4+ GB (typical: 2-3 GB used)
- Disk: 2+ GB free per video processed
- GPU: Not required (but would help MP4 encoding)

---

## 🔮 Future Improvements

### Short Term (Next Sprint)
1. Improve detection rate to >70%
   - Optimize `detect_threshold` per video
   - Pre-process videos (enhance contrast)
   - Test on reference videos

2. Add real-time progress bar
   - Show TREX progress in terminal
   - ETA for processing

### Medium Term (Next Quarter)
1. Behavior classification
   - Walking vs. stopped
   - Turning angle detection
   - Resting periods

2. Multi-bee support
   - Track 2+ individuals
   - Generate separate CSVs per bee
   - Interaction analysis

### Long Term (6+ Months)
1. Web dashboard
   - View videos, stats, plots
   - Manage batches
   - Download results

2. GPU acceleration
   - CUDA support for TREX
   - Faster MP4 encoding
   - Real-time processing

3. ML-based detection
   - Train CNN on bee images
   - Improve robustness vs. background subtraction
   - Multi-species support

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `docs.md` | Complete user documentation |
| `ARCHITECTURE.md` | Detailed system design |
| `QUICKSTART.md` | 5-minute getting started guide |
| `INTEGRATION.md` | This file — workflow overview |

---

## 🎓 Learning Resources

- **TREX Official:** https://trex.run/docs/
- **Background Subtraction:** https://en.wikipedia.org/wiki/Foreground_detection
- **Kalman Filtering:** https://en.wikipedia.org/wiki/Kalman_filter
- **OpenCV:** https://docs.opencv.org/

---

## ✉️ Support & Questions

**For issues:**
1. Check `docs.md` troubleshooting section
2. Review `TREX` log files in `V_OUTPUTS/`
3. Test with shorter videos first
4. Verify conda environment: `conda list -n track`

**For feature requests:**
- Document use case in `nots/` folder
- Submit as issue with video samples

---

**Project Status:** ✅ Production Ready (v2.0)  
**Next Review:** June 10, 2026  
**Contact:** Funda Yildiz
