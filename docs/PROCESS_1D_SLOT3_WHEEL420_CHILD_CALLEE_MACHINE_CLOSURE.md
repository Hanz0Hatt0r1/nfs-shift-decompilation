# Process 1D: slot3 `[wheel+0x420]` child-callee machine closure

This shard closes the known transformed-receiver child branch that remained after the direct-callee alias inventory. Authority is the PC retail 1.02 `SHIFT.exe` machine image with SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

## Entry identity

The selected slot3 wheel root remains `HDVehicle+0x2380`; its selected target is wheel `+0x538` = `HDVehicle+0x28b8..+0x28bf`.

The three bounded direct calls do **not** receive that wheel root:

- `FUN_00760b50 @ 0x00760d02` loads `ECX=[wheel+0x420]`, then `0x00760d4b -> FUN_007ba860`. The receiver is the dereferenced child object.
- `FUN_00755f80 @ 0x00755f9c` loads `EAX=[wheel+0x420]`, derives `ECX=EAX+0xd4`, then `0x00755fb0 -> FUN_007af0a0`.
- `FUN_00755f80 @ 0x00755fb8` loads `ECX=[wheel+0x420]`, adds `0xd4`, then `0x00755fd1 -> FUN_007af010`.

This corrects the coarse earlier label that described both transform helpers simply as receiving `[wheel+0x420]`: their machine receiver is `child+0xd4`.

## Nested direct chain

`FUN_007ba860` preserves the child receiver and calls `FUN_007ba7e0` at `0x007ba8a0`. `FUN_007ba7e0` copies child `ECX` into `ESI`, derives `EDI=child+0xd4`, and calls `FUN_007af0a0` plus `FUN_007aefb0` on that interior. The closure therefore pins all five machine bodies, not just the three originally listed direct callees.

Across the five complete bodies there are zero child-relative GPR loads and zero child-relative GPR stores. In particular, there is no machine-visible child back-pointer load that could recover the selected wheel/`HDVehicle`, and no pointer persistence from the child domain.

`FUN_007ba860` writes scalar coefficient state only at child `+0x128/+0x12c/+0x130` (f32) and `+0x138/+0x140/+0x148` (f64). The transform helpers read receiver scalar fields and write caller-provided output buffers; they do not write receiver fields.

## Adjudication

The known `[wheel+0x420]` child-callee subset and its nested direct calls are closed, with no selected slot3 writer found. This does **not** prove the global callee-created-alias or stored/escaped-alias gates: unrelated runtime/generated aliases, callbacks, aggregate copies, and the separate 16-carrier source-storage replay remain open. External provider count therefore remains 7 and P1.3D remains incomplete.

Reproduce with:

```bash
python tools/ghidra/analyze_p1d_slot3_wheel420_child_callees_pe.py /path/to/SHIFT.exe \
  --output evidence/p1d_slot3_wheel420_child_callee_machine_closure.json
```
