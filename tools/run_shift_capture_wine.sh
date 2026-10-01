#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash tools/run_shift_capture_wine.sh --game /path/to/SHIFT.exe \
    --proxy /path/to/d3d9.dll [--output DIR] \
    [--mode passthrough|diagnostic|capture] [--debug-output] \
    [--frame-start N] [--frame-end N] \
    [--screenshots] [--buffer-payloads] [--texture-payloads] \
    [--wine wine] [-- GAME_ARGS...]

The launcher temporarily installs the proxy beside SHIFT.exe. If a local
d3d9.dll already exists (for example DXVK), it is staged as
"d3d9.shift_backend.dll" so the proxy chainloads the same renderer backend.
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

game=""
proxy=""
output="./shift-capture"
mode="diagnostic"
wine_command="${WINE_COMMAND:-wine}"
debug_output=0
screenshots=0
frame_start=""
frame_end=""
buffer_payloads=0
texture_payloads=0
game_args=()

while (($#)); do
  case "$1" in
    --game) game="${2:?missing value for --game}"; shift 2 ;;
    --proxy) proxy="${2:?missing value for --proxy}"; shift 2 ;;
    --output) output="${2:?missing value for --output}"; shift 2 ;;
    --mode) mode="${2:?missing value for --mode}"; shift 2 ;;
    --wine) wine_command="${2:?missing value for --wine}"; shift 2 ;;
    --debug-output) debug_output=1; shift ;;
    --frame-start) frame_start="${2:?missing value for --frame-start}"; shift 2 ;;
    --frame-end) frame_end="${2:?missing value for --frame-end}"; shift 2 ;;
    --screenshots) screenshots=1; shift ;;
    --buffer-payloads) buffer_payloads=1; shift ;;
    --texture-payloads) texture_payloads=1; shift ;;
    --) shift; game_args=("$@"); break ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$game" || -z "$proxy" ]]; then
  usage >&2
  exit 2
fi

case "$mode" in
  passthrough|diagnostic|capture) ;;
  *) echo "invalid --mode: $mode" >&2; exit 2 ;;
esac

for bound in "$frame_start" "$frame_end"; do
  if [[ -n "$bound" && ! "$bound" =~ ^[0-9]+$ ]]; then
    echo "frame bounds must be non-negative integers" >&2
    exit 2
  fi
done
if [[ -n "$frame_start" && -n "$frame_end" ]] && ((frame_end < frame_start)); then
  echo "--frame-end must be >= --frame-start" >&2
  exit 2
fi

command -v "$wine_command" >/dev/null 2>&1 || {
  echo "Wine executable not found: $wine_command" >&2
  exit 2
}
command -v winepath >/dev/null 2>&1 || {
  echo "winepath is required to translate capture paths" >&2
  exit 2
}

game="$(realpath "$game")"
proxy="$(realpath "$proxy")"
output="$(realpath -m "$output")"

[[ -f "$game" ]] || { echo "game not found: $game" >&2; exit 2; }
[[ -f "$proxy" ]] || { echo "proxy not found: $proxy" >&2; exit 2; }
[[ "${proxy##*/}" == "d3d9.dll" ]] || {
  echo "proxy must be named d3d9.dll" >&2
  exit 2
}

game_dir="${game%/*}"
target_dll="$game_dir/d3d9.dll"
sidecar_dll="$game_dir/d3d9.shift_backend.dll"

if [[ "$proxy" == "$target_dll" ]]; then
  echo "--proxy must point to the built artifact, not the game's d3d9.dll" >&2
  exit 2
fi

mkdir -p "$output"
capture_path="$output/shift_d3d9_capture.jsonl"
crash_path="$output/shift_d3d9_crash.jsonl"
backup_dll="$output/original_d3d9.dll"
backup_sidecar="$output/original_d3d9.shift_backend.dll"
had_dll=0
had_sidecar=0
staged_backend=0

# Make every recovery copy before changing the game directory.
if [[ -f "$target_dll" ]]; then
  cp -f "$target_dll" "$backup_dll"
  had_dll=1
fi
if [[ -f "$sidecar_dll" ]]; then
  cp -f "$sidecar_dll" "$backup_sidecar"
  had_sidecar=1
fi

restore() {
  local rc=$?
  trap - EXIT INT TERM
  if ((had_dll)); then
    cp -f "$backup_dll" "$target_dll"
  else
    rm -f "$target_dll"
  fi
  if ((had_sidecar)); then
    cp -f "$backup_sidecar" "$sidecar_dll"
  else
    rm -f "$sidecar_dll"
  fi
  exit "$rc"
}
trap restore EXIT INT TERM

if ((had_sidecar)); then
  rm -f "$sidecar_dll"
fi

if ((had_dll)); then
  if [[ "$(sha256sum "$target_dll" | awk '{print $1}')" != \
        "$(sha256sum "$proxy" | awk '{print $1}')" ]]; then
    cp -f "$target_dll" "$sidecar_dll"
    staged_backend=1
  fi
fi

cp -f "$proxy" "$target_dll"

capture_windows="$(winepath -w "$capture_path")"
crash_windows="$(winepath -w "$crash_path")"
export SHIFT_D3D9_CAPTURE="$capture_windows"
export SHIFT_D3D9_CRASH_LOG="$crash_windows"
export SHIFT_D3D9_CRASH_DIAGNOSTICS=1
export SHIFT_D3D9_CAPTURE_MODE="$mode"
unset SHIFT_D3D9_BACKEND || true

if [[ -n "$frame_start" ]]; then
  export SHIFT_D3D9_CAPTURE_FRAME_START="$frame_start"
else
  unset SHIFT_D3D9_CAPTURE_FRAME_START || true
fi
if [[ -n "$frame_end" ]]; then
  export SHIFT_D3D9_CAPTURE_FRAME_END="$frame_end"
else
  unset SHIFT_D3D9_CAPTURE_FRAME_END || true
fi

if ((debug_output)); then
  export SHIFT_D3D9_CAPTURE_DEBUG_OUTPUT=1
else
  unset SHIFT_D3D9_CAPTURE_DEBUG_OUTPUT || true
fi

if ((screenshots)); then
  frame_dir="$output/frames"
  mkdir -p "$frame_dir"
  export SHIFT_D3D9_CAPTURE_SCREENSHOT=1
  export SHIFT_D3D9_CAPTURE_SCREENSHOT_EVERY=1
  export SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR="$(winepath -w "$frame_dir")"
fi

if ((buffer_payloads)); then
  buffer_dir="$output/buffers"
  mkdir -p "$buffer_dir"
  export SHIFT_D3D9_CAPTURE_BUFFER_PAYLOADS=1
  export SHIFT_D3D9_CAPTURE_BUFFER_PAYLOAD_DIR="$(winepath -w "$buffer_dir")"
else
  unset SHIFT_D3D9_CAPTURE_BUFFER_PAYLOADS || true
  unset SHIFT_D3D9_CAPTURE_BUFFER_PAYLOAD_DIR || true
fi

if ((texture_payloads)); then
  texture_payload_dir="$output/texture-payloads"
  mkdir -p "$texture_payload_dir"
  export SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOADS=1
  export SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOAD_DIR="$(winepath -w "$texture_payload_dir")"
else
  unset SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOADS || true
  unset SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOAD_DIR || true
fi

old_overrides="${WINEDLLOVERRIDES:-}"
filtered_overrides=""
if [[ -n "$old_overrides" ]]; then
  IFS=';' read -r -a override_parts <<< "$old_overrides"
  for entry in "${override_parts[@]}"; do
    [[ -n "$entry" ]] || continue
    name="${entry%%=*}"
    if [[ "${name,,}" == "d3d9" ]]; then
      continue
    fi
    if [[ -n "$filtered_overrides" ]]; then
      filtered_overrides+=";"
    fi
    filtered_overrides+="$entry"
  done
fi
if [[ -n "$filtered_overrides" ]]; then
  export WINEDLLOVERRIDES="$filtered_overrides;d3d9=n,b"
else
  export WINEDLLOVERRIDES="d3d9=n,b"
fi

echo "Launching: $game"
echo "Capture : $capture_path"
echo "Crash   : $crash_path"
echo "Mode    : $mode"
if [[ -n "$frame_start" || -n "$frame_end" ]]; then
  echo "Frames  : ${frame_start:-0}..${frame_end:-end}"
fi
if ((buffer_payloads)); then echo "Buffers : $buffer_dir"; fi
if ((texture_payloads)); then echo "Tex raw : $texture_payload_dir"; fi
if ((staged_backend)); then
  echo "Backend : preserved local d3d9.dll via $sidecar_dll"
else
  echo "Backend : Wine/system d3d9.dll"
fi

set +e
(
  cd "$game_dir"
  "$wine_command" "$game" "${game_args[@]}"
)
exit_code=$?
set -e

if ((exit_code != 0)); then
  echo "warning: game exited with code $exit_code; diagnostic prefix may still be useful" >&2
fi

if [[ ! -f "$capture_path" ]]; then
  echo "no runtime capture was produced: $capture_path" >&2
  exit 3
fi

python3 "$repo_root/native_capture/analyze_proxy_log.py" "$capture_path" 2>/dev/null || true
if [[ -s "$crash_path" ]]; then
  python3 "$repo_root/native_capture/analyze_proxy_crash.py" "$crash_path" 2>/dev/null || true
  echo "Crash context: $crash_path"
fi
echo "Capture completed: $capture_path"
exit "$exit_code"
