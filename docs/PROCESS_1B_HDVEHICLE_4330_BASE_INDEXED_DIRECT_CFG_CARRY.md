# Process 1B: HDVehicle+0x4330 base/index direct-CFG carry

## Result

A retail PC 1.02 fixed-point CFG pass extends the base/index writable-data provenance beyond the previous same-block windows. The pass tracks GPR taint through copies/transforms and follows direct conditional/unconditional branch successors until state convergence.

For the same **63** base/index-addressed writable `.data` loads / **51** effective addresses:

- **44** loads carry live GPR taint across at least one direct basic-block edge;
- **228** unique load/branch/taint-state events occur at **199** branch sites; state identity includes the transformed/untransformed taint bit;
- **0** modeled paths dispatch `CALL/JMP` through the tainted register;
- fixed-point max-out count is **0**;
- **56** direct-call boundaries remain with live taint;
- **11** indirect-call boundaries remain where the call target register itself is not tainted but another tainted register is live;
- indirect-jump boundaries are **0**.

The eleven indirect calls are kept fail-closed instead of guessing interprocedural provenance.

## Aggregate effect

`SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/14` increases bounded coverage classes from **17 to 18**. Exact carrier hits remain **0**.

## Boundary

This is a direct-CFG GPR subset, not global inter-block closure. Still open are direct-call and indirect-call interprocedural continuation, stack/alias/heap/runtime mutation, generated/copied pointer provenance, global incoming indirect entry, the manager+0x374 identity join, slot2 `0x004b86cf`, and aggregate P1.3. Provider count remains **7**.

## Next

Classify the 11 indirect-call live-taint boundaries first, then the relevant direct-call live-taint boundaries. Only after those surfaces are bounded should the global inter-block or incoming-indirect-entry gates be reconsidered.
