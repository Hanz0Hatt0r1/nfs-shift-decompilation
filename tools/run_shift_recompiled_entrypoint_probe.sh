#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 6 ]]; then
  printf 'usage: %s RUNTIME ARTIFACT_ROOT BUILD_ROOT PE_IMAGE GAME_DATA_ROOT LOG\n' "$0" >&2
  exit 2
fi

timeout_seconds=${SHIFT_ENTRYPOINT_TIMEOUT_SECONDS:-180}
if [[ ! "$timeout_seconds" =~ ^[1-9][0-9]*$ ]]; then
  printf 'SHIFT_ENTRYPOINT_TIMEOUT_SECONDS must be a positive integer\n' >&2
  exit 2
fi
probe_frames=${SHIFT_ENTRYPOINT_PROBE_FRAMES:-120}
if [[ ! "$probe_frames" =~ ^[1-9][0-9]*$ ]]; then
  printf 'SHIFT_ENTRYPOINT_PROBE_FRAMES must be a positive integer\n' >&2
  exit 2
fi
validation=${SHIFT_ENTRYPOINT_PROBE_VALIDATION:-0}
if [[ "$validation" != 0 && "$validation" != 1 ]]; then
  printf 'SHIFT_ENTRYPOINT_PROBE_VALIDATION must be 0 or 1\n' >&2
  exit 2
fi

runtime=$1
artifact_root=$2
build_root=$3
pe_image=$4
game_data_root=$5
log_path=$6

log_directory=$(dirname -- "$log_path")
mkdir -p "$log_directory"
log_path="$(cd "$log_directory" && pwd)/$(basename -- "$log_path")"
pcode_module=${SHIFT_ENTRYPOINT_PROBE_PCODE_MODULE:-"$artifact_root/libnfs_shift_pcode_startup_20261018.so"}
if [[ ! -r "$pcode_module" ]]; then
  printf 'probe P-code module is not readable: %s\n' "$pcode_module" >&2
  exit 2
fi
pcode_module=$(realpath -- "$pcode_module")

cd "$game_data_root"

mesh_source=${SHIFT_ENTRYPOINT_PROBE_MESH:-}
if [[ -z "$mesh_source" ]]; then
  printf 'set SHIFT_ENTRYPOINT_PROBE_MESH to a valid MGEO file or invoke tools/retail_frontier.py run\n' >&2
  exit 2
fi
if [[ ! -r "$mesh_source" ]]; then
  printf 'probe mesh is not readable: %s\n' "$mesh_source" >&2
  exit 2
fi
probe_args=(
  --mesh "$mesh_source"
  --shader-dir "$build_root/shaders"
  --recompiled-module "$pcode_module"
  --recompiled-override "$build_root/libnfs_shift_pcode_frontier.so"
  --recompiled-override "$artifact_root/computed-tail-dispatch-0065d140-pcode-20261018/libnfs_shift_pcode_supplement.so"
  --recompiled-supplement "$artifact_root/constructor-array-pcode-20261018-v11/libnfs_shift_pcode_supplement.so"
  --recompiled-supplement "$artifact_root/function-0040ce30-pcode-20261018/libnfs_shift_pcode_supplement.so"
  --recompiled-supplement "$artifact_root/function-005f1a20-pcode-20261018/libnfs_shift_pcode_supplement.so"
  --recompiled-supplement "$artifact_root/function-00632c90-pcode-20261018/libnfs_shift_pcode_supplement.so"
  --recompiled-supplement "$artifact_root/function-00632cc4-pcode-20261018/libnfs_shift_pcode_supplement.so"
  --recompiled-supplement "$artifact_root/function-006408e2-pcode-20261018/libnfs_shift_pcode_supplement.so"
  --recompiled-supplement "$artifact_root/function-006476e0-pcode-20261018/libnfs_shift_pcode_supplement.so"
  --recompiled-supplement "$artifact_root/function-006a8e30-pcode-20261018/libnfs_shift_pcode_supplement.so"
  --recompiled-supplement "$artifact_root/function-0082db30-pcode-20261018/libnfs_shift_pcode_supplement.so"
  --recompiled-supplement "$artifact_root/function-008328b0-008328c0-008328d0-pcode-20261018/libnfs_shift_pcode_supplement.so"
  --recompiled-supplement "$artifact_root/function-008328e0-pcode-20261018/libnfs_shift_pcode_supplement.so"
  --recompiled-supplement "$artifact_root/function-00886b80-pcode-20261018/libnfs_shift_pcode_supplement.so"
  --recompiled-supplement "$artifact_root/function-00886c80-pcode-20261018/libnfs_shift_pcode_supplement.so"
  --recompiled-supplement "$artifact_root/function-00a69220-pcode-20261018/libnfs_shift_pcode_supplement.so"
  --recompiled-supplement "$artifact_root/libnfs_shift_pcode_rvi_00909dcd.so"
  # rvi_00900f48 is already exported by libnfs_shift_pcode_startup_20261018.so.
  --recompiled-supplement "$artifact_root/libnfs_shift_pcode_rvi_0091577e.so"
  --recompiled-supplement "$artifact_root/libnfs_shift_pcode_rvi_00916b2d.so"
  --recompiled-supplement "$artifact_root/libnfs_shift_pcode_rvi_0091bf62.so"
  --recompiled-supplement "$artifact_root/libnfs_shift_pcode_rvi_00a74f20.so"
  --recompiled-supplement "$artifact_root/libnfs_shift_pcode_rvi_00a74fb0.so"
  --recompiled-supplement "$artifact_root/libnfs_shift_pcode_rvi_00a74fe0.so"
  --recompiled-supplement "$artifact_root/libnfs_shift_pcode_rvi_00a9aa80.so"
  --recompiled-supplement "$artifact_root/libnfs_shift_pcode_rvi_00a9aaa0.so"
  --recompiled-supplement "$artifact_root/libnfs_shift_pcode_rvi_00a9aab0.so"
  --recompiled-supplement "$artifact_root/libnfs_shift_pcode_rvi_00a9aac0.so"
  --recompiled-supplement "$artifact_root/libnfs_shift_pcode_rvi_00a9aad0.so"
  --recompiled-supplement "$artifact_root/libnfs_shift_pcode_rvi_00a9aaf0.so"
  --recompiled-supplement "$artifact_root/libnfs_shift_pcode_rvi_00a9ae1c.so"
  --recompiled-supplement "$artifact_root/libnfs_shift_pcode_rvi_00a9ae3e.so"
  --recompiled-supplement "$artifact_root/libnfs_shift_pcode_rvi_00a9ae54.so"
  --recompiled-supplement "$artifact_root/libnfs_shift_pcode_startup_00918b33_complete.so"
  --pe-image "$pe_image"
  --frames "$probe_frames"
  --recompiled-entrypoint
)

if [[ -n "${SHIFT_ENTRYPOINT_PROBE_EXTRA_OVERRIDES:-}" ]]; then
  mapfile -t extra_overrides <<< "$SHIFT_ENTRYPOINT_PROBE_EXTRA_OVERRIDES"
  for override in "${extra_overrides[@]}"; do
    [[ -z "$override" ]] && continue
    if [[ ! -r "$override" ]]; then
      printf 'extra P-code override is not readable: %s\n' "$override" >&2
      exit 2
    fi
    probe_args+=(--recompiled-override "$override")
  done
fi

if [[ -n "${SHIFT_ENTRYPOINT_PROBE_EXTRA_SUPPLEMENTS:-}" ]]; then
  mapfile -t extra_supplements <<< "$SHIFT_ENTRYPOINT_PROBE_EXTRA_SUPPLEMENTS"
  for supplement in "${extra_supplements[@]}"; do
    [[ -z "$supplement" ]] && continue
    if [[ ! -r "$supplement" ]]; then
      printf 'extra P-code supplement is not readable: %s\n' "$supplement" >&2
      exit 2
    fi
    probe_args+=(--recompiled-supplement "$supplement")
  done
fi

if [[ "$validation" == 1 ]]; then
  probe_args+=(--validation)
fi

timeout "${timeout_seconds}s" "$runtime" "${probe_args[@]}" >"$log_path" 2>&1
