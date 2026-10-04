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
delegates game/Wine staging to run_shift_capture_wine.sh, then fail-closed
validates that the requested stage/resource snapshot classes and PPM files were
actually produced.
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
planner="$script_dir/phase641_external_sampler_capture_plan.py"
result_validator="$script_dir/phase642_external_sampler_capture_result.py"
launcher="$script_dir/run_shift_capture_wine.sh"

handoff=""
output="./shift-capture"
# Keep capture mode ahead of any forwarded `--` game-argument separator.
forward=(--mode capture)

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
      # Capture mode is already the first delegated option.  Consume the
      # caller's equivalent request so game arguments can never reorder it.
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
if [[ ! -f "$planner" || ! -f "$result_validator" || ! -f "$launcher" ]]; then
  echo "Phase 642 tools are incomplete under: $script_dir" >&2
  exit 2
fi
command -v python3 >/dev/null 2>&1 || {
  echo "python3 is required for Phase 641/642 capture validation" >&2
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
capture_jsonl="$output/shift_d3d9_capture.jsonl"
capture_result="$output/external_sampler_capture_result.json"
rm -rf "$texture_dir"
rm -f "$capture_result"
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

printf 'Phase 641 snapshot stages: %s\n' "$texture_stages"
printf 'Snapshot directory        : %s\n' "$texture_dir"
printf 'Delegating to             : %s\n' "$launcher"

# Do not exec: Phase 642 owns the post-capture input-class validation step.
set +e
bash "$launcher" "${forward[@]}"
launcher_status=$?
set -e
if ((launcher_status != 0)); then
  echo "SHIFT capture launcher failed with status $launcher_status" >&2
  exit "$launcher_status"
fi
if [[ ! -f "$capture_jsonl" ]]; then
  echo "Phase 642 capture JSONL not found after successful launcher: $capture_jsonl" >&2
  exit 2
fi

python3 "$result_validator" \
  "$handoff" \
  "$capture_jsonl" \
  --capture-root "$output" \
  --output "$capture_result"

printf 'Capture result preflight   : %s\n' "$capture_result"
