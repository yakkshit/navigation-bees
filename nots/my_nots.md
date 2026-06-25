## **Walkthrough - Arena Circle Alignment and Calibration**

I have successfully updated the calibration parameters and adjusted the circle drawing and post-processing code to resolve the alignment issues in the bumblebee tracking pipeline.

## **Changes Made**

### 1\. Tracking Settings Updated

*   **working.settings**, **bee\_tracking.settings**, and **Data/first.settings**:
    *   Calibrated `cm_per_pixel` from `0.0773` to `0.1546` to map physical arena measurements (84 cm diameter) to pixel coordinates (~271.6 pixel radius).
    *   Updated `meta_real_width` to `197.89` to match the real-world frame width ($1280 \\times 0.1546\\text{ cm}$).

### 2\. Post-Processing Code Adjusted

*   **post\_process\_tracking.py**:
    *   Corrected default settings to `cm_per_pixel = 0.1546` and `meta_real_width = 197.89`.
    *   Modified `compute_dist_to_center` to **prefer Euclidean distance** ($hypot(x - cx, y - cy)$) from X/Y coordinates over TRex's `border_distance` column. This fixes the issue of negative distance values in the CSV and ensures reliable tracking metrics.

### 3\. Video Visualization Code Updated

*   **generate\_tracked\_video.py**:
    *   Updated default `cm_per_pixel` to `0.1546`.
    *   Verified that the circles are drawn using the correct radius variables:
        *   Outer boundary (84 cm physical diameter) is drawn at `r = 272` pixels in gray/white.
        *   Inner zone (42 cm physical diameter) is drawn at `r = 136` pixels in yellow.

## **Verification & Testing**

I isolated a video (`2025-04-22 16-28-22.mp4`) and ran the tracking and post-processing steps:

1.  **TRex Tracking**: Successfully ran TRex using the updated `working.settings` to output new raw tracking data.
2.  **Post-Processing**: Ran the updated `post_process_tracking.py` to calculate distances and flag circle events. The output CSV columns (`dist_to_center_cm`, `in_inner_circle`, `in_outer_circle`, `circle_event`) are now properly calculated and reflect positive physical distances.
3.  **Video Overlay Generation**: Ran `generate_tracked_video.py` to create the tracked video showing:
    *   The outer (gray/white) circle at $r = 272\\text{ px}$ (matching the physical table rim).
    *   The inner (yellow) circle at $r = 136\\text{ px}$ (correctly centered and scaled inside the outer circle).

The new tracked video has been saved in the output directory:

*   2025-04-22 16-28-22\_tracked.mp4

##  Version 2  
  
  
\# Walkthrough - Bee Tracking Restoration and Heading Angle Estimation

I have successfully updated the settings and code to resolve both the low detection rate and the noisy head/tail flipping posture issue.

\## Changes Made

\### 1. Tracking Restored  
\* \*\*Settings files (\`working.settings\`, \`bee\_tracking.settings\`, \`Data/first.settings\`)\*\*:  
 \* Set \`detect\_threshold = 7\` (restored from \`5\` to prevent background noise from overwhelming the tracker).  
 \* Adjusted \`track\_size\_filter\` to \`\[\[0.35, 3.6\]\]\`. Disabling the size filter completely caused TRex to get overwhelmed by static background noise blobs. Calibrating the size bounds to the new scale ($15\\text{ to }150\\text{ px}$ corresponding to $0.35\\text{ to }3.6\\text{ cm}^2$) successfully restored the bee tracking.  
 \* Verified that the bee detection rate is fully restored (20.4% on the test video).

\### 2. Displacement-Based Heading Angle Implemented  
\* \*\*\[post\_process\_tracking.py\](file:///Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee\_task/Scripts/post\_process\_tracking.py)\*\*:  
 \* Added a heading angle calculation based on position changes (displacement) over a 3-frame rolling window to eliminate frame-by-frame centroid jitter.  
 \* \*\*Speed-Thresholding Logic\*\*: The heading angle updates only when the bee is walking at a speed $>1.5\\text{ cm/s}$.  
 \* \*\*Carry-Forward Logic\*\*: When the bee is stationary or moving extremely slowly, the system carries forward the last valid direction angle, preventing the heading vector from flipping or rotating randomly.  
 \* Saved the new heading coordinate to the \`HEADING\_ANGLE\` column in the output \`\*\_id0\_new.csv\` and \`HEADING\_ANGLE\_rad\` in the event summaries.

\### 3. Tracked Video Visualization Updated  
\* \*\*\[generate\_tracked\_video.py\](file:///Users/yakkshit/Downloads/project/hiwi2/p1/bumblebee\_task/Scripts/generate\_tracked\_video.py)\*\*:  
 \* Modified the video overlays to prefer the new \`HEADING\_ANGLE\` column over TRex's raw posture \`ANGLE\` for drawing the green direction vector.

\---

\## Verification Results

\* The tracking now completes successfully with correct physical coordinate scales.  
\* The position-based heading angle resolves the 180-degree posture flipping issue. The orientation vector remains stable and points correctly in the direction of movement.  
\* Output files have been saved to: \[V\_OUTPUTS/2025-04-22 16-28-22/\](file:///Users/yakkshit/Downloads/project/hiwi2/p1/V\_OUTPUTS/2025-04-22%2016-28-22/)