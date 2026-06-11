# Quick Start Guide — Bumblebee Tracking

**Setup Time:** 5 minutes | **Tracking Time:** ~1 min/video

---

## 🚀 Getting Started in 3 Steps

### Step 1: Place Your Videos
```bash
# Copy your bee videos here:
cp your_videos/*.mp4 bumblebee_task/../../Videos/
```

Supported formats: `.mp4`, `.mov`

### Step 2: Run TREX Tracking
```bash
cd bumblebee_task/
bash Scripts/new_batch.sh
```

**What happens:**
- ✓ TREX processes all videos in `Videos/`
- ✓ Generates tracking data (CSV)
- ✓ Creates tracked MP4 videos
- ✓ Saves results to `V_OUTPUTS/`

### Step 3: View Results
```bash
# Watch tracked video with bee position & angle
open V_OUTPUTS/2025-06-03\ 14-57-02/2025-06-03\ 14-57-02_tracked.mp4

# Check tracking quality
cat V_OUTPUTS/tracking_quality_summary.csv
```

---

## 🎯 Option 1: Basic Tracking (No ROI)
**Use when:** You want to track the entire video frame.

```bash
bash Scripts/new_batch.sh
```

**Output:**
- `*_tracked.mp4` — Video with bee position (green circle), angle (arrow), and speed label
- `*_id0.csv` — Frame-by-frame data (X, Y, angle, speed, etc.)

---

## 🎯 Option 2: ROI-Based Tracking (NEW!)
**Use when:** You want tracking to activate only when bee enters a specific circle/region.

### Step 1: Draw the Region
```bash
python Scripts/roi_tracker_gui.py
```

**What to do:**
1. Window opens showing first video frame
2. **CLICK** on the frame to set circle center (green dot appears)
3. **DRAG** to set radius (green circle grows)
4. **RELEASE** to confirm
5. Press **SPACE** to save, **ESC** to cancel

**Output:** `roi_config.json` saved in output folder

### Step 2: Run TREX with ROI
```bash
bash Scripts/new_batch.sh
```

**What happens automatically:**
- TREX tracks the entire video
- ROI filter removes frames outside your circle
- MP4 shows only bee activity inside ROI (outside = red X)

---

## 📊 Understanding the Tracked Video

### Visual Elements
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TREX Tracked Video                   Frame: 1260
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                   
    🟢 Green Circle                  Position: (36.4, 40.3) cm
    └─ Bee detected here             
                                     Speed: 5.2 cm/s
    → Green Arrow                    Angle: 22°
    └─ Heading direction             Detection: ✓ FOUND
                                   
    🔴 Red X                         Missing: FALSE
    └─ Bee NOT detected here         
    
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Color Legend
| Symbol | Meaning | Action |
|--------|---------|--------|
| 🟢 Circle | Bee detected | Good tracking |
| → Arrow | Body heading | Shows direction bee is facing |
| 🔴 X mark | Bee missing | Lost tracking or outside ROI |
| Text | Speed, angle | Real-time values |

---

## 📈 Analyzing the Results

### Quick Quality Check
```bash
cat V_OUTPUTS/tracking_quality_summary.csv
```

**Look for:**
- `pct` (detection %): should be >70%
- If <30%: TREX settings need tuning (see Troubleshooting below)

### Detailed Analysis in Jupyter
```bash
jupyter notebook Scripts/bee_analysis.ipynb
```

**Plots include:**
- Bee trajectory over time
- Detection rate (frames found vs. lost)
- Speed curve
- Acceleration profile

---

## ⚙️ Tuning for Better Detection

### Problem: Low Detection Rate (<30%)

**Solution 1: Lower detection threshold**
```bash
# Edit: bumblebee_task/working.settings
# Change:
detect_threshold = 7
# To:
detect_threshold = 5
# Then rerun:
bash Scripts/new_batch.sh
```

**Solution 2: Check video quality**
```bash
# View background reference (should be clear)
open V_OUTPUTS/2025-06-03\ 14-57-02/average_*.png
```

If the background is blurry or noisy, the video may need better lighting.

---

## 📁 Project Structure

```
bumblebee_task/
├── Scripts/
│   ├── new_batch.sh                 ← Main entry point
│   ├── roi_tracker_gui.py           ← Draw ROI circle
│   ├── roi_filter.py                ← Apply ROI filtering
│   ├── generate_tracked_video.py    ← MP4 visualization
│   ├── check_tracking_quality.py    ← Quality stats
│   └── bee_analysis.ipynb           ← Analysis notebook
├── nots/
│   ├── docs.md                      ← Full documentation
│   ├── ARCHITECTURE.md              ← System design
│   └── QUICKSTART.md                ← This file
├── working.settings                 ← TREX parameters
└── .env.local                       ← Paths & config
```

---

## 🆘 Troubleshooting

### Q: "TREX executable not found"
**Answer:**
```bash
# Check if TREX is installed
ls /opt/miniconda3/envs/track/bin/TRex.app/Contents/MacOS/TRex

# If missing, TREX needs to be installed in the conda environment
```

### Q: Low detection rate (36%)
**Answer:**
1. Lower `detect_threshold` in `working.settings` (try 3-5)
2. Check video brightness (view `average_*.png`)
3. Ensure bee is visible in the video

### Q: MP4 generation failed
**Answer:**
```bash
# Check the error log
cat V_OUTPUTS/2025-06-03\ 14-57-02/generate_tracked.log

# Common cause: missing OpenCV library
pip install opencv-python
```

### Q: ROI filter not working
**Answer:**
Make sure you ran `roi_tracker_gui.py` first and saved the ROI circle.

---

## 💾 Data Storage

### Outputs saved to: `V_OUTPUTS/`

```
V_OUTPUTS/
├── batch_log.txt                    ← Summary of all runs
├── tracking_quality_summary.csv     ← Stats per video
└── 2025-06-03\ 14-57-02/           ← One folder per video
    ├── 2025-06-03\ 14-57-02_tracked.mp4    ← ⭐ Watch this
    ├── data/2025-06-03\ 14-57-02_id0.csv  ← Raw tracking
    ├── roi_config.json              ← If ROI was used
    └── (various logs and temp files)
```

---

## 🔗 Next Steps

1. **Run basic tracking:** `bash Scripts/new_batch.sh`
2. **Review results:** Watch `*_tracked.mp4`
3. **Analyze data:** Open `bee_analysis.ipynb` in Jupyter
4. **Improve detection:** Adjust `working.settings` if needed
5. **Add ROI:** Use `roi_tracker_gui.py` for conditional tracking

---

## 📞 Help & References

- **TREX Docs:** https://trex.run/docs/
- **Project Overview:** See `docs.md`
- **System Architecture:** See `ARCHITECTURE.md`
- **Python env:** `/opt/miniconda3/envs/track`

---

**Ready to track some bees? 🐝** Run `bash Scripts/new_batch.sh`
