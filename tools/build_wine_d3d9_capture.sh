#!/usr/bin/env bash
set -euo pipefail

WINE_SRC="\${1:-}"
BUILD_DIR="\${2:-}"
INSTALL_DIR="\${3:-}"

if [[ -z "$WINE_SRC" ]]; then
    echo "usage: $0 /path/to/wine-10.0 [build-dir] [install-dir]" >&2
    exit 2
fi

WINE_SRC="$(cd "$WINE_SRC" && pwd)"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -f "$WINE_SRC/configure" ]]; then
    echo "Wine source tree not found: $WINE_SRC" >&2
    exit 1
fi

if [[ -z "$BUILD_DIR" ]]; then
    BUILD_DIR="$WINE_SRC/build-shift-d3d9-32"
else
    mkdir -p "$BUILD_DIR"
    BUILD_DIR="$(cd "$BUILD_DIR" && pwd)"
fi

if [[ -z "$INSTALL_DIR" ]]; then
    INSTALL_DIR="$BUILD_DIR/install"
fi

python3 "$ROOT/tools/inject_wine_d3d9_capture.py" "$WINE_SRC"

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

if [[ ! -f Makefile ]]; then
    "$WINE_SRC/configure" \
        --disable-win64 \
        --prefix="$INSTALL_DIR"
fi

JOBS="\${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)}"

make -j"$JOBS" dlls/d3d9/d3d9.dll

DLL="$BUILD_DIR/dlls/d3d9/d3d9.dll"
if [[ ! -f "$DLL" ]]; then
    echo "PE d3d9.dll was not produced at: $DLL" >&2
    echo "Inspect $BUILD_DIR/dlls/d3d9/ for the build result." >&2
    exit 1
fi

file "$DLL"
printf 'D3D9_DLL=%s\n' "$DLL"
