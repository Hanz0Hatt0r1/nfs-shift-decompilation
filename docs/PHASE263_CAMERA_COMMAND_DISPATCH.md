# Phase 263 — Camera command dispatch

Phase 263 reconstructs the `switch(command[1])` in `FUN_0080e650`.

## Proven branches

| command[1] | Runtime operation | Callee |
|---:|---|---|
| 1 | static-view transition | `FUN_0080de00(this, command[4], command[2])` |
| 2 | camera activation | `FUN_0080e1b0(this, command[4], command[5], command[3])` |
| 3 | camera activation | `FUN_0080e1b0(this, command[4], command[5], command[3])` |
| 4 | external-view source | `FUN_0080d520(this, command[0], 1)` |

`camera_command_runtime.py` preserves the positional argument order exactly and does not assign higher-level names to the integer command fields.

Unknown command kinds are reported as `unsupported` rather than guessed.

## Integration

The command dispatcher connects the previously reconstructed camera runtime pieces:

`command → static-view / activation / external source → CameraManager state gate → buffer/snapshot transition`

`camera-command` is exposed through the universal importer.

## Limits

This phase does not infer where command records originate, how mode numbers are presented to gameplay/UI code, or what `FUN_0080de00`, `FUN_0080d520` and callbacks do internally beyond their established signatures.

Renderer and `RENDER.bff` remain untouched.