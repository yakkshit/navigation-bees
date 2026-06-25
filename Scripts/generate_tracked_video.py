#!/usr/bin/env python3
"""
Generate tracked video from TREX CSV output with angle visualization.
Shows bee position, orientation angle, speed, and detection status.
Optimized for multi-core processors using thread-based queues for frame I/O.
"""

import cv2
import pandas as pd
import numpy as np
from pathlib import Path
import os
import queue
import threading
import sys
from dotenv import load_dotenv

from arena_config import load_circle_config, arena_center_px, radius_px, find_source_video

# Load env config
env_path = Path(__file__).parent.parent / ".env.local"
if env_path.exists():
    load_dotenv(env_path)
elif (Path(__file__).parent.parent / ".env").exists():
    load_dotenv(Path(__file__).parent.parent / ".env")

# Configuration
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/Users/yakkshit/Downloads/project/hiwi2/p1/V_OUTPUTS"))
INPUT_VIDEO_DIR = Path(os.getenv("INPUT_VIDEO_DIR", os.getenv("INPUT_DIR", "/Users/yakkshit/Downloads/project/hiwi2/p1/Videos")))
# Set FULL_RES=1 to write at original resolution (slower). Default: half-res for speed.
FULL_RES = os.getenv("FULL_RES", "0") == "1"


class ThreadedVideoReader:
    def __init__(self, video_path, queue_size=256):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(str(video_path))
        self.queue = queue.Queue(maxsize=queue_size)
        self.stopped = False
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def _reader(self):
        frame_idx = 0
        while not self.stopped:
            ret, frame = self.cap.read()
            if not ret:
                self.queue.put((None, None))
                break
            self.queue.put((frame_idx, frame))
            frame_idx += 1
        self.cap.release()

    def read(self):
        return self.queue.get()

    def stop(self):
        self.stopped = True
        self.cap.release()


class ThreadedVideoWriter:
    def __init__(self, output_path, fourcc, fps, size, queue_size=256):
        self.out = cv2.VideoWriter(str(output_path), fourcc, fps, size)
        self.queue = queue.Queue(maxsize=queue_size)
        self.stopped = False
        self.thread = threading.Thread(target=self._writer, daemon=True)
        self.thread.start()

    def _writer(self):
        while not self.stopped:
            frame = self.queue.get()
            if frame is None:
                break
            self.out.write(frame)
        self.out.release()

    def write(self, frame):
        self.queue.put(frame)

    def close(self):
        self.queue.put(None)
        self.thread.join()


def parse_settings(settings_path):
    """Read cm_per_pixel, source video path, and track_include from a TRex settings file."""
    cm_per_pixel = 0.1546
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

    csv_files = list((video_dir / "data").glob("*_id0_new.csv"))
    if not csv_files:
        csv_files = list((video_dir / "data").glob("*_id0.csv"))
        csv_files = [p for p in csv_files if not p.name.endswith("_id0_new.csv")]
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
        video_path = find_source_video(video_dir, settings_path, INPUT_VIDEO_DIR)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return False

    print(f"   Video: {video_path.name}")
    print(f"   cm_per_pixel: {cm_per_pixel}")

    # Temporary cap to read video meta properties
    cap_temp = cv2.VideoCapture(str(video_path))
    if not cap_temp.isOpened():
        print(f"❌ Failed to open video: {video_path}")
        return False

    fps = cap_temp.get(cv2.CAP_PROP_FPS)
    width = int(cap_temp.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap_temp.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap_temp.get(cv2.CAP_PROP_FRAME_COUNT))
    cap_temp.release()

    # Determine output resolution — half-res by default for speed
    if FULL_RES or width <= 960:
        out_width, out_height = width, height
        scale = 1.0
    else:
        out_width, out_height = width // 2, height // 2
        scale = 0.5

    print(f"   Resolution: {width}x{height} → output {out_width}x{out_height} @ {fps:.1f} FPS")
    print(f"   Video frames: {total_frames}")

    output_video_path = video_dir / f"{video_dir.name}_tracked.mp4"
    # Try avc1 for fast hardware-assisted encoding, fallback to mp4v
    fourcc = cv2.VideoWriter_fourcc(*"avc1")
    test_writer = cv2.VideoWriter(str(output_video_path), fourcc, fps, (out_width, out_height))
    if not test_writer.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        test_writer.release()
    else:
        test_writer.release()

    # Start threaded reader and writer
    reader = ThreadedVideoReader(video_path)
    writer = ThreadedVideoWriter(output_video_path, fourcc, fps, (out_width, out_height))

    print(f"   Output: {output_video_path.name}")

    frame_col = "frame" if "frame" in df.columns else df.columns[0]
    tracking_by_frame = {
        int(row[frame_col]): row
        for _, row in df.iterrows()
        if pd.notna(row[frame_col])
    }

    # Arena circles — scale to output resolution
    circle_cfg = load_circle_config(video_dir.name)
    arena_center_full = arena_center_px(width, height, circle_cfg, cm_per_pixel, video_name=video_path.name, video_path=video_path)
    arena_center = (int(arena_center_full[0] * scale), int(arena_center_full[1] * scale))
    outer_radius = radius_px(circle_cfg["outer_radius_cm"], cm_per_pixel / scale if scale != 1.0 else cm_per_pixel)
    inner_radius = radius_px(circle_cfg["inner_radius_cm"], cm_per_pixel / scale if scale != 1.0 else cm_per_pixel)
    print(f"   Outer arena: Ø{circle_cfg['outer_diameter_cm']}cm → r={outer_radius}px")
    print(f"   Inner zone:  Ø{circle_cfg['inner_diameter_cm']}cm → r={inner_radius}px")
    print(f"   Arena center: {arena_center}")

    inner_center = arena_center
    inner_radius_draw = inner_radius

    detection_count = 0
    total_processed = 0
    last_x_px = None
    last_y_px = None

    # Font scale for half-res output
    font_scale = 0.6 if scale < 1.0 else 0.7
    font_scale_small = 0.4 if scale < 1.0 else 0.5

    while True:
        frame_idx, frame = reader.read()
        if frame is None:
            break

        # Resize if needed for faster encoding
        if scale != 1.0:
            frame = cv2.resize(frame, (out_width, out_height), interpolation=cv2.INTER_LINEAR)

        # Outer arena boundary (84 cm diameter) — gray circle
        cv2.circle(frame, arena_center, outer_radius, (200, 200, 200), 2, cv2.LINE_AA)
        # Inner feeder zone (42 cm diameter) — yellow circle
        cv2.circle(frame, inner_center, inner_radius_draw, (0, 255, 255), 1, cv2.LINE_AA)

        row = tracking_by_frame.get(frame_idx)
        if row is None:
            # Draw frame counter even for untracked frames
            cv2.putText(
                frame,
                f"Frame: {frame_idx}/{total_frames}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (150, 150, 150),
                2,
                cv2.LINE_AA,
            )
            writer.write(frame)
            total_processed += 1
            continue

        is_missing = row["missing"] == 1.0
        outside_arena = row.get("outside_arena", 0) == 1 if "outside_arena" in row.index else False
        if outside_arena:
            is_missing = True

        circle_event = ""
        if "circle_event" in row.index and pd.notna(row["circle_event"]) and str(row["circle_event"]).strip():
            circle_event = str(row["circle_event"]).strip()

        try:
            x_cm = row["X (cm)"]
            y_cm = row["Y (cm)"]
            angle = row["HEADING_ANGLE"] if "HEADING_ANGLE" in row.index and pd.notna(row["HEADING_ANGLE"]) else row["ANGLE"]
            speed = row["SPEED (cm/s)"]
        except KeyError:
            x_cm = np.inf
            y_cm = np.inf
            angle = np.inf
            speed = 0

        if np.isfinite(x_cm) and np.isfinite(y_cm):
            x_px = int(x_cm / cm_per_pixel * scale)
            y_px = int(y_cm / cm_per_pixel * scale)
        else:
            x_px = out_width // 2
            y_px = out_height // 2

        x_px = max(0, min(x_px, out_width - 1))
        y_px = max(0, min(y_px, out_height - 1))
        angle = angle if np.isfinite(angle) else 0

        detection_count += 1 if not is_missing and row.get("arena_tracked", 1 if not is_missing else 0) == 1 else 0
        if not is_missing:
            last_x_px = x_px
            last_y_px = y_px
            color = (0, 255, 0) if row.get("in_inner_circle", 0) != 1 else (0, 200, 255)
            cv2.circle(frame, (x_px, y_px), 15, color, 2, cv2.LINE_AA)

            if pd.notna(angle):
                line_len = 40
                end_x = int(x_px + line_len * np.cos(angle))
                end_y = int(y_px + line_len * np.sin(angle))
                cv2.line(frame, (x_px, y_px), (end_x, end_y), (0, 255, 0), 2, cv2.LINE_AA)

            if pd.notna(speed) and speed > 0:
                cv2.putText(
                    frame,
                    f"Speed: {speed:.2f} cm/s",
                    (x_px + 20, y_px - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale_small,
                    (0, 255, 0),
                    1,
                    cv2.LINE_AA,
                )

            if pd.notna(angle):
                angle_deg = np.degrees(angle)
                cv2.putText(
                    frame,
                    f"Angle: {angle_deg:.1f} deg",
                    (x_px + 20, y_px + 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale_small,
                    (0, 255, 0),
                    1,
                    cv2.LINE_AA,
                )
        else:
            # MISSING: draw red X at last known position if available, else at CSV position
            draw_x = x_px if (np.isfinite(row["X (cm)"] if "X (cm)" in row else np.inf)) else (last_x_px or x_px)
            draw_y = y_px if (np.isfinite(row["Y (cm)"] if "Y (cm)" in row else np.inf)) else (last_y_px or y_px)
            cv2.circle(frame, (draw_x, draw_y), 15, (0, 0, 255), 2, cv2.LINE_AA)
            cv2.line(frame, (draw_x - 10, draw_y - 10), (draw_x + 10, draw_y + 10), (0, 0, 255), 2, cv2.LINE_AA)
            cv2.line(frame, (draw_x - 10, draw_y + 10), (draw_x + 10, draw_y - 10), (0, 0, 255), 2, cv2.LINE_AA)

        status = "DETECTED" if not is_missing else "MISSING"
        if outside_arena:
            status = "OUTSIDE ARENA"
        status_color = (0, 255, 0) if not is_missing else (0, 0, 255)
        cv2.putText(
            frame,
            f"Frame: {frame_idx}/{total_frames} - {status}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            status_color,
            2,
            cv2.LINE_AA,
        )
        if circle_event:
            cv2.putText(
                frame,
                f"Event: {circle_event}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )
        if "in_inner_circle" in row.index and row.get("in_inner_circle", 0) == 1 and not is_missing:
            cv2.putText(
                frame,
                "IN INNER",
                (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )

        writer.write(frame)
        total_processed += 1

        if total_processed % 100 == 0:
            print(f"   Progress: {total_processed}/{total_frames} frames", end="\r")

    reader.stop()
    writer.close()

    detection_pct = 100 * detection_count / total_processed if total_processed > 0 else 0

    print(f"\n✅ Tracked video created: {output_video_path.name}")
    print(f"   Detected frames: {detection_count}/{total_processed} ({detection_pct:.1f}%)")
    try:
        import time
        time.sleep(0.5)
        print(f"   File size: {output_video_path.stat().st_size / (1024 * 1024):.1f} MB")
    except Exception as e:
        print(f"   File size: unknown ({e})")

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
