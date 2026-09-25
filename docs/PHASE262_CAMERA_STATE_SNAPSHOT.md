# Phase 262 — CameraManager state snapshot and double-buffer transition

Phase 262 tightens the camera switch gate and adds the rollback/update state that surrounds camera transitions.

## CameraSwitchGateRuntime/2

`FUN_0080d3d0` compares the requested mode against `+0x26a8`. For mode `1`, the request's secondary value is compared with the active camera buffer's dword at `+0xe4`; the request byte is compared with active-buffer byte `+0xf2`. The requested camera id is compared with `+0x26a0`, and a clean dirty byte at `+0x269d` is required for the fast path.

The earlier public `/1` contract used abstract `sub_index/sub_flag` state names. `/2` explicitly records the active-buffer origin so the schema reflects the decompiled access path.

## FUN_0080e040 snapshot

`FUN_0080e040` emits exactly six dword values:

| Snapshot word | Source |
|---|---|
| 0 | `+0x2568` camera source/reference |
| 1 | `+0x26a8` current mode |
| 2 | active buffer `+0xe4` |
| 3 | `+0x26a0` active camera id |
| 4 | `+0x26a4` active group |
| 5 | type-dependent runtime object `+0x7c`, otherwise active group |

`camera_state_snapshot_runtime.py` preserves these six words verbatim and puts active-buffer index/flag into separate `source_context` metadata rather than pretending they are serialized snapshot fields.

## FUN_0080cd40 double buffer

Two camera-data buffers are selected through `+0x2560`, initially `0`. `FUN_0080cd40` is guarded by `+0x269c`; when not already inside an update it switches the index with `1 - current` and performs three source-backed copies:

- camera/view data: `old + 0xbe0` → `new + 0x20` via `FUN_0081e6c0`;
- static-camera state: `old + 0x1a20` → `new + 0x17a0` with `0x280` stride via `FUN_00815eb0`;
- tracking-camera state: `old + 0x2100` → `new + 0x1ca0` with `0x460` stride via `FUN_00815eb0`.

The Python contract exposes these copy directions but does not reinterpret the copied object payloads.

## Initialization

`FUN_0080e960` / `FUN_0080ea10` establish the initial buffer index `0`, inactive camera/group ids `-1`, and clear the update guard. `FUN_0080dc60` performs the corresponding runtime reset of transient camera state.

Renderer and `RENDER.bff` remain untouched.