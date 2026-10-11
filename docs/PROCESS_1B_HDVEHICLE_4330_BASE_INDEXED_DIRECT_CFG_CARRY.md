# Process 1B: HDVehicle+0x4330 base/index direct-CFG carry

## Result

A retail PC 1.02 fixed-point CFG pass extends the base/index writable-data provenance beyond the previous same-block windows. The pass tracks GPR taint through copies/transforms, follows direct conditional/unconditional branch successors until state convergence, and propagates taint through memory loads whose address expression depends on a tainted GPR.

For the same **63** base/index-addressed writable `.data` loads / **51** effective addresses:

- **44** loads carry live GPR taint across at least one direct basic-block edge;
- **228** unique load/branch/taint-state events occur at **199** branch sites; state identity includes the transformed/untransformed taint bit;
- fixed-point max-out count is **0**;
- **2** indirect `CALL` targets are memory-derived from base/index writable-data values;
- those exact sites are `0x00553247` from load `0x00553240 / 0x00b83dc0` and `0x005539ac` from load `0x0055399a / 0x00b83ec0`, both through `[eax+0x4] -> edx`;
- **56** direct-call boundaries remain with live taint;
- **9** additional indirect-call boundaries remain where the call target is not tainted-derived in this model but another tainted register is live;
- indirect-jump boundaries are **0**.

The two memory-derived target identities are deliberately left unresolved by this contract rather than treated as negative evidence.

## Aggregate effect

`SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/14` increases bounded coverage classes from **17 to 18**. Previously resolved exact carrier hits remain **0**, but the two newly recovered memory-derived target identities remain an explicit open frontier.

## Boundary

This is a direct-CFG plus memory-dereference subset, not global inter-block closure. Still open are exact target provenance for the two positive indirect calls, direct/indirect-call interprocedural continuation, stack/alias/heap/runtime mutation, generated/copied pointer provenance, global incoming indirect entry, the manager+0x374 identity join, slot2 `0x004b86cf`, and aggregate P1.3. Provider count remains **7**.

## Next

Recover exact target provenance for `0x00553247` and `0x005539ac` first. Then classify the remaining nine indirect-call and relevant direct-call live-taint boundaries before reconsidering global inter-block or incoming-indirect-entry gates.
