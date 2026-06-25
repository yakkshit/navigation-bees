# Documentation Index — Bumblebee Tracking Project

**Complete Documentation Suite — Updated June 3, 2026**

Welcome! This folder contains comprehensive documentation for the bumblebee tracking project. Start here to understand what's available and find what you need.

---

## 📖 Documentation Files (In This Folder)

### 🚀 Getting Started
- **[QUICKSTART.md](QUICKSTART.md)** — **START HERE** if you just want to run the pipeline
  - 3-step basic workflow
  - ROI selection tutorial
  - Output explanation
  - Troubleshooting FAQ
  - ⏱️ Read time: 5 minutes

### 📚 Comprehensive Guides
- **[docs.md](docs.md)** — Complete project documentation
  - Project overview & current status
  - Full architecture diagram
  - Project structure explanation
  - Workflow step-by-step
  - Data format reference
  - TREX settings explanation
  - Tracking quality analysis
  - ⏱️ Read time: 20 minutes

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Detailed system design
  - Component breakdown & responsibilities
  - Data flow diagrams
  - CSV format specification
  - Configuration tuning guide
  - Performance metrics
  - Future improvements
  - ⏱️ Read time: 25 minutes

- **[INTEGRATION.md](INTEGRATION.md)** — Workflow & architecture integration
  - Project scope & capabilities
  - System architecture overview
  - Detailed workflow scenarios (basic + ROI)
  - Technical implementation details
  - Data interpretation guide
  - Quality metrics & validation
  - ⏱️ Read time: 30 minutes

### 🆘 Help & Reference
- **[README.md](README.md)** — This file
  - Quick reference guide
  - File organization
  - Where to find information

---

## 🎯 Quick Navigation by Use Case

### "I just want to track videos"
1. Read: **QUICKSTART.md** (5 min)
2. Run: `bash Scripts/new_batch.sh`
3. Watch: `V_OUTPUTS/*_tracked.mp4`

### "I want to understand the system"
1. Read: **docs.md** (20 min) — Project overview
2. Read: **ARCHITECTURE.md** (25 min) — System details
3. Explore: Source code in `Scripts/`

### "I need to define a tracking region (ROI)"
1. Read: **QUICKSTART.md** → "Option 2: ROI-Based Tracking" (10 min)
2. Run: `python Scripts/roi_tracker_gui.py`
3. Run: `bash Scripts/new_batch.sh` (auto-applies ROI)

### "Detection rate is low, how do I fix it?"
1. Read: **QUICKSTART.md** → "Tuning for Better Detection" (5 min)
2. Check: `cat V_OUTPUTS/tracking_quality_summary.csv`
3. Adjust: `working.settings` → lower `detect_threshold`
4. Rerun: `bash Scripts/new_batch.sh`

### "I want to analyze the tracking data"
1. Read: **docs.md** → "Key Data Points per Frame" section
2. Open: `Scripts/bee_analysis.ipynb` in Jupyter
3. Or: Create custom Python scripts reading CSV files

### "I'm implementing a new feature"
1. Read: **INTEGRATION.md** (30 min) — Full workflow
2. Read: **ARCHITECTURE.md** (25 min) — Component design
3. Study: Source code in `Scripts/`
4. Check: Existing issue documentation in this folder

---

## 🗂️ Project File Structure

```
bumblebee_task/
│
├── nots/                          ← YOU ARE HERE
│   ├── README.md                  (this file)
│   ├── QUICKSTART.md              (5-min getting started)
│   ├── docs.md                    (20-min full guide)
│   ├── ARCHITECTURE.md            (25-min system design)
│   ├── INTEGRATION.md             (30-min workflow)
│   └── TRex_Handover.pdf          (original TREX docs)
│
├── Scripts/                        ← Main code
│   ├── new_batch.sh               (main orchestrator)
│   ├── roi_tracker_gui.py         (draw ROI circle)
│   ├── roi_filter.py              (apply ROI filtering)
│   ├── generate_tracked_video.py  (MP4 visualization)
│   ├── check_tracking_quality.py  (quality stats)
│   └── bee_analysis.ipynb         (analysis notebook)
│
├── Data/                          ← Configuration
│   └── first.settings
│
├── working.settings               ← TREX parameters (MAIN)
├── .env.local                     ← Paths & TREX_CMD
└── README.txt                     ← Original project info
```

---

## 📊 What Each Script Does

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `new_batch.sh` | **Main entry point** — TRex → post-process → MP4 | `Videos/` | `V_OUTPUTS/` |
| `post_process_tracking.py` | Arena circle events → `*_id0_new.csv` | `*_id0.csv` | `*_id0_new.csv`, `*_events.csv` |
| `generate_tracked_video.py` | Tracked MP4 with circles | `*_id0_new.csv` + video | `*_tracked.mp4` |
| `check_tracking_quality.py` | Quality summary | `V_OUTPUTS/` | `tracking_quality_summary.csv` |
| `generate_tracked_video.py` | Create MP4 with bee position/angle visualized | CSV + video | `*_tracked.mp4` |
| `check_tracking_quality.py` | Generate summary statistics | All CSVs | `tracking_quality_summary.csv` |
| `bee_analysis.ipynb` | Interactive analysis & plotting | CSV files | Plots & stats |

---

## 💡 Key Concepts

### Detection Rate
**What:** Percentage of frames where bee was successfully detected  
**Formula:** (frames with missing=0) / (total frames) × 100  
**Target:** >70%  
**Current:** 36% (needs tuning)

### ROI (Region of Interest)
**What:** Circular region where tracking should be active  
**Why:** Reduce noise, focus on specific area, conditional tracking  
**How:** User draws circle → saved as JSON → applied as filter

### ANGLE (Body Orientation)
**What:** Direction bee's body is pointing (radians)  
**Range:** -π to +π (or 0 to 2π)  
**Visualization:** Green arrow on tracked video

### CSV Data
**Format:** Frame-by-frame tracking results  
**Columns:** X, Y, ANGLE, SPEED, ACCELERATION, missing flag, etc.  
**Location:** `V_OUTPUTS/{video_name}/data/*_id0_new.csv` (enriched) or `*_id0.csv` (raw TRex)

---

## 🔍 Finding Information

### By Topic

**Project Setup & Installation**
→ See original handover docs or `docs.md` → Installation section

**Running the Tracker**
→ **QUICKSTART.md** (easiest) or `docs.md` → Workflow Steps

**Understanding Output Data**
→ `docs.md` → Key Data Points per Frame section
→ `ARCHITECTURE.md` → CSV Data Format section

**Tuning Parameters**
→ `docs.md` → TREX Settings section
→ `ARCHITECTURE.md` → Configuration & Tuning section

**ROI-Based Tracking**
→ **QUICKSTART.md** → Option 2 section (simplest)
→ `INTEGRATION.md` → Scenario 2: ROI-Based Tracking (detailed)

**Troubleshooting**
→ **QUICKSTART.md** → Troubleshooting section (quick fixes)
→ `docs.md` → Troubleshooting section (comprehensive)

**System Architecture**
→ `ARCHITECTURE.md` (complete design breakdown)
→ `INTEGRATION.md` (workflow & integration details)

**Analysis & Visualization**
→ `docs.md` → Current Tracking Quality section
→ `bee_analysis.ipynb` (Jupyter notebook with plots)

---

## 🚀 Common Workflows

### Workflow 1: Basic Tracking (No ROI)
```
1. Place videos in Videos/
2. Run: bash Scripts/new_batch.sh
3. View: open V_OUTPUTS/*_tracked.mp4
```
→ **Documentation:** QUICKSTART.md (Option 1)

### Workflow 2: ROI-Based Tracking
```
1. Place videos in Videos/
2. Run: python Scripts/roi_tracker_gui.py (draw circle)
3. Run: bash Scripts/new_batch.sh (auto-applies ROI)
4. View: open V_OUTPUTS/*_tracked.mp4
```
→ **Documentation:** QUICKSTART.md (Option 2)

### Workflow 3: Analysis & Improvement
```
1. Run tracking (see Workflow 1 or 2)
2. Check: cat V_OUTPUTS/tracking_quality_summary.csv
3. Adjust: Edit working.settings (detect_threshold, etc.)
4. Rerun: bash Scripts/new_batch.sh
5. Analyze: jupyter notebook Scripts/bee_analysis.ipynb
```
→ **Documentation:** docs.md + QUICKSTART.md Tuning section

### Workflow 4: Custom Analysis
```
1. Run tracking
2. Read CSV: V_OUTPUTS/{video_name}/data/*_id0.csv
3. Process: Write custom Python script using pandas
4. Result: Custom metrics/plots
```
→ **Documentation:** ARCHITECTURE.md (CSV Format section)

---

## 📞 Getting Help

### Issue: Script Error
**First Step:** Check the error message  
**Second:** Look in relevant `.log` file (e.g., `V_OUTPUTS/.../trex.log`)  
**Third:** Consult **QUICKSTART.md** → Troubleshooting section  

### Issue: Low Detection Rate
**Read:** QUICKSTART.md → "Tuning for Better Detection"  
**Or:** ARCHITECTURE.md → "Configuration & Tuning" section  

### Issue: Understanding Data Format
**Read:** ARCHITECTURE.md → "CSV Data Format & Interpretation"  
**Or:** docs.md → "Key Data Points per Frame"  

### Issue: How to use ROI
**Read:** QUICKSTART.md → "Option 2: ROI-Based Tracking"  
**Or:** INTEGRATION.md → "Scenario 2: ROI-Based Tracking"  

### Issue: Understanding Architecture
**Read:** INTEGRATION.md (30 min read for complete picture)  
**Or:** ARCHITECTURE.md (focus on system components)  

---

## 📋 Documentation Checklist

- ✅ **QUICKSTART.md** — Quick start guide (created)
- ✅ **docs.md** — Complete documentation (created)
- ✅ **ARCHITECTURE.md** — System design (created)
- ✅ **INTEGRATION.md** — Workflow integration (created)
- ✅ **README.md** — This file (index)
- ✅ **roi_tracker_gui.py** — ROI selector script (created)
- ✅ **roi_filter.py** — ROI post-processor script (created)
- ✅ **new_batch.sh** — Updated with ROI integration (updated)

---

## 🎓 Learning Path

**If you have 5 minutes:**
→ Read QUICKSTART.md

**If you have 20 minutes:**
→ Read QUICKSTART.md + docs.md

**If you have 1 hour:**
→ Read all documentation + explore Scripts/ folder

**If you want to modify the system:**
→ Read INTEGRATION.md + ARCHITECTURE.md + study Scripts/

---

## 📅 Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2026-06-03 | Added ROI-based tracking, GUI, comprehensive docs |
| 1.5 | 2026-06-02 | Auto MP4 generation in batch pipeline |
| 1.0 | 2026-06-01 | Initial TREX batch processing |

---

## ✅ Project Status

**Current Capabilities (v2.0):**
- ✅ Batch video processing
- ✅ TREX background subtraction tracking
- ✅ Frame-by-frame CSV output
- ✅ MP4 visualization with angle/position
- ✅ Quality metrics computation
- ✅ **NEW:** ROI-based conditional tracking
- ✅ **NEW:** Interactive ROI selection GUI
- ✅ **NEW:** Comprehensive documentation

**Known Issues:**
- ⚠️ Low detection rate (36% — needs parameter tuning)

**Planned Improvements:**
- 🔄 Optimize detection parameters
- 🔄 Behavior classification (walking/stopped/turning)
- 🔄 Real-time progress visualization
- 🔄 Multi-bee tracking support

---

## 🎯 Next Steps

1. **Get Started:** Read QUICKSTART.md
2. **Run Tracking:** `bash Scripts/new_batch.sh`
3. **Understand Results:** Check `V_OUTPUTS/tracking_quality_summary.csv`
4. **Improve:** Adjust `working.settings` if detection is low
5. **Analyze:** Open `Scripts/bee_analysis.ipynb` in Jupyter

---

**Last Updated:** June 3, 2026  
**Status:** ✅ Production Ready (v2.0)  
**Questions?** Check the relevant documentation file above or review source code in `Scripts/`
