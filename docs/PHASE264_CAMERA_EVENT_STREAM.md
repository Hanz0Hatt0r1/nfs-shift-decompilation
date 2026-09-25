# Phase 264 — Camera event stream boundary

Phase 264 reconstructs the event-stream wrapper `FUN_0080c710` around camera commands.

## Event filter

Each queued record is accepted only when its byte at `event +0x5` matches the current channel byte stored at `+0x580`.

The low byte of the dword at `event +0x4` selects the event handler:

| type | Callee |
|---:|---|
| 0 | `FUN_0080b910` |
| 1 | `FUN_0080bf30` |
| 2 | `FUN_0080c230` |
| 3 | `FUN_0080c2e0` |
| 5 | `FUN_0080e650` |

Only type `5` is decoded further in this phase. Its payload begins at `event +0xc` and is passed directly to the Camera command dispatcher reconstructed in Phase 263.

`camera_event_stream_runtime.py` preserves the other known event targets as opaque boundaries and reports unknown types as unsupported.

## Runtime chain

`event queue → channel filter → event type 5 → camera command → camera activation/switch gate → double-buffer state`

## Limits

The source of the event queue, meaning of the other event types, and gameplay/UI producers of camera commands remain unresolved.

Renderer and `RENDER.bff` remain untouched.