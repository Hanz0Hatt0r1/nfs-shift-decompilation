#!/usr/bin/env bash
# Incremental native runtime build. Never regenerates the multi-GB retail P-code ELF.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash tools/build_shift_runtime_cached.sh [--build-dir DIR] [--jobs N] [--target NAME]
Keeps the CMake build directory and uses ccache/sccache if installed.
Only native runtime targets are built; the pinned P-code ELF remains external.
EOF
}

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
build_dir="$repo_root/native_runtime/build"
jobs=""
targets=()
target_count=0
while (( $# )); do
  case "$1" in
    --build-dir) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; build_dir="$2"; shift 2 ;;
    --jobs) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; jobs="$2"; shift 2 ;;
    --target) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; targets+=("$2"); target_count=$(( target_count + 1 )); shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'unexpected argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done
if [[ -n "$jobs" && ! "$jobs" =~ ^[1-9][0-9]*$ ]]; then
  echo '--jobs must be a positive integer' >&2
  exit 2
fi
if (( target_count == 0 )); then
  targets=(shift_runtime shift_runtime_recompiled_pcode_module_check)
fi

mkdir -p "$build_dir"
configure=(cmake -S "$repo_root/native_runtime" -B "$build_dir" -DCMAKE_BUILD_TYPE=Release)
if [[ ! -f "$build_dir/CMakeCache.txt" ]] && command -v ninja >/dev/null 2>&1; then
  configure+=(-G Ninja)
fi

cache_mode=auto
if [[ -v SHIFT_COMPILER_CACHE ]]; then cache_mode="$SHIFT_COMPILER_CACHE"; fi
if [[ "$cache_mode" == auto ]]; then
  if command -v ccache >/dev/null 2>&1; then
    launcher=ccache
  elif command -v sccache >/dev/null 2>&1; then
    launcher=sccache
  else
    launcher=""
  fi
elif [[ "$cache_mode" == off ]]; then
  launcher=""
else
  launcher="$cache_mode"
  command -v "$launcher" >/dev/null 2>&1 || {
    printf 'compiler cache executable not found: %s\n' "$launcher" >&2
    exit 2
  }
fi

configure+=("-DCMAKE_C_COMPILER_LAUNCHER=$launcher" "-DCMAKE_CXX_COMPILER_LAUNCHER=$launcher")
"configure[@]"
build=(cmake --build "$build_dir" --target "targets[@]" --parallel)
if [[ -n "$jobs" ]]; then
  build+=("$jobs")
fi
"build[@]"
