# Project Workflow & Architecture — Complete Integration Guide

**Status:** ✅ **Production Ready**  
**Last Updated:** June 17, 2026  
**Version:** 3.0 (arena circle events + id0_new.csv)

---

## 📋 Project Scope

**Objective:** Track individual bumblebees in video recordings, capturing position, orientation (angle), speed, and movement patterns using automated TREX tracking + angle analysis.

**Current Capabilities:**
- ✅ Batch video processing (multiple videos)
- ✅ Frame-by-frame bee detection & tracking (TRex background subtraction)
- ✅ Body angle/orientation extraction (in radians)
- ✅ Speed, acceleration, BORDER_DISTANCE, posture fields from TRex
- ✅ **Arena event post-processing** — inner/outer circle entry & exit
- ✅ Enriched CSV output (`*_id0_new.csv`) — original `*_id0.csv` preserved
- ✅ Per-video event summary (`*_events.csv`)
- ✅ Visualization with tracked MP4 videos (84 cm outer / 42 cm inner overlay)
- ✅ Quality metrics (TRex detection % + arena tracked %)

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
  │  TREX Tracking Engine   │ ← Background subtraction → *_id0.csv
  └──────────┬──────────────┘
             ↓
  ┌─────────────────────────┐
  │  post_process_tracking  │ ← 84 cm / 42 cm arena events → *_id0_new.csv
  └──────────┬──────────────┘
             ↓
  ┌─────────────────────────┐
  │  MP4 Visualization      │ ← Reads id0_new.csv, draws circles + events
  └──────────┬──────────────┘
             ↓
  OUTPUT: Tracked video + raw CSV + enriched CSV + events CSV
```

### Component Responsibilities

| Component | Role | Input | Output |
|-----------|------|-------|--------|
| `new_batch.sh` | Orchestrator | Video files | Runs TRex → post-process → MP4 |
| `TREX binary` | Tracker | Video + settings | `data/*_id0.csv` + logs |
| `post_process_tracking.py` | Event analyzer | `*_id0.csv` + `circle_config.json` | `*_id0_new.csv`, `*_events.csv` |
| `arena_config.py` | Shared geometry | `circle_config.json` | Inner Ø42 cm, outer Ø84 cm |
| `generate_tracked_video.py` | Renderer | `*_id0_new.csv` + video | `*_tracked.mp4` |
| `check_tracking_quality.py` | QA summary | All output folders | `tracking_quality_summary.csv` |
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
         │   ├─→ Run post_process_tracking.py
         │   │   └─ Output: data/*_id0_new.csv + *_events.csv
         │   │
         │   └─→ Run generate_tracked_video.py
         │       ├─ Input: id0_new.csv + video
         │       ├─ Draw: 84 cm / 42 cm circles + arrows
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
- `V_OUTPUTS/{video_name}/data/{video_name}_id0.csv` — Raw TRex export (unchanged)
- `V_OUTPUTS/{video_name}/data/{video_name}_id0_new.csv` — **Enriched** frame data with arena columns
- `V_OUTPUTS/{video_name}/data/{video_name}_events.csv` — One row per entry/exit event
- `V_OUTPUTS/{video_name}/{video_name}_tracked.mp4` — Visualization with gray/yellow circles
- `V_OUTPUTS/batch_log.txt` — Run summary

---

## 💾 Data Format & Interpretation

### Arena Geometry (`circle_config.json`)

| Circle | Diameter | Radius | Role |
|--------|----------|--------|------|
| **Outer (gray in MP4)** | 84 cm | 42 cm | Active tracking boundary — bee must be inside to count as `arena_tracked=1` |
| **Inner (yellow in MP4)** | 42 cm | 21 cm | Feeder zone — inner entry/exit events |

Distance from centre uses TRex `BORDER_DISTANCE#pcentroid (cm)` when available:
`dist_to_center_cm = 42 − BORDER_DISTANCE` ([TRex docs](https://trex.run/docs/formats.html)).

### Raw CSV (`*_id0.csv`) — TRex export

All standard TRex kinematic fields are preserved, including:
`frame`, `X (cm)`, `Y (cm)`, `ANGLE`, `SPEED (cm/s)`, `VX/VY`, `AX/AY`,
`BORDER_DISTANCE#pcentroid (cm)`, `MIDLINE_OFFSET`, `num_pixels`, `time`, `missing`, etc.

### Enriched CSV (`*_id0_new.csv`) — added columns

| Column | Meaning |
|--------|---------|
| `dist_to_center_cm` | Radial distance from arena centre (cm) |
| `in_inner_circle` | 1 if detected inside 42 cm feeder zone |
| `in_outer_circle` | 1 if detected inside 84 cm arena |
| `arena_tracked` | 1 if actively tracked inside outer arena |
| `outside_arena` | 1 if TRex detected bee but outside 84 cm circle |
| `is_video_entry` | 1 on first bee appearance in video |
| `is_outer_entry` / `is_outer_exit` | 1 on outer circle crossing |
| `is_inner_entry` / `is_inner_exit` | 1 on inner circle crossing |
| `circle_event` | Event label(s) on that frame |

### Events CSV (`*_events.csv`)

| Column | Meaning |
|--------|---------|
| `event` | `video_entry`, `outer_entry`, `inner_entry`, `inner_exit`, `outer_exit` |
| `frame`, `time_s` | When the event occurred |
| `X_cm`, `Y_cm`, `dist_to_center_cm` | Bee position at event |
| `ANGLE_rad`, `SPEED_cm_s` | TRex posture/kinematics at event |

### Post-process existing outputs (without re-running TRex)

```bash
cd bumblebee_task/Scripts
python3 post_process_tracking.py              # all videos in V_OUTPUTS
python3 post_process_tracking.py "2025-06-05" # one video
python3 check_tracking_quality.py           # summary with arena_tracked %
```

### Interpreting Results

**Good detection (inside arena):**
```
✓ arena_tracked=1, missing=0, X & Y are numbers
→ Bee detected inside the 84 cm outer circle
```

**Lost tracking:**
```
✗ missing=1 or arena_tracked=0
→ Bee not detected, or outside the outer arena boundary
```

**Detection rate:**
```
TRex detection %  = (missing=0) / total frames
Arena tracked %   = (arena_tracked=1) / total frames   ← use this for behaviour analysis
```

---

## 🎯 Arena Circle Tracking

Tracking is active only when the bee is inside the **84 cm outer circle** (gray overlay in `*_tracked.mp4`).

| Event | Trigger |
|-------|---------|
| `video_entry` | First confirmed detection inside outer arena |
| `outer_entry` | Bee re-enters outer arena after leaving (≥20 frame gap) |
| `outer_exit` | Bee leaves outer arena or track lost for ≥20 frames |
| `inner_entry` | `dist_to_center` crosses from >21 cm to ≤21 cm |
| `inner_exit` | `dist_to_center` crosses from ≤21 cm to >21 cm |

Tune sensitivity in `circle_config.json`: `event_debounce_frames`, `visit_gap_frames`, `center_offset_*`.

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
