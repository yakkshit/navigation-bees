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

printf '%s\n' "TREX batch run started: $(date)" > "$LOG_FILE"
printf '%s\n' "Input:    $INPUT_DIR" | tee -a "$LOG_FILE"
printf '%s\n' "Output:   $OUTPUT_DIR" | tee -a "$LOG_FILE"
printf '%s\n' "Settings: $SETTINGS_FILE" | tee -a "$LOG_FILE"
printf '%s\n' "TREX_CMD: $TREX_CMD" | tee -a "$LOG_FILE"
printf '%s\n' "PYTHON_CMD: ${PYTHON_CMD:-not found}" | tee -a "$LOG_FILE"
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

count=0
success=0
failed=0
for video in "${videos[@]}"; do
  count=$((count + 1))
  name="$(basename "$video")"
  name_no_ext="${name%.*}"
  video_out="$OUTPUT_DIR/$name_no_ext"

  echo "[$count/${#videos[@]}] $name"
  echo "  → output: $video_out"

  rm -rf "$video_out"
  mkdir -p "$video_out"

  trex_args=(
    -i "$video"
    -s "$SETTINGS_FILE"
    -output_dir "$video_out"
    -detect_type background_subtraction
    -track_background_subtraction true
    -auto_quit true
    -nowindow true
  )
  if [ -f "$MASK_FILE" ]; then
    trex_args+=(-mask_path "$MASK_FILE")
  fi

  "$TREX_CMD" "${trex_args[@]}" > "$video_out/trex.log" 2>&1

  if [ $? -eq 0 ]; then
    echo "  ✓ done"
    success=$((success + 1))
    echo "OK   | $name" >> "$LOG_FILE"

    if [ -n "$PYTHON_CMD" ] && [ -x "$PYTHON_CMD" ] && [ -f "$SCRIPT_DIR/generate_tracked_video.py" ]; then
      echo "  → generating tracked MP4"
      if "$PYTHON_CMD" "$SCRIPT_DIR/generate_tracked_video.py" "$name_no_ext" > "$video_out/generate_tracked.log" 2>&1; then
        echo "  ✓ tracked MP4 created"
        echo "TRACKED | $name" >> "$LOG_FILE"
      else
        echo "  ✗ MP4 generation failed (see $video_out/generate_tracked.log)"
        echo "TRACK_FAIL | $name" >> "$LOG_FILE"
      fi
    else
      echo "  ⚠ skipping tracked MP4 generation"
    fi
  else
    echo "  ✗ failed (see $video_out/trex.log)"
    failed=$((failed + 1))
    echo "FAIL | $name" >> "$LOG_FILE"
  fi
  echo ""
done

printf "========================================\n" | tee -a "$LOG_FILE"
printf "Batch complete: %s\n" "$(date)" | tee -a "$LOG_FILE"
printf "Total:   %d\n" "$((success + failed))" | tee -a "$LOG_FILE"
printf "Success: %d\n" "$success" | tee -a "$LOG_FILE"
printf "Failed:  %d\n" "$failed" | tee -a "$LOG_FILE"
printf "Output:  %s\n" "$OUTPUT_DIR" | tee -a "$LOG_FILE"
printf "========================================\n" | tee -a "$LOG_FILE"
