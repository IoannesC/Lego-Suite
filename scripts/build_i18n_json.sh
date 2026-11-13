#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

TARGET_DIR="$BASE_DIR/defaults/i18n"
OUTPUT_FILE="$BASE_DIR/src/i18n/languages.json"

if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Directory $TARGET_DIR not found."
    exit 1
fi

jq -n '
  reduce inputs as $i ( {}; . + { (input_filename | split("/") | last | split(".json")[0]): $i } )
' "$TARGET_DIR"/*.json > "$OUTPUT_FILE"
