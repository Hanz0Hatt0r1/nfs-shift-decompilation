# Process 1A — remaining direct `participant+0x4b0` writer worklist

## BLOCKER

P1.1a still lacks the exact runtime producer of the selected PhysicsParticipant `+0x4b0` value consumed by `FUN_00713630`.

The direct-displacement surface is now reduced to seven unresolved sites after the merged VehicleLoadData, singleton-byte, 0x600-allocation, `FUN_00481e20`, FMOD FLAC and TBC compound rejections.

## OUTPUT

`SHIFT.Fun00713630Participant4b0RemainingDirectWorklist/1` freezes the current direct surface:

- `0x00487d2d` — `FUN_004876f0`, f32;
- `0x005b0b1b` — `FUN_005b0af0`, u8;
- `0x005b0ea6` — `FUN_005b0e60`, u8;
- `0x00607f22` — `FUN_00607980`, u32;
- `0x0076019f` — unassigned function in the original inventory, f64;
- `0x00832f46` — `FUN_00832a80`, u32;
- `0x0098e583` — `FUN_0098e558`, u32 OR.

This contract makes no identity claim for any listed site. Every candidate must be joined or rejected by exact receiver provenance; matching `+0x4b0` displacement is insufficient.

## GATES_CHANGED

- unresolved direct-displacement candidates: **7**;
- selected participant runtime `+0x4b0` producer: **open**;
- P1.1a/P1.1: **incomplete**;
- `contact_response` removal: **not authorized**;
- provider count: **7**.

## NEXT_STEP

Adjudicate the seven sites by exact receiver provenance. Do not reopen already-rejected direct candidates. Only after all seven are closed should Process 1A widen to computed-address, escaped-alias, indirect-dispatch or residual bulk-copy paths.
