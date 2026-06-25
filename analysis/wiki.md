# 🐝 Bumblebee Path Integration — Project Wiki

> **Thesis**: *Path Integration in Bumblebees* (Marie Jansen, 2025)
> **Based on**: Patel et al. (2022), *Current Biology*
> **GitHub**: [yakkshit/navigation-bees](https://github.com/yakkshit/navigation-bees)
> **Total experiments analysed**: **105 videos** across multiple bees and conditions

---

## 📋 Table of Contents

1. [What Is This Project?](#-what-is-this-project)
2. [The Experiment — How It Works](#-the-experiment--how-it-works)
3. [The Arena — Physical Setup](#-the-arena--physical-setup)
4. [Experimental Conditions Explained](#-experimental-conditions-explained)
5. [How Videos Were Processed](#-how-videos-were-processed)
6. [Understanding the Data](#-understanding-the-data)
7. [All Graphs Explained](#-all-graphs-explained)
   - [Trajectory Plots](#trajectory-plots)
   - [Heatmaps (Density Plots)](#heatmaps-density-plots)
   - [Polar / Directional Plots](#polar--directional-plots)
   - [Speed & Path Metrics](#speed--path-metrics)
   - [Zone Occupancy](#zone-occupancy)
   - [Summary Figures](#summary-figures)
8. [Key Findings](#-key-findings)
9. [Statistical Methods](#-statistical-methods)
10. [Repository Structure](#-repository-structure)
11. [How to Reproduce Everything](#-how-to-reproduce-everything)

---

## 🔬 What Is This Project?

This project investigates whether **bumblebees can navigate using an internal mental map** — a process called **path integration**.

### The Big Question

> *"When a bumblebee walks to a food source and then needs to return home, does it retrace its exact path — or does it use a shortcut?"*

If a bee uses path integration, it continuously tracks:
- **Which direction** it has been moving
- **How far** it has walked

…and then computes the **direct home vector** — the straight-line route back to the hive. This is similar to how a person can return to their car after wandering through a forest, even without seeing the car.

### Why It Matters

- Path integration (also called **dead reckoning**) is a fundamental navigation strategy found in desert ants, honeybees, and mammals.
- This experiment is one of the first to show it in **walking bumblebees** in a controlled laboratory setting.
- Understanding how bee brains compute navigation has implications for **neuroscience, robotics, and insect ecology**.

---

## 🏟️ The Experiment — How It Works

### Step-by-Step Trial

```
1. 🐝 Bee leaves hive  →  walks to feeder at arena centre
2. 🍯 Bee feeds on sugar-water + pollen
3. 🪤 Bee is trapped at feeder (door closes)
4. 💡 Light cue is manipulated (or left unchanged)
5. 🔓 Bee is released — where does it go?
6. 📹 Camera records entire path from above
7. 🖥️ TRex software tracks bee position frame-by-frame
```

### What We Measure

After release, a path-integrating bee should walk **directly** toward where the hive **should be**, based on its memory of the outbound trip. We measure:

| Measurement | What it tells us |
|-------------|-----------------|
| **Exit direction** | Which direction does the bee leave the arena? |
| **Path straightness** | Does it walk in a straight line or wander? |
| **Speed** | How fast does it walk? |
| **Time in zones** | Does it search near the feeder or near the walls? |

---

## 🔵 The Arena — Physical Setup

```
        ╭────────────────────────────────────────╮
        │         OUTER CIRCLE (84 cm dia)       │
        │   ╭──────────────────────────────╮     │
        │   │    INNER CIRCLE (42 cm dia)  │     │
        │   │         ╭───╮                │     │
        │   │         │ F │  ← Feeder      │     │
        │   │         ╰───╯                │     │
        │   │          (0,0)               │     │
        │   ╰──────────────────────────────╯     │
        │                                        │
        ╰────────────────────────────────────────╯
```

| Element | Size | Purpose |
|---------|------|---------|
| **Inner circle** | 42 cm diameter (r = 21 cm) | Feeder zone — where food is |
| **Outer circle** | 84 cm diameter (r = 42 cm) | Search boundary |
| **Feeder** | Centre point `(0, 0)` | Where the bee eats |
| **Arena coordinates** | cm from feeder centre | `(0,0)` = feeder; `+x` = East; `+y` = North |

### Overhead Polarized Light

The arena is illuminated from above with **linearly polarized light** — artificial skylight that bees can detect with their compound eyes. By rotating the polarizer, we can trick the bee into thinking North is in a different direction.

---

## 🧪 Experimental Conditions Explained

### Two Light Cue Types

| Code | Full Name | What it means |
|------|-----------|---------------|
| **LR** | Left-Right polarization | Polarized light oriented horizontally |
| **TB** | Top-Bottom polarization | Polarized light oriented vertically |

### Two Pollen Load Levels

Bees collect pollen during foraging. A bee with **lots of pollen** has had a successful trip; a bee with **little pollen** had a poor trip.

| Level | Pollen amount | Meaning |
|-------|--------------|---------|
| **Low-P** | P < 4 mg | Poor foraging — bee is "hungry", strong motivation to return |
| **High-P** | P ≥ 4 mg | Successful foraging — bee is "satisfied", less urgent to return |

### The Four Conditions

| Condition Label | Cue | Pollen | n (bees) |
|----------------|-----|--------|----------|
| **LR Low-P** | Left-Right | < 4 mg | 30 |
| **LR High-P** | Left-Right | ≥ 4 mg | 17 |
| **TB Low-P** | Top-Bottom | < 4 mg | 31 |
| **TB High-P** | Top-Bottom | ≥ 4 mg | 22 |

> **Total: 105 experiments** (47 LR-cue, 53 TB-cue, 5 with unknown cue type)

### Bee Identity Codes

Bees were individually paint-tagged:
- **R** = Red-tagged bee (e.g., R13)
- **W** = White-tagged bee (e.g., W5)
- **G** = Green-tagged bee (e.g., G2)

---

## 🎬 How Videos Were Processed

### Pipeline Overview

```
Raw .mp4 Videos
      │
      ▼  [trim_input_videos.py]
Trim to 10 min max
      │
      ▼  [TRex tracking software]
Frame-by-frame bee position (x, y pixels, speed, heading)
      │
      ▼  [post_process_tracking.py]
Convert to cm, add distance/zone/event columns
      │
      ▼  V_OUTPUTS/ folders
      │     ├── *_id0_new.csv   → frame-by-frame trajectory
      │     └── *_events.csv    → entry/exit events
      │
      ▼  [analyse_bees.py]  +  [plot_heatmaps.py]
16 thesis figures  +  6 heatmap figures  +  2 summary CSVs
```

### Calibration

| Setting | Value |
|---------|-------|
| Camera zoom-out | 0.1546 cm per pixel |
| Camera zoom-in | 0.0773 cm per pixel |
| Arena centre | Detected per video using Hough circle transform |
| Centre cache | Stored in `circle_config_cache.json` |

---

## 📊 Understanding the Data

### What Each CSV Column Means (`*_id0_new.csv`)

| Column | Unit | Description |
|--------|------|-------------|
| `frame` | — | Frame number (25 frames/sec typical) |
| `X (cm)`, `Y (cm)` | cm | Bee's absolute position in arena |
| `SPEED (cm/s)` | cm/s | Walking speed (capped at 50 cm/s to remove errors) |
| `HEADING_ANGLE` | radians | Body orientation |
| `missing` | 0 or 1 | `1` = tracking lost this frame (excluded from analysis) |
| `dist_to_center_cm` | cm | Distance from feeder `(0, 0)` |
| `in_inner_circle` | 0 or 1 | `1` = bee is within 21 cm of feeder |
| `in_outer_circle` | 0 or 1 | `1` = bee is within 42 cm of feeder |
| `circle_event` | text | e.g. `outer_exit` = moment bee crossed outer boundary |

### Folder Name Convention

```
2024-11-17 17-04-16.R13.LR.P0U8
│                   │   │  │ │
│                   │   │  │ └─ Uncertainty = 8
│                   │   │  └─── Pollen = 0 mg
│                   │   └────── Cue type = LR
│                   └────────── Bee ID = R13
└────────────────────────────── Date & time of recording
```

---

## 📈 All Graphs Explained

> All figures are saved in `analysis/results/`

---

### Trajectory Plots

#### `fig1_representative_trajectories.png` — Best Single Trajectories

**What you see:** One example trajectory per condition, displayed inside a circle. The path is coloured from **dark purple (start)** → **bright yellow (end)** using the plasma colourmap.

**How to read it:**
- The inner dashed circle = feeder zone (r = 21 cm)
- The outer dashed circle = arena boundary (r = 42 cm)
- The dot at centre = feeder
- Follow the colour from dark to bright to see where the bee went over time

**What it tells us:** Shows a "typical" example of what bee movement looks like in each condition. Low-P bees often show a short, directed home vector; High-P bees tend to search more before finding direction.

---

#### `fig2_all_trajectories_by_condition.png` — All Paths Overlaid

**What you see:** Every single recorded trajectory overlaid on one arena, grouped by condition (4 panels: LR low-P, LR high-P, TB low-P, TB high-P). Each path is a different colour; alpha transparency lets you see where paths overlap.

**How to read it:**
- Dense crossing at centre = bees spent time near feeder
- Radiating lines outward = home runs / directional exits
- Spaghetti patterns = exploratory or undirected movement

**What it tells us:** At a glance shows whether a condition produces **directed** (parallel lines) or **scattered** (all directions) movement.

---

#### `fig12_per_bee_trajectories.png` — Per-Individual Bee

**What you see:** All sessions from the **same individual bee** shown together — one subplot per unique bee ID.

**How to read it:** Compare rows across the same individual across different sessions to see consistency or learning.

**What it tells us:** Individual variation — some bees are much more consistent navigators than others.

---

#### `heatmap_trajectory_overlays.png` — Time-Coloured Overlays (Paper Style)

**What you see:** All trajectories overlaid on a **dark navy background**, coloured by time — **dark purple = start**, **bright yellow = end** of each trial. 4 panels by condition.

**How to read it:**
- If many trajectories converge on the same direction at the end (bright yellow), the condition produces consistent homing
- A dark blob near the centre = all bees started there (at the feeder)
- Bright streaks in many directions = undirected searching

**Why it looks like the paper:** Reproduces the style of Figure 3C and Figure 6A from Patel et al. (2022).

---

### Heatmaps (Density Plots)

> These show **where bees spent the most time** — like a thermal camera showing heat footprints.

**How to read ALL heatmaps:**
```
Colour scale:    Dark navy   →   Blue   →   Red   →   Orange   →   Yellow   →   White
Meaning:          Never here      Rare        Sometimes    Often       Very often   Almost always here
```

- The two **white dashed circles** are the inner (r=21 cm) and outer (r=42 cm) arena boundaries
- The **white dot** at the centre is the feeder
- **Hot spots** (red/orange/yellow/white) = where bees concentrated their search

---

#### `heatmap_all_bees.png` — All 105 Bees Combined

**What you see:** Two panels:
- **Left** = full trajectories of all 105 experiments
- **Right** = clipped to within the arena boundary

**What it tells us:** The overall "footprint" of all bees — where do bees collectively spend most time regardless of condition? Hot spots reveal preferred search zones.

---

#### `heatmap_per_condition.png` — 2×2 Condition Grid

**What you see:** 4 separate heatmaps — one per condition (LR low-P, LR high-P, TB low-P, TB high-P).

**How to compare:**
- **Low-P conditions** (top-left, bottom-left): Hot spots should be near centre if bees are homing accurately
- **High-P conditions** (top-right, bottom-right): Expect more spread/scatter if bees are less motivated

**What it tells us:** Whether different experimental conditions cause bees to search in different spatial patterns.

---

#### `heatmap_lr_vs_tb.png` — LR vs. TB Direct Comparison

**What you see:** Two heatmaps side by side — Left-Right cue (all pollen levels) vs. Top-Bottom cue (all pollen levels).

**What it tells us:** Whether the **direction of the polarized light** (horizontal vs vertical) changes where bees search.

---

#### `heatmap_paper_fig6_style.png` — Full Fig 6 Reproduction Panel

**What you see:** A 2-row × 3-column panel:
- **Row 1** (top): Time-coloured trajectory overlays for LR low-P / TB low-P / All conditions
- **Row 2** (bottom): Density heatmaps for the same three groups

**Why this figure:** This directly reproduces the layout of **Figure 6** from Patel et al. (2022), which showed search behaviour density maps alongside path tracings. It's the most comprehensive single figure in the dataset.

---

#### `heatmap_radial_density.png` — Distance Profile

**What you see:** A line plot where the x-axis = distance from feeder (cm) and y-axis = fraction of time spent at that distance. Four coloured lines, one per condition.

**How to read it:**
- A peak near `r = 0` means bees stayed close to the feeder (searching near the expected home)
- A peak near `r = 42` means bees were near the outer wall
- Vertical dashed lines mark the inner circle (21 cm) and outer circle (42 cm)

**What it tells us:** A quantitative summary of how far from the feeder each group searched.

---

#### `fig5_density_heatmaps.png` — Earlier Style Heatmaps

**What you see:** Same heatmap data but rendered with a **white background** and `YlOrRd` colormap. Older style, complementary to the dark-background versions above.

---

### Polar / Directional Plots

> These use **circular (polar) coordinates** to show *which direction* bees chose to leave the arena.
> The arena centre is at the middle; the distance from centre = number of bees choosing that direction.

---

#### `fig3_polar_exit_directions.png` — Polar Histograms of Exit Angles

**What you see:** 4 polar rose plots — one per condition. Each "petal" pointing in a direction shows how many bees exited the outer circle heading that way.

**How to read it:**
- A long petal in one direction = many bees chose that direction → **directional homing**
- Petals spread evenly = bees chose random directions → **no path integration**
- The **arrow** = mean vector (average direction), its length = how consistent the group was (short = scattered, long = consistent)

**What it tells us:** The most direct test of path integration — if bees integrate their path, they should all exit in the same direction (toward the hive).

---

#### `fig4_polar_scatter_exit_angles.png` — Individual Exit Angles

**What you see:** Each dot on the polar plot = one bee's exit angle. The arrow = mean vector.

**How to read it:** Same as fig3, but each individual data point is visible rather than binned into a histogram.

**What it tells us:** Shows the distribution of individual choices and identifies outliers.

---

#### `fig11_lr_vs_tb_polar.png` — LR vs TB Overall Comparison

**What you see:** Two polar plots side by side — Left-Right cue vs Top-Bottom cue — combining all pollen levels.

**What it tells us:** Whether the **type of polarization cue** changes the direction bees choose to exit.

---

#### `fig9_exit_angle_vs_pollen.png` — Direction vs Pollen Amount

**What you see:** A scatter plot where x-axis = pollen amount (mg) and y-axis = exit angle (°). Points are coloured by uncertainty level.

**How to read it:**
- If points cluster at a specific angle for low pollen → low-P bees are consistently directed
- If points scatter across all angles for high pollen → high-P bees are undirected

**What it tells us:** Whether pollen load (foraging success) affects the reliability of navigation.

---

### Speed & Path Metrics

#### `fig6_speed_analysis.png` — Walking Speed

**What you see:**
- **Left panel**: Boxplot of mean walking speed (cm/s) for each condition
- **Right panel**: Speed vs. pollen amount scatter plot

**How to read boxplots:**
```
        ┬  ← Maximum (excluding outliers)
        │
    ┌───┤  ← 75th percentile (upper quartile)
    │   │
    │ ─ │  ← Median (50th percentile)
    │   │
    └───┤  ← 25th percentile (lower quartile)
        │
        ┴  ← Minimum (excluding outliers)
        ○  ← Outliers (individual points)
```

**What it tells us:** Whether pollen load or cue type affects how fast bees move. Faster walking may indicate more directed, confident homing.

| Condition | Mean Speed |
|-----------|-----------|
| LR Low-P  | ~12.8 cm/s |
| LR High-P | ~11.4 cm/s |
| TB Low-P  | ~11.9 cm/s |
| TB High-P | ~12.7 cm/s |

---

#### `fig7_path_straightness.png` — How Direct Is the Path?

**What you see:** Straightness index (d/L) per condition, shown as boxplots and scatter vs pollen.

**Formula:**
```
Straightness = displacement / path_length

  displacement = straight-line distance from start to end
  path_length  = total length of all steps walked

  Straightness = 1.0 → perfectly straight (bee walked directly to hive)
  Straightness = 0.0 → random walk (went everywhere, ended up nowhere)
```

**What it tells us:** Bees performing accurate path integration should show **higher straightness** during the home vector phase.

---

#### `fig15_path_lengths.png` — Total Distance Walked

**What you see:** Distribution of total path length (cm) per condition. Longer paths = more exploration; shorter paths = more directed.

**What it tells us:** Whether different conditions cause bees to walk more or less before exiting/finding direction.

---

### Zone Occupancy

#### `fig8_zone_time.png` — Time Spent in Each Zone

**What you see:** Stacked bar chart or grouped bars showing what **percentage of time** each condition group spent in:
- 🟢 **Inner zone** (r < 21 cm): Near the feeder
- 🔵 **Outer zone** (21 cm < r < 42 cm): Mid-arena
- ⚪ **Outside** (r > 42 cm): Beyond arena boundary

**How to read it:** If bees are good path integrators, they should spend most time near the **feeder zone** (inner circle) when starting their home vector.

| Condition | Inner zone | Outer zone | Outside |
|-----------|-----------|-----------|---------|
| LR Low-P  | 37.5% | 14.1% | 48.4% |
| LR High-P | 33.7% | 19.4% | 47.0% |
| TB Low-P  | 42.0% | 13.6% | 44.4% |
| TB High-P | 42.9% | 20.3% | 36.9% |

---

#### `fig10_search_radius.png` — How Far Do Bees Search?

**What you see:** Maximum search radius plotted against pollen amount and uncertainty level.

**How to read it:** A bee that searches further from the feeder is less certain about where the hive is. Expected pattern: **high-P bees search further** (less certain), **low-P bees search closer** (more certain).

---

### Summary Figures

#### `fig13_summary_statistics_table.png` — Statistics Table

**What you see:** A publication-ready table showing:
- n (sample size per condition)
- Mean exit direction (°)
- Mean vector length R (0 = uniform, 1 = all same direction)
- Rayleigh test p-value
- Mean speed, path length, straightness

**The most important numbers to know:**

| Condition | n | Direction | R | p-value | Significant? |
|-----------|---|-----------|---|---------|-------------|
| LR Low-P  | 30 | 12.6° | 0.577 | < 0.001 | ✅ YES |
| TB Low-P  | 31 | 10.8° | 0.536 | < 0.001 | ✅ YES |
| LR High-P | 17 | 319.4° | 0.384 | 0.093 | ❌ NO (trend) |
| TB High-P | 22 | 298.1° | 0.363 | 0.053 | ❌ NO (trend) |

---

#### `fig14_exit_angle_violins.png` — Exit Angle Distributions

**What you see:** Violin plots of exit angle per condition. A violin is like a sideways density curve — wider = more bees chose that angle.

**How to read it:**
- A **narrow, tall violin** = bees chose very similar directions (good path integration)
- A **wide, flat violin** = bees scattered in all directions (no consistent homing)

---

#### `fig16_overview_dashboard.png` — Full 4×3 Summary Dashboard

**What you see:** A single combined figure with 12 panels showing ALL key analyses together: trajectories, polar plots, speed, straightness, zone time, and heatmaps.

**Use this figure** for presentations when you want to show everything at once.

---

## 🎯 Key Findings

### Main Result

> **Bumblebees with low pollen loads navigate home significantly more accurately than bees with high pollen loads.**

This is consistent with path integration theory: a bee that had a poor foraging trip (low pollen) is strongly motivated to return home and uses its path integration system accurately. A well-fed bee is less precise.

### Statistical Summary

| Condition | Mean Direction | R | p-value | Interpretation |
|-----------|---------------|---|---------|---------------|
| **LR Low-P** (n=30) | 12.6° | **0.577** | **p < 0.001** | ✅ Strong directional homing |
| **TB Low-P** (n=31) | 10.8° | **0.536** | **p < 0.001** | ✅ Strong directional homing |
| LR High-P (n=17) | 319.4° | 0.384 | p = 0.093 | ⚠️ Weak trend only |
| TB High-P (n=22) | 298.1° | 0.363 | p = 0.053 | ⚠️ Weak trend only |

### Secondary Findings

- **LR vs TB cue**: No significant difference in homing accuracy between Left-Right and Top-Bottom polarization — bees use **both** types of polarized skylight equally well.
- **Walking speed**: Consistent across conditions (~11–13 cm/s), suggesting motivation doesn't change locomotion rate.
- **Path straightness**: Low-P bees show slightly straighter home vectors (higher d/L ratio).

---

## 📐 Statistical Methods

### Rayleigh Test of Uniformity

Used to test whether exit directions are **concentrated** (not random):

- **H₀** (null hypothesis): Exit angles are uniformly distributed (no preferred direction)
- **H₁** (alternative): Exit angles cluster in one direction
- **p < 0.05** = we reject H₀ = bees have a consistent preferred direction

### Mean Vector R

- **R = 0**: Bees exit in completely random directions
- **R = 1**: All bees exit in exactly the same direction
- **R > 0.5** is generally considered "strong" concentration

### Circular Statistics

Because angles wrap around (359° is next to 0°), we cannot use normal statistics. Instead:
- **Circular mean**: Computed using sine/cosine components
- **Circular standard deviation**: Based on R value
- **All implemented** following Mardia & Jupp (2000) using the `scipy` library

---

## 🗂️ Repository Structure

```
navigation-bees/
│
├── 📁 Scripts/                    ← Video processing pipeline
│   ├── new_batch.sh               ← Main script: runs all videos through TRex
│   ├── post_process_tracking.py   ← Adds distance/zone/events to tracking data
│   ├── arena_config.py            ← Arena geometry & centre detection
│   ├── generate_tracked_video.py  ← Overlays bee path on video
│   └── trim_input_videos.py       ← Pre-trims videos > 10 min to exactly 10 min
│
├── 📁 analysis/
│   ├── 📁 scripts/
│   │   ├── analyse_bees.py        ← ⭐ Main analysis: generates fig1–fig16
│   │   └── plot_heatmaps.py       ← ⭐ Paper-style heatmaps (Fig 6 style)
│   │
│   └── 📁 results/                ← ALL output figures & CSVs
│       ├── fig1_representative_trajectories.png
│       ├── fig2_all_trajectories_by_condition.png
│       ├── fig3_polar_exit_directions.png
│       ├── fig4_polar_scatter_exit_angles.png
│       ├── fig5_density_heatmaps.png
│       ├── fig6_speed_analysis.png
│       ├── fig7_path_straightness.png
│       ├── fig8_zone_time.png
│       ├── fig9_exit_angle_vs_pollen.png
│       ├── fig10_search_radius.png
│       ├── fig11_lr_vs_tb_polar.png
│       ├── fig12_per_bee_trajectories.png
│       ├── fig13_summary_statistics_table.png
│       ├── fig14_exit_angle_violins.png
│       ├── fig15_path_lengths.png
│       ├── fig16_overview_dashboard.png
│       ├── heatmap_all_bees.png           ← NEW: dark-style heatmap all bees
│       ├── heatmap_per_condition.png      ← NEW: per-condition 2×2 heatmap
│       ├── heatmap_trajectory_overlays.png ← NEW: time-coloured overlays
│       ├── heatmap_lr_vs_tb.png           ← NEW: LR vs TB comparison
│       ├── heatmap_paper_fig6_style.png   ← NEW: full Fig 6 reproduction
│       ├── heatmap_radial_density.png     ← NEW: radial profile plot
│       ├── summary_all_experiments.csv    ← Per-experiment metrics (105 rows)
│       └── summary_per_condition.csv      ← Aggregated per-condition stats
│
├── 📁 nots/                       ← Reference papers
│   ├── paper1.pdf                 ← Jansen 2025 thesis
│   └── paper2.pdf                 ← Patel et al. 2022 (Current Biology)
│
├── circle_config_cache.json       ← Per-video arena centre coordinates (pixels)
├── working.settings               ← TRex tracking configuration
├── requirements.txt               ← Python package list
└── pyproject.toml                 ← Project metadata
```

---

## ▶️ How to Reproduce Everything

### 1. Set Up Python Environment

```bash
# The virtual environment is at:
source /Users/yakkshit/Downloads/project/hiwi2/p1/.venv/bin/activate

# Install dependencies (already done)
pip install pandas numpy matplotlib seaborn scipy
```

### 2. Run the Main Analysis (fig1–fig16 + CSVs)

```bash
cd /path/to/bumblebee_task
python analysis/scripts/analyse_bees.py
```

⏱️ Takes ~2–3 minutes. Reads all 105 experiments from `V_OUTPUTS/`.

### 3. Run the Heatmap Figures

```bash
python analysis/scripts/plot_heatmaps.py
```

⏱️ Takes ~1–2 minutes. Generates 6 paper-style heatmap figures.

### 4. Run the Full Video Tracking Batch

```bash
bash Scripts/new_batch.sh
```

⚠️ This processes raw videos through TRex and takes **many hours** for all 357 videos.

---

## 📚 References

1. **Patel, R.N. et al. (2022)**. "Bumblebees use path integration to estimate both the direction and distance of their hive from a food source." *Current Biology*, 32(13), 2871–2883.e4. https://doi.org/10.1016/j.cub.2022.05.026

2. **Jansen, M. (2025)**. *Path Integration in Bumblebees* (Bachelor's Thesis). University of Würzburg.

3. **TRex** — Tracking software: Walter, T., & Couzin, I.D. (2021). TRex, a fast multi-animal tracking system with markerless identification, 2D body posture estimation, and visual field reconstruction. *eLife*, 10, e64000.

4. **Mardia, K.V. & Jupp, P.E. (2000)**. *Directional Statistics*. Wiley. — Used for all circular statistics formulas.

---

## 🙋 Glossary

| Term | Meaning |
|------|---------|
| **Path integration** | Navigation by tracking direction + distance traveled from a known point |
| **Home vector** | The computed straight-line route back to the nest |
| **Mean vector R** | How consistent a group of angles is (0 = random, 1 = all same) |
| **Rayleigh test** | Statistical test: "Are these angles non-random?" |
| **p-value** | Probability the result is due to chance; p < 0.05 = significant |
| **Polarized light** | Light waves oscillating in one plane — bees can see this, humans mostly can't |
| **LR / TB** | Left-Right / Top-Bottom orientation of polarization filter |
| **Pollen load** | Amount of pollen collected by bee (mg) — proxy for foraging success |
| **d/L (straightness)** | Displacement / path length ratio — 1.0 = perfectly straight path |
| **Inner circle** | r = 21 cm from feeder — the feeding zone |
| **Outer circle** | r = 42 cm from feeder — the search boundary |
| **Exit direction** | Angle (in degrees) at which bee crosses the outer circle boundary |
| **Heatmap** | 2D density plot showing where bees spent most time |

---

*Last updated: June 2025 | Analysis: Antigravity AI × Marie Jansen*
*Repository: [github.com/yakkshit/navigation-bees](https://github.com/yakkshit/navigation-bees)*
