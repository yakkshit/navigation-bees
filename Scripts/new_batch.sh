#!/bin/bash
# ============================================================
# TREX Batch Tracking Script
# Uses TREX to process all videos in INPUT_DIR and save results
# in OUTPUT_DIR using the settings file specified in .env or defaults.
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env.local"
if [ ! -f "$ENV_FILE" ]; then
  ENV_FILE="$SCRIPT_DIR/../.env"
fi

if [ -f "$ENV_FILE" ]; then
  echo "Loading configuration from $ENV_FILE"
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
else
  echo "WARNING: No .env.local or .env found; using default paths"
fi

INPUT_DIR="${INPUT_DIR:-$SCRIPT_DIR/../../Videos}"
OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPT_DIR/../../V_OUTPUTS}"
SETTINGS_FILE="${SETTINGS_FILE:-$SCRIPT_DIR/working.settings}"
MASK_FILE="${MASK_FILE:-$SCRIPT_DIR/../Data/arena_center_mask.mp4}"
TREX_CMD="${TREX_CMD:-}"
PYTHON_CMD="${PYTHON_CMD:-}"
CONDA_ENV="${CONDA_ENV:-track}"
# Max parallel Python jobs (post-process + video generation)
N_PARALLEL="${N_PARALLEL:-4}"
# Set FORCE=1 to reprocess already-completed videos
FORCE="${FORCE:-0}"

# Activate conda environment (required for TRex Python backend)
if [ -f "/opt/miniconda3/etc/profile.d/conda.sh" ]; then
  # shellcheck source=/dev/null
  source "/opt/miniconda3/etc/profile.d/conda.sh"
  conda activate "$CONDA_ENV" >/dev/null 2>&1 || true
elif command -v conda >/dev/null 2>&1; then
  CONDA_BASE="$(conda info --base 2>/dev/null || true)"
  if [ -n "$CONDA_BASE" ] && [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
    # shellcheck source=/dev/null
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    conda activate "$CONDA_ENV" >/dev/null 2>&1 || true
  fi
fi

if [ -z "$TREX_CMD" ]; then
  if command -v TREX >/dev/null 2>&1; then
    TREX_CMD=$(command -v TREX)
  elif command -v trex >/dev/null 2>&1; then
    TREX_CMD=$(command -v trex)
  elif [ -x "/opt/miniconda3/envs/$CONDA_ENV/bin/TREx.app/Contents/MacOS/TRex" ]; then
    TREX_CMD="/opt/miniconda3/envs/$CONDA_ENV/bin/TREx.app/Contents/MacOS/TRex"
  elif [ -x "/opt/miniconda3/envs/$CONDA_ENV/bin/trex" ]; then
    TREX_CMD="/opt/miniconda3/envs/$CONDA_ENV/bin/trex"
  fi
fi

if [ -z "$PYTHON_CMD" ]; then
  if [ -x "$SCRIPT_DIR/../.venv/bin/python" ]; then
    PYTHON_CMD="$SCRIPT_DIR/../.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD=$(command -v python3)
  elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD=$(command -v python)
  fi
fi

if [ -z "$TREX_CMD" ] || [ ! -x "$TREX_CMD" ]; then
  echo "ERROR: TREX executable not found."
  echo "Set TREX_CMD in .env.local or install TREX and ensure it is on PATH."
  exit 1
fi

if [ ! -d "$INPUT_DIR" ]; then
  echo "ERROR: Input directory not found: $INPUT_DIR"
  exit 1
fi
if [ ! -f "$SETTINGS_FILE" ]; then
  echo "ERROR: Settings file not found: $SETTINGS_FILE"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
LOG_FILE="$OUTPUT_DIR/batch_log.txt"

# Default parallel jobs for full pipeline to 2 to prevent overloading CPU/memory
N_PARALLEL="${N_PARALLEL:-2}"

printf '%s\n' "TREX batch run started: $(date)" > "$LOG_FILE"
printf '%s\n' "Input:    $INPUT_DIR" | tee -a "$LOG_FILE"
printf '%s\n' "Output:   $OUTPUT_DIR" | tee -a "$LOG_FILE"
printf '%s\n' "Settings: $SETTINGS_FILE" | tee -a "$LOG_FILE"
printf '%s\n' "TREX_CMD: $TREX_CMD" | tee -a "$LOG_FILE"
printf '%s\n' "PYTHON_CMD: ${PYTHON_CMD:-not found}" | tee -a "$LOG_FILE"
printf '%s\n' "N_PARALLEL: $N_PARALLEL (concurrent video pipelines)" | tee -a "$LOG_FILE"
printf '%s\n' "FORCE: $FORCE (reprocess existing: $([ "$FORCE" = "1" ] && echo yes || echo no))" | tee -a "$LOG_FILE"
printf '%s\n' "----------------------------------------" | tee -a "$LOG_FILE"

shopt -s nullglob
videos=("$INPUT_DIR"/*.mp4 "$INPUT_DIR"/*.mov "$INPUT_DIR"/*.MP4 "$INPUT_DIR"/*.MOV)
shopt -u nullglob

if [ ${#videos[@]} -eq 0 ]; then
  echo "No videos found in $INPUT_DIR"
  exit 1
fi

echo "Found ${#videos[@]} video(s) to process" | tee -a "$LOG_FILE"
echo ""

# Function to run the full pipeline for a single video
run_full_pipeline() {
  local video="$1"
  local name="$2"
  local name_no_ext="$3"
  local video_out="$4"
  local settings_file="$5"
  local mask_file="$6"
  local trex_cmd="$7"
  local python_cmd="$8"
  local script_dir="$9"

  local video_start
  video_start=$(date +%s)

  # Check duration and trim to 10 minutes (600s) if longer
  local duration
  duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$video" 2>/dev/null || echo "0")
  local duration_int
  duration_int=${duration%.*}

  if [ -n "$duration_int" ] && [ "$duration_int" -gt 600 ]; then
    echo "  → Video $name is ${duration_int}s (>10m), trimming in-place to 10 minutes..."
    local temp_video="${video%.*}_temp.${video##*.}"
    if ffmpeg -y -i "$video" -t 600 -c copy "$temp_video" >/dev/null 2>&1; then
      mv "$temp_video" "$video"
      echo "  ✓ Video $name trimmed in-place successfully."
    else
      rm -f "$temp_video"
      echo "  ✗ Failed to trim $name in-place, using original video."
    fi
  fi

  rm -rf "$video_out"
  mkdir -p "$video_out"

  local trex_args=(
    -i "$video"
    -s "$settings_file"
    -output_dir "$video_out"
    -detect_type background_subtraction
    -track_background_subtraction true
    -auto_quit true
    -nowindow true
  )
  if [ -f "$mask_file" ]; then
    trex_args+=(-mask_path "$mask_file")
  fi

  # Run TRex (gracefully catching failure status to not trigger set -e in main shell)
  if "$trex_cmd" "${trex_args[@]}" > "$video_out/trex.log" 2>&1; then
    local video_end
    video_end=$(date +%s)
    local trex_secs=$((video_end - video_start))
    echo "  ✓ TRex done: $name (${trex_secs}s)"

    # Run Python post-processing and video generation
    if [ -n "$python_cmd" ] && [ -x "$python_cmd" ]; then
      local py_start
      py_start=$(date +%s)
      local has_post=0
      local has_gen=0

      if [ -f "$script_dir/post_process_tracking.py" ]; then
        if "$python_cmd" "$script_dir/post_process_tracking.py" "$name_no_ext" > "$video_out/post_process.log" 2>&1; then
          has_post=1
        else
          echo "  ✗ Python post-processing failed: $name (see $video_out/post_process.log)"
        fi
      else
        has_post=1 # If post_process script doesn't exist, ignore
      fi

      if [ -f "$script_dir/generate_tracked_video.py" ]; then
        if "$python_cmd" "$script_dir/generate_tracked_video.py" "$name_no_ext" > "$video_out/generate_tracked.log" 2>&1; then
          has_gen=1
        else
          echo "  ✗ Python video generation failed: $name (see $video_out/generate_tracked.log)"
        fi
      else
        has_gen=1 # If video gen script doesn't exist, ignore
      fi

      local py_end
      py_end=$(date +%s)
      local py_secs=$((py_end - py_start))

      if [ "$has_post" -eq 1 ] && [ "$has_gen" -eq 1 ]; then
        echo "  ✓ Post-process + video done: $name (${py_secs}s)"
        echo "OK" > "$video_out/status"
        return 0
      else
        echo "FAIL" > "$video_out/status"
        return 1
      fi
    else
      echo "OK" > "$video_out/status"
      return 0
    fi
  else
    echo "  ✗ TRex failed: $name (see $video_out/trex.log)"
    echo "FAIL" > "$video_out/status"
    return 1
  fi
}

count=0
skipped=0
start_time=$(date +%s)

for video in "${videos[@]}"; do
  count=$((count + 1))
  name="$(basename "$video")"
  name_no_ext="${name%.*}"
  video_out="$OUTPUT_DIR/$name_no_ext"

  # Skip if already done and FORCE=0
  if [ "$FORCE" != "1" ] && [ -f "$video_out/${name_no_ext}_tracked.mp4" ]; then
    echo "[$count/${#videos[@]}] SKIP (already done): $name"
    skipped=$((skipped + 1))
    continue
  fi

  echo "[$count/${#videos[@]}] START: $name"
  run_full_pipeline "$video" "$name" "$name_no_ext" "$video_out" "$SETTINGS_FILE" "$MASK_FILE" "$TREX_CMD" "${PYTHON_CMD:-}" "$SCRIPT_DIR" || true
done

# Gather statistics from status files in output directories
success=0
failed=0

for video in "${videos[@]}"; do
  name="$(basename "$video")"
  name_no_ext="${name%.*}"
  video_out="$OUTPUT_DIR/$name_no_ext"

  if [ -f "$video_out/status" ]; then
    status_val=$(cat "$video_out/status")
    if [ "$status_val" = "OK" ]; then
      success=$((success + 1))
      echo "OK   | $name" >> "$LOG_FILE"
    else
      failed=$((failed + 1))
      echo "FAIL | $name" >> "$LOG_FILE"
    fi
  elif [ -f "$video_out/${name_no_ext}_tracked.mp4" ]; then
    # Already existed and was skipped
    success=$((success + 1))
  else
    failed=$((failed + 1))
    echo "FAIL | $name (no status file)" >> "$LOG_FILE"
  fi
done

end_time=$(date +%s)
total_secs=$((end_time - start_time))

printf "========================================\n" | tee -a "$LOG_FILE"
printf "Batch complete: %s\n" "$(date)" | tee -a "$LOG_FILE"
printf "Total time:  %dm %ds\n" "$((total_secs/60))" "$((total_secs%60))" | tee -a "$LOG_FILE"
printf "Total:   %d\n" "$((success + failed))" | tee -a "$LOG_FILE"
printf "Success: %d\n" "$success" | tee -a "$LOG_FILE"
printf "Failed:  %d\n" "$failed" | tee -a "$LOG_FILE"
printf "Skipped: %d (already done)\n" "$skipped" | tee -a "$LOG_FILE"
printf "Output:  %s\n" "$OUTPUT_DIR" | tee -a "$LOG_FILE"
printf "========================================\n" | tee -a "$LOG_FILE"
printf "===============\n" | tee -a "$LOG_FILE"
