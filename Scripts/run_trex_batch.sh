#!/bin/bash
# ============================================================
# TRex Batch Processor — single bumblebee tracking
# Uses a clean settings file, plus passes detect_type explicitly
# so background subtraction is guaranteed during conversion.
# ============================================================

# ---------------- CONFIGURATION ----------------
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

INPUT_DIR="${INPUT_DIR:-/Users/fundayildiz/Desktop/videos}"
OUTPUT_DIR="${OUTPUT_DIR:-/Users/fundayildiz/Desktop/bee_results}"
SETTINGS_FILE="${SETTINGS_FILE:-/Users/fundayildiz/Desktop/first.settings}"
# -----------------------------------------------

# Activate conda environment
if [ -f "/opt/miniconda3/etc/profile.d/conda.sh" ]; then
  source "/opt/miniconda3/etc/profile.d/conda.sh"
else
  echo "ERROR: conda.sh not found at /opt/miniconda3/etc/profile.d/conda.sh"
  exit 1
fi

CONDA_ENV="tracking"
if conda info --envs | awk '/^track[[:space:]]/ {print $1; exit}' | grep -q .; then
  CONDA_ENV="$(conda info --envs | awk '/^track[[:space:]]/ {print $1; exit}')"
elif conda info --envs | awk '/^tracking[[:space:]]/ {print $1; exit}' | grep -q .; then
  CONDA_ENV="$(conda info --envs | awk '/^tracking[[:space:]]/ {print $1; exit}')"
fi

echo "Activating conda env: $CONDA_ENV"
conda activate "$CONDA_ENV" >/dev/null 2>&1 || true

# Use the direct executable path to avoid wrapper script issues with spaces in filenames
TREX_CMD="/opt/miniconda3/envs/$CONDA_ENV/bin/TRex.app/Contents/MacOS/TRex"
if [ ! -x "$TREX_CMD" ]; then
  if [ -x "/opt/miniconda3/envs/track/bin/TRex.app/Contents/MacOS/TRex" ]; then
    TREX_CMD="/opt/miniconda3/envs/track/bin/TRex.app/Contents/MacOS/TRex"
  fi
fi

if [ ! -x "$TREX_CMD" ]; then
  echo "ERROR: TRex executable not found: $TREX_CMD"
  exit 1
fi

# Sanity checks
if [ ! -d "$INPUT_DIR" ]; then
  echo "ERROR: Input folder not found: $INPUT_DIR"
  exit 1
fi
if [ ! -f "$SETTINGS_FILE" ]; then
  echo "ERROR: Settings file not found: $SETTINGS_FILE"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

LOG_FILE="$OUTPUT_DIR/batch_log.txt"
echo "TRex batch run started: $(date)" > "$LOG_FILE"
echo "Input:    $INPUT_DIR"  | tee -a "$LOG_FILE"
echo "Output:   $OUTPUT_DIR" | tee -a "$LOG_FILE"
echo "Settings: $SETTINGS_FILE" | tee -a "$LOG_FILE"
echo "----------------------------------------" | tee -a "$LOG_FILE"

shopt -s nullglob
videos=( "$INPUT_DIR"/*.mp4 "$INPUT_DIR"/*.mov "$INPUT_DIR"/*.MP4 "$INPUT_DIR"/*.MOV )
total=${#videos[@]}

if [ $total -eq 0 ]; then
  echo "No videos found in $INPUT_DIR"
  exit 1
fi

echo "Found $total video(s) to process" | tee -a "$LOG_FILE"
echo ""

count=0
success=0
failed=0
for video in "${videos[@]}"; do
  count=$((count+1))
  name=$(basename "$video")
  name_no_ext="${name%.*}"
  video_out="$OUTPUT_DIR/$name_no_ext"

  echo "[$count/$total] $name"
  echo "  → output: $video_out"

  # Clean any stale results so TRex re-converts with the correct settings
  rm -rf "$video_out"
  mkdir -p "$video_out"

  # Run TRex: settings file for all parameters, plus detect_type
  # passed explicitly as a safety net (guarantees background subtraction).
  "$TREX_CMD" -i "$video" \
       -s "$SETTINGS_FILE" \
       -output_dir "$video_out" \
       -detect_type background_subtraction \
       -track_background_subtraction true \
       -auto_quit true \
       -nowindow true \
       > "$video_out/trex.log" 2>&1

  if [ $? -eq 0 ]; then
    echo "  ✓ done"
    success=$((success+1))
    echo "OK   | $name" >> "$LOG_FILE"
  else
    echo "  ✗ failed (see $video_out/trex.log)"
    failed=$((failed+1))
    echo "FAIL | $name" >> "$LOG_FILE"
  fi
  echo ""
done

echo "========================================" | tee -a "$LOG_FILE"
echo "Batch complete: $(date)"   | tee -a "$LOG_FILE"
echo "Total:   $total"            | tee -a "$LOG_FILE"
echo "Success: $success"          | tee -a "$LOG_FILE"
echo "Failed:  $failed"           | tee -a "$LOG_FILE"
echo "Output:  $OUTPUT_DIR"       | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
