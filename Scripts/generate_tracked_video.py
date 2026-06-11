#!/usr/bin/env python3
"""
Generate tracked video from TREX CSV output with angle visualization.
Shows bee position, orientation angle, speed, and detection status.
"""

import cv2
import pandas as pd
import numpy as np
from pathlib import Path
import os
from dotenv import load_dotenv
import sys

# Load env config
env_path = Path(__file__).parent.parent / ".env.local"
if env_path.exists():
    load_dotenv(env_path)
elif (Path(__file__).parent.parent / ".env").exists():
    load_dotenv(Path(__file__).parent.parent / ".env")

# Configuration
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/Users/yakkshit/Downloads/project/hiwi2/p1/V_OUTPUTS"))
INPUT_VIDEO_DIR = Path(os.getenv("INPUT_VIDEO_DIR", os.getenv("INPUT_DIR", "/Users/yakkshit/Downloads/project/hiwi2/p1/Videos")))

def parse_settings(settings_path):
    """Read cm_per_pixel, source video path, and track_include from a TRex settings file."""
    cm_per_pixel = 0.0773
    source_video = None
    track_include = None
    if not settings_path.exists():
        return cm_per_pixel, source_video, track_include

    with open(settings_path) as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"')
            if key == "cm_per_pixel":
                try:
                    cm_per_pixel = float(val)
                except ValueError:
                    pass
            elif key == "meta_source_path":
                source_video = Path(val)
            elif key == "track_include":
                try:
                    import json
                    track_include = json.loads(val)
                except Exception:
                    pass
    return cm_per_pixel, source_video, track_include

def find_source_video(video_dir, settings_path):
    """Resolve the exact source video for a TRex output folder."""
    _, source_from_settings, _ = parse_settings(settings_path)
    if source_from_settings and source_from_settings.exists():
        return source_from_settings

    video_name = video_dir.name
    exact = INPUT_VIDEO_DIR / f"{video_name}.mp4"
    if exact.exists():
        return exact

    matches = sorted(INPUT_VIDEO_DIR.glob(f"{video_name}.*"))
    for candidate in matches:
        if candidate.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"}:
            return candidate

    raise FileNotFoundError(
        f"No source video found for '{video_name}' in {INPUT_VIDEO_DIR}"
    )
    

def generate_tracked_video(video_name=None):
    """Generate tracked video with angle visualization."""

    if video_name:
        video_dirs = [d for d in OUTPUT_DIR.iterdir() if d.is_dir() and video_name in d.name]
        if not video_dirs:
            print(f"❌ Video folder matching '{video_name}' not found")
            return False
        video_dir = sorted(video_dirs)[0]
    else:
        video_dirs = [d for d in OUTPUT_DIR.iterdir() if d.is_dir() and (d / "data").exists()]
        if not video_dirs:
            print("❌ No video folders with tracking data found")
            return False
        video_dir = sorted(video_dirs)[-1]

    print(f"\n📹 Processing: {video_dir.name}")

    csv_files = list((video_dir / "data").glob("*_id0.csv"))
    if not csv_files:
        print(f"❌ No tracking CSV found in {video_dir / 'data'}")
        return False

    csv_path = csv_files[0]
    print(f"   CSV: {csv_path.name}")

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"❌ Failed to read CSV: {e}")
        return False

    print(f"   Frames in CSV: {len(df)}")

    settings_candidates = [
        video_dir / f"{video_dir.name}.settings",
        video_dir / f"{csv_path.stem.rsplit('_id', 1)[0]}.settings",
    ]
    settings_path = next((p for p in settings_candidates if p.exists()), settings_candidates[0])
    cm_per_pixel, _, track_include_poly = parse_settings(settings_path)

    try:
        video_path = find_source_video(video_dir, settings_path)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return False

    print(f"   Video: {video_path.name}")
    print(f"   cm_per_pixel: {cm_per_pixel}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"❌ Failed to open video: {video_path}")
        return False

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"   Resolution: {width}x{height} @ {fps:.1f} FPS")
    print(f"   Video frames: {total_frames}")

    output_video_path = video_dir / f"{video_dir.name}_tracked.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_video_path), fourcc, fps, (width, height))

    if not out.isOpened():
        print("❌ Failed to create output video")
        return False

    print(f"   Output: {output_video_path.name}")

    frame_col = "frame" if "frame" in df.columns else df.columns[0]
    tracking_by_frame = {
        int(row[frame_col]): row
        for _, row in df.iterrows()
        if pd.notna(row[frame_col])
    }

    # Determine arena center/radius for drawing the boundary overlay.
    # Default: centered at ~(640, 360) with radius ~295px based on camera setup.
    
    # Default fallback center (middle of the image)
    # arena_center = (width // 2, height // 2)
    # arena_radius = min(width, height) * 30 // 100 

    # Tweak these numbers manually until the circle aligns perfectly with feeder
    manual_center_x = (width // 2) - 50  # Shifts 15 pixels to the left
    manual_center_y = (height // 2) + 5  # Shifts 20 pixels down

    arena_center = (manual_center_x, manual_center_y)
    arena_radius = 230  # Adjust radius value in pixels directly to frame the mirror edge

    # If track_include polygon exists, compute its bounding circle as a visual hint.
    if track_include_poly and len(track_include_poly) > 0 and len(track_include_poly[0]) > 0:
        poly_pts = np.array(track_include_poly[0], dtype=np.float32)
        (cx, cy), cr = cv2.minEnclosingCircle(poly_pts)
        inner_center = (int(cx), int(cy))
        inner_radius = int(cr)
        print(f"   Track-include zone: center=({int(cx)},{int(cy)}), radius={inner_radius}px")
    else:
        inner_center = None
        inner_radius = None

    detection_count = 0
    total_processed = 0
    last_x_px = None
    last_y_px = None

    for frame_idx in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            break

        # Draw arena boundary on every frame (full outer arena in white)
        cv2.circle(frame, arena_center, arena_radius, (200, 200, 200), 2)
        #                  ↑ position   ↑ radius       ↑ gray color    ↑ line thickness
        # If a track_include polygon was set, draw it in yellow so it's visible
        if inner_center is not None:
            cv2.circle(frame, inner_center, inner_radius, (0, 255, 255), 1)

        row = tracking_by_frame.get(frame_idx)
        if row is None:
            # Draw frame counter even for untracked frames
            cv2.putText(
                frame,
                f"Frame: {frame_idx}/{total_frames}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (150, 150, 150),
                2,
            )
            out.write(frame)
            total_processed += 1
            continue

        is_missing = row["missing"] == 1.0

        try:
            x_cm = row["X (cm)"]
            y_cm = row["Y (cm)"]
            angle = row["ANGLE"]
            speed = row["SPEED (cm/s)"]
        except KeyError:
            x_cm = np.inf
            y_cm = np.inf
            angle = np.inf
            speed = 0

        if np.isfinite(x_cm) and np.isfinite(y_cm):
            x_px = int(x_cm / cm_per_pixel)
            y_px = int(y_cm / cm_per_pixel)
        else:
            x_px = width // 2
            y_px = height // 2

        x_px = max(0, min(x_px, width - 1))
        y_px = max(0, min(y_px, height - 1))
        angle = angle if np.isfinite(angle) else 0

        if not is_missing:
            detection_count += 1
            last_x_px = x_px
            last_y_px = y_px
            cv2.circle(frame, (x_px, y_px), 15, (0, 255, 0), 2)

            if pd.notna(angle):
                line_len = 40
                end_x = int(x_px + line_len * np.cos(angle))
                end_y = int(y_px + line_len * np.sin(angle))
                cv2.line(frame, (x_px, y_px), (end_x, end_y), (0, 255, 0), 2)

            if pd.notna(speed) and speed > 0:
                cv2.putText(
                    frame,
                    f"Speed: {speed:.2f} cm/s",
                    (x_px + 20, y_px - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1,
                )

            if pd.notna(angle):
                angle_deg = np.degrees(angle)
                cv2.putText(
                    frame,
                    f"Angle: {angle_deg:.1f} deg",
                    (x_px + 20, y_px + 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1,
                )
        else:
            # MISSING: draw red X at last known position if available, else at CSV position
            draw_x = x_px if (np.isfinite(row["X (cm)"] if "X (cm)" in row else np.inf)) else (last_x_px or x_px)
            draw_y = y_px if (np.isfinite(row["Y (cm)"] if "Y (cm)" in row else np.inf)) else (last_y_px or y_px)
            cv2.circle(frame, (draw_x, draw_y), 15, (0, 0, 255), 2)
            cv2.line(frame, (draw_x - 10, draw_y - 10), (draw_x + 10, draw_y + 10), (0, 0, 255), 2)
            cv2.line(frame, (draw_x - 10, draw_y + 10), (draw_x + 10, draw_y - 10), (0, 0, 255), 2)

        status = "DETECTED" if not is_missing else "MISSING"
        status_color = (0, 255, 0) if not is_missing else (0, 0, 255)
        cv2.putText(
            frame,
            f"Frame: {frame_idx}/{total_frames} - {status}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            status_color,
            2,
        )

        out.write(frame)
        total_processed += 1

        if total_processed % 100 == 0:
            print(f"   Progress: {total_processed}/{total_frames} frames", end="\r")

    cap.release()
    out.release()

    detection_pct = 100 * detection_count / total_processed if total_processed > 0 else 0

    print(f"\n✅ Tracked video created: {output_video_path.name}")
    print(f"   Detected frames: {detection_count}/{total_processed} ({detection_pct:.1f}%)")
    print(f"   File size: {output_video_path.stat().st_size / (1024 * 1024):.1f} MB")

    return True

def diagnose_tracking_quality():
    """Analyze why tracking quality might be low."""

    print("\n" + "=" * 60)
    print("🔍 TRACKING QUALITY DIAGNOSIS")
    print("=" * 60)

    summary_csv = OUTPUT_DIR / "tracking_quality_summary.csv"
    if not summary_csv.exists():
        print("❌ Quality summary not found. Run check_tracking_quality.py first.")
        return

    df_quality = pd.read_csv(summary_csv)
    print(f"\n📊 Summary: {len(df_quality)} video(s)")
    print(df_quality.to_string(index=False))

    video_dirs = [d for d in OUTPUT_DIR.iterdir() if d.is_dir() and (d / "data").exists()]
    if video_dirs:
        latest_dir = sorted(video_dirs)[-1]
        csv_file = list((latest_dir / "data").glob("*_id0.csv"))[0]
        df = pd.read_csv(csv_file)

        print(f"\n📝 Latest video analysis: {latest_dir.name}")
        print(f"   Total frames: {len(df)}")
        print(f"   Detected: {(df['missing'] == 0).sum()}")
        print(f"   Missing: {(df['missing'] == 1).sum()}")
        print(
            f"   Avg body size (pixels): {df['num_pixels'].mean():.0f} "
            f"(min: {df['num_pixels'].min():.0f}, max: {df['num_pixels'].max():.0f})"
        )

        settings_file = latest_dir / f"{latest_dir.name}.settings"
        if settings_file.exists():
            print("\n⚙️ TREX Settings:")
            with open(settings_file) as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line:
                        key, val = line.split("=", 1)
                        if any(x in key for x in ["detect", "track", "size", "threshold", "cm_per_pixel"]):
                            print(f"   {key:30} = {val}")

        detection_pct = 100 * (df["missing"] == 0).sum() / len(df)
        print("\n💡 Recommendations:")
        if detection_pct < 30:
            print("   ⚠️ Detection rate is VERY LOW (<30%). Possible causes:")
            print("      • Video contrast/lighting issues - check average_*.png")
            print("      • Bee body size changed - check num_pixels range")
            print("      • Background subtraction threshold too high")
            print("      • Bee not present in some sections of video")
        elif detection_pct < 70:
            print("   ⚠️ Detection rate is LOW (<70%). Consider:")
            print("      • Adjusting detect_threshold parameter")
            print("      • Checking track_size_filter bounds")
            print("      • Verifying video lighting/contrast")
        else:
            print("   ✅ Detection rate is good (>70%)")

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🐝 Bumblebee Tracking - Video Generation & Diagnosis")
    print("=" * 60)

    video_name = sys.argv[1] if len(sys.argv) > 1 else None
    success = generate_tracked_video(video_name)

    if success:
        diagnose_tracking_quality()

    print("\n" + "=" * 60)
