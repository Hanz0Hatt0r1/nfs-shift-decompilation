# Wine-native D3D9 capture

This directory contains the first native producer for capturing Need for Speed:
SHIFT through a modified Wine 10.0 d3d9.dll.

Unlike native_capture/, this path does not proxy or wrap D3D9. It adds logging
directly to Wine's implementation of the existing IDirect3DDevice9 methods,
then builds the normal PE d3d9.dll that can be placed next to SHIFT.exe.

## Producer

shift_d3d9_capture.c emits the same event names consumed by:

- d3d9_capture_schema.py;
- d3d9_runtime_trace.py;
- the BMW same-instance runtime gates.

Captured boundaries are:

- vertex declaration creation/binding;
- vertex stream binding;
- index-buffer binding;
- texture-stage binding;
- vertex/pixel shader creation and binding;
- vertex/pixel float-constant writes;
- indexed draw submission.

Declaration and shader creation events include their raw byte streams as
bytes_hex, preserving enough data for the existing Python decoder to identify
the exact declaration/shader object.

## Injection

Run the injector against a clean Wine 10.0 source tree:

    python3 tools/inject_wine_d3d9_capture.py /path/to/wine-10.0

Use --check-only to verify the source anchors without modifying it:

    python3 tools/inject_wine_d3d9_capture.py \
      /path/to/wine-10.0 \
      --check-only

The injector:

1. verifies the Wine D3D9 source shape used by Wine 10.0;
2. copies the producer and header into dlls/d3d9;
3. adds the producer to dlls/d3d9/Makefile.in;
4. includes the capture interface from d3d9_private.h;
5. instruments the exact D3D9 functions used by the current SHIFT capture ABI.

The operation is idempotent. Re-running it on the same patched tree does not
duplicate the hooks.

## Build

A 32-bit Wine build is required because the target game is a 32-bit process.

The helper performs injection, configures a separate 32-bit build directory, and
builds only the D3D9 module:

    tools/build_wine_d3d9_capture.sh /path/to/wine-10.0

Equivalent manual build:

    ../wine-10.0/configure \
      --disable-win64 \
      --prefix="$PWD/../wine-prefix"

    make -j"$(getconf _NPROCESSORS_ONLN)" \
      dlls/d3d9/d3d9.dll

The resulting PE is expected at:

    <build-dir>/dlls/d3d9/d3d9.dll

## Deploy to SHIFT

The modified DLL is a complete Wine implementation of D3D9, so it replaces the
game-local proxy experiment.

    GAME="$HOME/PortProton/prefixes/DEFAULT/drive_c/GOG Games/Need For Speed.Shift.v 1.02"

    cp <build-dir>/dlls/d3d9/d3d9.dll "$GAME/d3d9.dll"

    WINEDLLOVERRIDES="d3d9=n" \
    SHIFT_D3D9_CAPTURE="$GAME/shift_m3_capture.jsonl" \
    wine "$GAME/SHIFT.exe"

Keep the PortProton/Wine executable and WINEPREFIX configuration already used
for the retail game. Only the native override and capture path are added.

## Output

A valid capture line looks conceptually like:

    {"event_index":0,"frame":0,"thread_id":1234,"event":"create_vertex_declaration","device_ptr":"0x...","declaration_ptr":"0x...","bytes_hex":"..."}

The event stream is directly consumable by:

    python shift_importer.py validate-d3d9-capture shift_m3_capture.jsonl

    python bmw_post_capture_pipeline.py \
      BMW_M3_E36.bff \
      RENDER.bff \
      shift_m3_capture.jsonl \
      out/bmw_runtime

No synthetic Direct3DCreate9 event is emitted. Present advances the internal
frame counter so every subsequent event receives the next frame id.

## Current limitation

This first Wine-native producer intentionally stops at the object/state layer.
Texture resource descriptors and surface snapshots are not yet injected into
Wine itself. That is the next runtime layer after the first real JSONL trace is
proven against the BMW M3 E36 draw.

The existing native_capture/ proxy remains available as a separate experiment,
but it is not required for this Wine-native path.
