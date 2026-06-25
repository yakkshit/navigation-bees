"""
Shared arena geometry for bumblebee tracking post-processing.

Physical arena (user-specified):
  - Inner circle: 42 cm diameter  (21 cm radius)
  - Outer circle: 84 cm diameter  (42 cm radius) — tracking arena boundary

TRex BORDER_DISTANCE (with cam_circle_mask) is distance from the bee centroid
to the outer arena edge in cm. See https://trex.run/docs/formats.html
"""

from __future__ import annotations

import json
import os
import cv2
import numpy as np
from pathlib import Path

# Physical dimensions (cm)
INNER_DIAMETER_CM = 74.0
OUTER_DIAMETER_CM = 132.0
INNER_RADIUS_CM = INNER_DIAMETER_CM / 2.0
OUTER_RADIUS_CM = OUTER_DIAMETER_CM / 2.0

# Pixel offset from image centre for arena centre (matches tracked-video overlay)
DEFAULT_CENTER_OFFSET_X_PX = 208
DEFAULT_CENTER_OFFSET_Y_PX = -7

CONFIG_PATH = Path(__file__).parent.parent / "circle_config.json"
CACHE_PATH = Path(__file__).parent.parent / "circle_config_cache.json"


def load_circle_config(video_name: str | None = None) -> dict:
    """Load optional overrides from circle_config.json, supporting video-specific overrides."""
    cfg = {
        "inner_diameter_cm": INNER_DIAMETER_CM,
        "outer_diameter_cm": OUTER_DIAMETER_CM,
        "center_offset_x_px": DEFAULT_CENTER_OFFSET_X_PX,
        "center_offset_y_px": DEFAULT_CENTER_OFFSET_Y_PX,
        "event_debounce_frames": 2,
        "visit_gap_frames": 8,
    }
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            raw_cfg = json.load(f)
            # Apply generic settings
            for k, v in raw_cfg.items():
                if k != "video_overrides":
                    cfg[k] = v
            # Apply video-specific overrides if a pattern matches the video name
            if video_name and "video_overrides" in raw_cfg:
                for pattern, overrides in raw_cfg["video_overrides"].items():
                    if pattern in video_name:
                        cfg.update(overrides)
                        break
    cfg["inner_radius_cm"] = cfg["inner_diameter_cm"] / 2.0
    cfg["outer_radius_cm"] = cfg["outer_diameter_cm"] / 2.0
    return cfg


def _cache_key(video_name: str) -> str:
    """Normalize cache key: strip directory and extension."""
    return Path(video_name).stem


def get_cached_center(video_name: str) -> tuple[int, int] | None:
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH) as f:
                cache = json.load(f)
                key = _cache_key(video_name)
                # Try stem key first, then full name for backward compat
                for k in [key, video_name, video_name + ".mp4", video_name + ".mkv"]:
                    if k in cache and cache[k] is not None:
                        return tuple(cache[k])
        except Exception:
            pass
    return None


def save_cached_center(video_name: str, center: tuple[int, int] | None) -> None:
    cache = {}
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH) as f:
                cache = json.load(f)
        except Exception:
            pass
    key = _cache_key(video_name)
    cache[key] = list(center) if center is not None else None
    # Also update old key format for backward compat
    if video_name in cache and video_name != key:
        cache[video_name] = cache[key]
    try:
        with open(CACHE_PATH, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass


def detect_arena_center(video_path: Path) -> tuple[int, int] | None:
    """Detect arena center using HoughCircles to find either the inner zone circle or reflective feeder."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    # Use a frame at 30% in — avoids dark startup frames
    frame_idx = max(0, min(int(total_frames * 0.30), total_frames - 1))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = cap.read()
    cap.release()
    if not ret:
        return None

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    cx_img, cy_img = width // 2, height // 2

    def _search(img, use_clahe=False):
        if use_clahe:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            img = clahe.apply(img)
        blurred = cv2.GaussianBlur(img, (7, 7), 2)
        for p2 in [30, 22, 15]:
            # 1. Try small circle (reflective feeder or inner zone dot)
            small = cv2.HoughCircles(
                blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=30,
                param1=50, param2=p2, minRadius=10, maxRadius=60
            )
            if small is not None:
                candidates = []
                for x, y, r in np.around(small[0]).astype(int):
                    dist = np.hypot(x - cx_img, y - cy_img)
                    if dist < 350:
                        candidates.append((dist, (x, y)))
                if candidates:
                    candidates.sort()
                    return int(candidates[0][1][0]), int(candidates[0][1][1])
            # 2. Try large circle (inner zone boundary)
            large = cv2.HoughCircles(
                blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=100,
                param1=50, param2=p2, minRadius=100, maxRadius=350
            )
            if large is not None:
                candidates = []
                for x, y, r in np.around(large[0]).astype(int):
                    dist = np.hypot(x - cx_img, y - cy_img)
                    if dist < 350:
                        candidates.append((dist, (x, y)))
                if candidates:
                    candidates.sort()
                    return int(candidates[0][1][0]), int(candidates[0][1][1])
        return None

    result = _search(gray, use_clahe=False)
    if result is None:
        result = _search(gray, use_clahe=True)
    return result



def find_source_video(video_dir: Path, settings_path: Path, input_video_dir: Path | None = None) -> Path:
    """Resolve the exact source video for a TRex output folder."""
    if input_video_dir is None:
        input_video_dir = Path(os.getenv("INPUT_VIDEO_DIR", os.getenv("INPUT_DIR", "/Users/yakkshit/Downloads/project/hiwi2/p1/Videos/BBP2025")))

    # Read meta_source_path from settings
    source_video = None
    if settings_path.exists():
        with open(settings_path) as f:
            for line in f:
                line = line.strip()
                if not line or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                if key.strip() == "meta_source_path":
                    source_video = Path(val.strip().strip('"'))
                    break

    if source_video:
        if source_video.exists():
            return source_video
        
        local_path = input_video_dir / source_video.name
        if local_path.exists():
            return local_path
        
        local_path_space = input_video_dir / source_video.name.replace("_", " ")
        if local_path_space.exists():
            return local_path_space
            
        local_path_under = input_video_dir / source_video.name.replace(" ", "_")
        if local_path_under.exists():
            return local_path_under

    video_name = video_dir.name
    exact = input_video_dir / f"{video_name}.mp4"
    if exact.exists():
        return exact

    matches = sorted(input_video_dir.glob(f"{video_name}.*"))
    for candidate in matches:
        if candidate.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"}:
            return candidate

    import re
    dt_match = re.search(r"(\d{4}-\d{2}-\d{2})[_\s](\d{2}-\d{2}-\d{2})", video_name)
    if dt_match:
        date_str, time_str = dt_match.groups()
        for f in input_video_dir.iterdir():
            if f.is_file() and f.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"}:
                if date_str in f.name and (time_str in f.name or time_str.replace("-", " ") in f.name):
                    return f

    raise FileNotFoundError(f"No source video found for '{video_name}' in {input_video_dir}")


def arena_center_px(width: int, height: int, cfg: dict | None = None, cm_per_pixel: float | None = None, video_name: str | None = None, video_path: Path | None = None) -> tuple[int, int]:
    cfg = cfg or load_circle_config()
    
    # 1. Try to load from cache
    if video_name:
        cached = get_cached_center(video_name)
        if cached:
            return cached

    # 2. Try to detect dynamically if video_path is provided
    if video_path and video_path.exists():
        detected = detect_arena_center(video_path)
        if detected:
            # Sanity check: detected center must be within 450px of image center
            max_dist = max(width, height) * 0.45
            dist_from_center = ((detected[0] - width // 2) ** 2 + (detected[1] - height // 2) ** 2) ** 0.5
            if dist_from_center <= max_dist:
                save_cached_center(video_path.name, detected)
                return detected

    # Dynamically select offsets based on the calibration factor (zoom level)
    if cm_per_pixel is not None:
        # Zoom-out setup (cm_per_pixel ~ 0.1546)
        if abs(cm_per_pixel - 0.1546) < 0.02:
            cx = int(width // 2 + 208)
            cy = int(height // 2 - 7)
            return cx, cy
        # Zoom-in setup (cm_per_pixel ~ 0.0773)
        elif abs(cm_per_pixel - 0.0773) < 0.02:
            cx = int(width // 2 - 25)
            cy = int(height // 2 + 3)
            return cx, cy

    cx = int(width // 2 + cfg.get("center_offset_x_px", DEFAULT_CENTER_OFFSET_X_PX))
    cy = int(height // 2 + cfg.get("center_offset_y_px", DEFAULT_CENTER_OFFSET_Y_PX))
    return cx, cy


def arena_center_cm(width: int, height: int, cm_per_pixel: float, cfg: dict | None = None, video_dir: Path | None = None) -> tuple[float, float]:
    video_name = video_dir.name if video_dir else None
    video_path = None
    if video_dir:
        # Resolve source video to detect center dynamically
        settings_path = video_dir / f"{video_dir.name}.settings"
        try:
            video_path = find_source_video(video_dir, settings_path)
        except Exception:
            pass

    cx_px, cy_px = arena_center_px(width, height, cfg, cm_per_pixel, video_name=video_name, video_path=video_path)
    return cx_px * cm_per_pixel, cy_px * cm_per_pixel


def radius_px(radius_cm: float, cm_per_pixel: float) -> int:
    return max(1, int(round(radius_cm / cm_per_pixel)))


def find_column(columns: list[str], *candidates: str) -> str | None:
    """Return first matching column name (exact or prefix)."""
    for cand in candidates:
        for col in columns:
            if col == cand or col.startswith(cand):
                return col
    return None


def dist_to_center_from_border(border_distance_cm: float, outer_radius_cm: float) -> float:
    """TRex BORDER_DISTANCE → radial distance from arena centre (cm)."""
    return outer_radius_cm - border_distance_cm


def dist_to_center_euclidean(x_cm: float, y_cm: float, cx_cm: float, cy_cm: float) -> float:
    import math

    return math.hypot(x_cm - cx_cm, y_cm - cy_cm)

