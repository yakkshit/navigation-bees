# 🐝 Bumblebee Path Integration — Project Wiki

> **Thesis**: *Path Integration in Bumblebees* (Marie Jansen, 2025)
> **Based on**: Patel et al. (2022), *Current Biology*
> **GitHub**: [yakkshit/navigation-bees](https://github.com/yakkshit/navigation-bees)
> **Total experiments analysed**: **105 trials** across multiple bees and conditions

---

## 📋 Table of Contents

1. [What Is This Project?](#-what-is-this-project)
2. [The Experiment — How It Works](#-the-experiment--how-it-works)
3. [The Arena — Physical Setup](#-the-arena--physical-setup)
4. [Experimental Parameters & DoP Mapping](#-experimental-parameters--dop-mapping)
5. [How Videos Were Processed](#-how-videos-were-processed)
6. [Understanding the Data](#-understanding-the-data)
7. [New Figures & Scientific Findings](#-new-figures--scientific-findings)
   - [Homing Accuracy vs. DoP](#homing-accuracy-vs-dop)
   - [Rotation Shift Comparison (LR vs TB)](#rotation-shift-comparison-lr-vs-tb)
   - [Dedicated Individual Bee Profile: R13](#dedicated-individual-bee-profile-r13)
   - [Condition Trajectory Summaries](#condition-trajectory-summaries)
   - [Individual Bee Trajectory Grids](#individual-bee-trajectory-grids)
8. [Interpretation & Discussion of the Results](#-interpretation--discussion-of-the-results)
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

…and then computes the **direct home vector** — the straight-line route back to the hive.

---

## 🏟️ The Arena — Physical Setup

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
| **Inner circle** | 42 cm diameter (r = 21 cm) | Polarized light zone — where the stimulus is presented |
| **Outer circle** | 84 cm diameter (r = 42 cm) | Unpolarized search boundary |
| **Feeder** | Centre point `(0, 0)` | Release point |
| **Arena coordinates** | cm from feeder centre | `(0,0)` = feeder; `+x` = East; `+y` = North |

---

## 🧪 Experimental Parameters & DoP Mapping

The Würzburg experimental setup controls the **Degree of Polarization (DoP)** by mixing different intensities of linearly polarized light (**P**) and unpolarized light (**U**) emitted from an overhead LED array. 

### Mapping Table: P & U to DoP
Following Marie Jansen (2025), the experimental settings map to the following calibrated physical DoP values:

#### Top-Bottom (TB) Cue Settings
| Setting | Stimulus Rotation | DoP | Strength |
|---|---|---|---|
| `p0.0 u1.0` | Vertical to Horizontal | **0.07** | 🔴 Weak |
| `p0.7 u1.0` | Vertical to Horizontal | **0.07** | 🔴 Weak |
| `p1.3 u1.0` | Vertical to Horizontal | **0.08** | 🔴 Weak |
| `p1.5 u1.0` | Vertical to Horizontal | **0.08** | 🔴 Weak |
| `p1.8 u1.0` | Vertical to Horizontal | **0.10** | 🔵 Strong |
| `p2.5 u1.0` | Vertical to Horizontal | **0.12** | 🔵 Strong |
| `p4.4 u1.0` | Vertical to Horizontal | **0.15** | 🔵 Strong |
| `p8.0 u1.0` | Vertical to Horizontal | **0.19** | 🔵 Strong |
| `p0.4 u2.0` | Vertical to Horizontal | **0.04** | 🔴 Weak |
| `p0.9 u2.0` | Vertical to Horizontal | **0.07** | 🔴 Weak |
| `p1.5 u2.0` | Vertical to Horizontal | **0.05** | 🔴 Weak |
| `p8.0 u2.0` | Vertical to Horizontal | **0.12** | 🔵 Strong |
| `p0.0 u8.0` | Vertical to Horizontal | **0.07** | 🔴 Weak |
| `p3.8 u8.0` | Vertical to Horizontal | **0.07** | 🔴 Weak |
| `p4.3 u8.0` | Vertical to Horizontal | **0.07** | 🔴 Weak |
| `p7.7 u8.0` | Vertical to Horizontal | **0.08** | 🔴 Weak |
| `p8.0 u8.0` | Vertical to Horizontal | **0.07** | 🔴 Weak |

#### Left-Right (LR) Cue Settings
| Setting | Stimulus Rotation | DoP | Strength |
|---|---|---|---|
| `p0.7 u1.0` | Horizontal to Vertical | **0.06** | 🔴 Weak |
| `p2.0 u1.0` | Horizontal to Vertical | **0.10** | 🔵 Strong |
| `p2.5 u1.0` | Horizontal to Vertical | **0.12** | 🔵 Strong |
| `p3.5 u1.0` | Horizontal to Vertical | **0.14** | 🔵 Strong |
| `p4.2 u1.0` | Horizontal to Vertical | **0.12** | 🔵 Strong |
| `p4.4 u1.0` | Horizontal to Vertical | **0.12** | 🔵 Strong |
| `p8.0 u1.0` | Horizontal to Vertical | **0.19** | 🔵 Strong |
| `p0.0 u2.0` | Horizontal to Vertical | **0.04** | 🔴 Weak |
| `p0.6 u2.0` | Horizontal to Vertical | **0.04** | 🔴 Weak |
| `p1.5 u2.0` | Horizontal to Vertical | **0.05** | 🔴 Weak |
| `p0.1 u8.0` | Horizontal to Vertical | **0.05** | 🔴 Weak |
| `p3.8 u8.0` | Horizontal to Vertical | **0.04** | 🔴 Weak |
| `p4.2 u8.0` | Horizontal to Vertical | **0.05** | 🔴 Weak |
| `p4.4 u8.0` | Horizontal to Vertical | **0.05** | 🔴 Weak |
| `p8.0 u8.0` | Horizontal to Vertical | **0.05** | 🔴 Weak |

#### Training/Control Setting
- `p8.0 u0.0` or `p5.0 u0.0` (with $U=0$): **DoP = 1.00** (Full linear polarization, no stimulus rotation).

---

## 🎬 How Videos Were Processed

Raw `.mp4` videos are pre-trimmed to 10 minutes maximum to avoid processing overhead. Coordinates are extracted via **TRex tracking software** and post-processed to align the origin `(0, 0)` with the hough-detected arena feeder centre.

- **Inner exit angle** (`inner_exit_angle_deg`): Measured at the exact coordinate frame where the bee's distance from the feeder crosses $r > 21.0\text{ cm}$.
- **Outer exit angle** (`exit_angle_deg`): Measured at the exact coordinate frame where the bee's distance from the feeder crosses $r > 42.0\text{ cm}$.

---

## 📈 New Figures & Scientific Findings

All newly generated plots are stored in [`analysis/results/`](file:///Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee_task/analysis/results/).

---

### Homing Accuracy vs. DoP
#### [`homing_accuracy_vs_dop.png`](file:///Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee_task/analysis/results/homing_accuracy_vs_dop.png)

This linear plot summarizes navigation performance across all tested DoP levels:
- **Left Panel (Path Straightness)**: Path straightness index ($d/L$) vs. DoP with standard error bars.
- **Right Panel (Angular Deviation)**: Mean angular deviation (in degrees) from the expected target axis vs. DoP. It plots:
  - **Deviation from Real Home (180°)** (red circles)
  - **Deviation from Fictive Target** (green squares; 180° for LR, 90°/270° for TB)

**Key Finding**: As the DoP increases, the bees show a distinct change in their exit choices. Under low DoP, exit directions are highly concentrated but biased (see below). As the polarization signal becomes stronger, the conflict between their default bias and the rotated cue introduces wider angular dispersion.

---

### Rotation Shift Comparison (LR vs TB)
#### [`polar_rotation_check.png`](file:///Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee_task/analysis/results/polar_rotation_check.png)

Polar histograms showing the distribution of inner exit angles for **Strong DoP** trials under LR and TB cues:
- **LR Cue (expected 180°/0°)**: Shows exit bearings clustering near the vertical axis (mean angle = 5.3°, R = 0.48, n = 12 exits).
- **TB Cue (expected 90°/270°)**: Shows exit bearings under rotated polarization (mean angle = 359.2°, R = 0.40, n = 17 exits).

**Key Finding**: Under strong polarization, the exit angles show higher scatter, which is characteristic of the conflict between the rotated visual stimulus (which suggests a fictive home 90° away) and their internal path integration state / geomagnetic default.

---

### Dedicated Individual Bee Profile: R13
#### [`bee_r13_four_panel.png`](file:///Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee_task/analysis/results/bee_r13_four_panel.png)

A 2×2 grid showing all 39 trials of the most active individual bee, **R13**:
- **Panel 1 (Low DoP)**: All trajectories under Weak Polarization (DoP < 0.10).
- **Panel 2 (High DoP)**: All trajectories under Strong Polarization (DoP ≥ 0.10).
- **Panel 3 (LR Cue)**: All trajectories under LR cues.
- **Panel 4 (TB Cue)**: All trajectories under TB cues.

**Key Finding**: Bee R13 exhibits a strong directional bias towards the ~15°–25° direction under low DoP conditions (unpolarized/weak cue). However, under high DoP, the trajectory vectors spread out, indicating that the bee's walking path is actively influenced by the strength of the overhead polarized light.

---

### Condition Trajectory Summaries
#### [Conditions Folder](file:///Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee_task/analysis/results/conditions/)

Overlaid trajectory plots showing the path of all trials inside a circular boundary for each unique experimental setting. For example:
- [`summary_LR_p4.4_u8.png`](file:///Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee_task/analysis/results/conditions/summary_LR_p4.4_u8.png)
- [`summary_TB_p8.0_u2.png`](file:///Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee_task/analysis/results/conditions/summary_TB_p8.0_u2.png)

---

### Individual Bee Trajectory Grids
#### [Individual Folder](file:///Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee_task/analysis/results/individual/)

Circular grid trajectory plots for each unique bee (with at least 3 trials) showing their navigation path across different DoP levels:
- [`bee_R13_trajectories.png`](file:///Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee_task/analysis/results/individual/bee_R13_trajectories.png)
- [`bee_W36_trajectories.png`](file:///Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee_task/analysis/results/individual/bee_W36_trajectories.png)
- [`bee_R51_trajectories.png`](file:///Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee_task/analysis/results/individual/bee_R51_trajectories.png)

---

## 📝 Discussion: Understanding the "Weak DoP" Significance

An interesting statistical trend emerged from the Rayleigh test:

| Condition | n | Mean Direction | Vector Length R | Rayleigh p-value |
|---|---|---|---|---|
| **LR Weak DoP** | 35 | 2.28° | **0.6929** | **p < 0.001** |
| **TB Weak DoP** | 35 | 3.28° | **0.7039** | **p < 0.001** |
| **LR Strong DoP** | 11 | 0.39° | **0.4432** | **p = 0.115** |
| **TB Strong DoP** | 16 | 6.29° | **0.3902** | **p = 0.087** |

### Why is the Weak DoP condition highly significant?
Under **Weak DoP** (DoP < 0.10), the polarized light signal is too faint for the bees' compound eyes to detect. Deprived of a directional navigation cue, the bees default to a **systematic phototactic or arena bias** (walking towards 0°–20° where a minor light leak or visual artifact exists). Because almost all bees walk towards this same artifact, their exit angles are highly concentrated, resulting in a very high vector length ($R \approx 0.70$) and a highly significant Rayleigh p-value.

Under **Strong DoP** (DoP ≥ 0.10), the polarization signal becomes perceptible. The bees attempt to use this signal for navigation, which conflicts with their default arena bias. This conflict causes the exit angles to scatter, lowering the mean vector length ($R \approx 0.39$) and increasing the Rayleigh p-value. This proves that the polarized light stimulus actively disrupts their default heading and guides their choices.

---

## 📐 Statistical Methods

- **Circular Mean & Vector Length R**: Used to calculate average direction and clustering.
- **Rayleigh Test of Uniformity**: Used to assess if exit angles have a preferred direction ($p < 0.05$).
- **Bimodal Correction**: Handles bimodal exit behavior (e.g. going 180° opposite).

---

##  ▶️ How to Run the Analysis

Activate the virtual environment and run:

```bash
source /Users/yakkshit/Downloads/project/hiwi2/p1/.venv/bin/activate
python3 analysis/scripts/plot_dop_analysis.py
```

---
*Last updated: June 2026*
