# Quick Start Guide — Bumblebee Tracking

**Setup Time:** 5 minutes | **Tracking Time:** ~1 min/video

---

## 🚀 Getting Started in 3 Steps

### Step 1: Place Your Videos
```bash
cp your_videos/*.mp4 Videos/
```

Supported formats: `.mp4`, `.mov`

### Step 2: Run the Full Pipeline
```bash
cd bumblebee_task/
bash Scripts/new_batch.sh
```

**What happens automatically:**
1. **TRex** — background subtraction tracking → `data/*_id0.csv`
2. **post_process_tracking.py** — arena circle events → `data/*_id0_new.csv` + `*_events.csv`
3. **generate_tracked_video.py** — tracked MP4 with gray (84 cm) and yellow (42 cm) circles

### Step 3: View Results
```bash
# Tracked video with circles + events
open "V_OUTPUTS/2025-06-05 15-16-32/2025-06-05 15-16-32_tracked.mp4"

# Enriched frame-by-frame data (use this for analysis)
open "V_OUTPUTS/2025-06-05 15-16-32/data/2025-06-05 15-16-32_id0_new.csv"

# Entry/exit events only
open "V_OUTPUTS/2025-06-05 15-16-32/data/2025-06-05 15-16-32_events.csv"

# Quality summary
python Scripts/check_tracking_quality.py
```

---

## 📊 Output Files

| File | Description |
|------|-------------|
| `data/*_id0.csv` | Raw TRex export (never modified) |
| `data/*_id0_new.csv` | All TRex columns **plus** arena/event columns |
| `data/*_events.csv` | Summary: video entry, inner/outer entry & exit |
| `*_tracked.mp4` | Visualization — gray outer (84 cm), yellow inner (42 cm) |
| `tracking_quality_summary.csv` | Detection % per video |

---

## 🎯 Arena Circles

Configured in `circle_config.json`:

| Circle | Diameter | Used for |
|--------|----------|----------|
| Outer (gray in MP4) | **84 cm** | Tracking boundary — `arena_tracked=1` only inside |
| Inner (yellow in MP4) | **42 cm** | Feeder zone — inner entry/exit events |

Distance uses TRex `BORDER_DISTANCE#pcentroid` ([TRex format docs](https://trex.run/docs/formats.html)).

---

## 🔧 Post-Process Without Re-Running TRex

If you already have `*_id0.csv` files:

```bash
cd bumblebee_task/Scripts
python3 post_process_tracking.py          # all videos
python3 post_process_tracking.py "2025" # filter by name
```

---

## ⚙️ Improve Detection Accuracy

Edit `working.settings`:

```ini
detect_threshold = 7        # lower = more sensitive (try 5–7)
track_max_speed = 24.73688
cm_per_pixel = 0.0773       # must match camera calibration
```

Then re-run `bash Scripts/new_batch.sh`.

---

## 🆘 Troubleshooting

**Low detection rate?**
- Lower `detect_threshold` in `working.settings`
- Check `*_tracked.mp4` — green dot should follow the bee
- Run `python Scripts/check_tracking_quality.py`

**Circles misaligned in MP4?**
- Adjust `center_offset_x_px` / `center_offset_y_px` in `circle_config.json`

**Too many/few outer exit events?**
- Adjust `visit_gap_frames` in `circle_config.json` (default 20 frames)

---

## 📁 Key Scripts

```
bumblebee_task/Scripts/
├── new_batch.sh                 ← Main entry point
├── post_process_tracking.py     ← Arena events → id0_new.csv
├── generate_tracked_video.py    ← Tracked MP4
├── check_tracking_quality.py    ← Quality summary
└── arena_config.py              ← Shared circle geometry

bumblebee_task/
├── circle_config.json           ← Inner/outer diameters + centre offset
└── working.settings             ← TRex parameters
```
