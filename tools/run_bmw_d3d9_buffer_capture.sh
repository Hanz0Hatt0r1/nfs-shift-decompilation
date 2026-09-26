#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat >&2 <<EOF
Usage:
  $0 [--wine WINE] [--prefix WINEPREFIX] [--output-dir DIR] -- GAME_EXE [GAME_ARGS...]

Environment overrides:
  SHIFT_D3D9_CAPTURE_FLUSH
  SHIFT_D3D9_CAPTURE_SCREENSHOT
  SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT
EOF
}

WINE_BIN="${WINE_BIN:-wine}"
WINEPREFIX_ARG=""
OUTPUT_DIR=""
GAME_EXE=""
GAME_ARGS=()

while (($#)); do
    case "$1" in
        --wine)
            [[ $# -ge 2 ]] || { usage; exit 2; }
            WINE_BIN="$2"
            shift 2
            ;;
        --prefix)
            [[ $# -ge 2 ]] || { usage; exit 2; }
            WINEPREFIX_ARG="$2"
            shift 2
            ;;
        --output-dir)
            [[ $# -ge 2 ]] || { usage; exit 2; }
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --)
            shift
            [[ $# -ge 1 ]] || { usage; exit 2; }
            GAME_EXE="$1"
            shift
            GAME_ARGS=("$@")
            break
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "unknown option: $1" >&2
            usage
            exit 2
            ;;
    esac
done

[[ -n "$GAME_EXE" ]] || { usage; exit 2; }

if [[ -z "$OUTPUT_DIR" ]]; then
    OUTPUT_DIR="$(pwd)/bmw-buffer-capture"
fi
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"
PAYLOAD_DIR="$OUTPUT_DIR/buffer_payloads"
mkdir -p "$PAYLOAD_DIR"

export WINEDLLOVERRIDES="d3d9=n${WINEDLLOVERRIDES:+;$WINEDLLOVERRIDES}"
if [[ -n "$WINEPREFIX_ARG" ]]; then
    export WINEPREFIX="$WINEPREFIX_ARG"
fi

export SHIFT_D3D9_CAPTURE="$OUTPUT_DIR/shift_d3d9_capture.jsonl"
export SHIFT_D3D9_CAPTURE_BUFFER_PAYLOADS=1
export SHIFT_D3D9_CAPTURE_BUFFER_PAYLOAD_DIR="$PAYLOAD_DIR"
export SHIFT_D3D9_CAPTURE_FLUSH="${SHIFT_D3D9_CAPTURE_FLUSH:-1}"
export SHIFT_D3D9_CAPTURE_SCREENSHOT="${SHIFT_D3D9_CAPTURE_SCREENSHOT:-0}"
export SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT="${SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT:-0}"
export SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOADS="${SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOADS:-0}"

echo "capture: $SHIFT_D3D9_CAPTURE" >&2
echo "buffer payloads: $SHIFT_D3D9_CAPTURE_BUFFER_PAYLOAD_DIR" >&2
echo "wine: $WINE_BIN" >&2
echo "game: $GAME_EXE" >&2

exec "$WINE_BIN" "$GAME_EXE" "${GAME_ARGS[@]}"
