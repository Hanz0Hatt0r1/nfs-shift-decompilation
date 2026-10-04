#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash tools/run_phase641_snapshot_capture_wine.sh \
    --handoff out/.../renderer_native_scene_handoff.json \
    --game /path/to/SHIFT.exe --proxy /path/to/d3d9.dll \
    [--output DIR] [run_shift_capture_wine.sh options...]

Consumes the exact Phase 641 runtime_evidence_required frontier, enables D3D9
texture snapshots only for the requested sampler stages, forces capture mode,
and delegates all game/Wine staging to run_shift_capture_wine.sh.
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
planner="$script_dir/phase641_external_sampler_capture_plan.py"
launcher="$script_dir/run_shift_capture_wine.sh"

handoff=""
output="./shift-capture"
mode_seen=0
forward=()

while (($#)); do
  case "$1" in
    --handoff)
      handoff="${2:?missing value for --handoff}"
      shift 2
      ;;
    --output)
      output="${2:?missing value for --output}"
      forward+=("$1" "$2")
      shift 2
      ;;
    --mode)
      requested_mode="${2:?missing value for --mode}"
      if [[ "$requested_mode" != "capture" ]]; then
        echo "Phase 641 snapshot capture requires --mode capture" >&2
        exit 2
      fi
      mode_seen=1
      forward+=("$1" "$2")
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      forward+=("$@")
      break
      ;;
    *)
      forward+=("$1")
      shift
      ;;
  esac
done

if [[ -z "$handoff" ]]; then
  echo "--handoff is required" >&2
  usage >&2
  exit 2
fi
if [[ ! -f "$handoff" ]]; then
  echo "Phase 641 handoff not found: $handoff" >&2
  exit 2
fi
if [[ ! -f "$planner" || ! -f "$launcher" ]]; then
  echo "Phase 642 tools are incomplete under: $script_dir" >&2
  exit 2
fi
command -v python3 >/dev/null 2>&1 || {
  echo "python3 is required for Phase 641 capture planning" >&2
  exit 2
}

texture_stages="$(python3 "$planner" "$handoff" --print-stages)"
if [[ -z "$texture_stages" ]]; then
  echo "Phase 641 capture plan did not produce any texture stages" >&2
  exit 2
fi
if [[ ! "$texture_stages" =~ ^([0-9]|1[0-5])(,([0-9]|1[0-5]))*$ ]]; then
  echo "invalid Phase 641 texture stage list: $texture_stages" >&2
  exit 2
fi

output="$(realpath -m "$output")"
texture_dir="$output/textures"
rm -rf "$texture_dir"
mkdir -p "$texture_dir"

snapshot_dir_windows="$(python3 - "$texture_dir" <<'PY'
import os
import sys
path = os.path.abspath(sys.argv[1])
print("Z:" + path.replace("/", "\\"))
PY
)"

export SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT=1
export SHIFT_D3D9_CAPTURE_TEXTURE_STAGES="$texture_stages"
export SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT_DIR="$snapshot_dir_windows"

if (( ! mode_seen )); then
  forward+=(--mode capture)
fi

printf 'Phase 641 snapshot stages: %s\n' "$texture_stages"
printf 'Snapshot directory        : %s\n' "$texture_dir"
printf 'Delegating to             : %s\n' "$launcher"

exec bash "$launcher" "${forward[@]}"
