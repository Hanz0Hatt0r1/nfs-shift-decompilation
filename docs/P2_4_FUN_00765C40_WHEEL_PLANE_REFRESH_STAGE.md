# Process 2 P2.4 — `FUN_00765c40` wheel-plane refresh stage

## INPUT

The PC-retail direct write surface proves the first residual stage writes four qwords at `+0x0a70/+0x14f0/+0x1f70/+0x29f0`, using wheel stride `0x0a80`, from sites `0x00765cf7/0x00765d46` and `0x00765d9c/0x00765dd7`.

Current ownership does not prove the arithmetic that produces those qwords or a physical semantic name for the lanes.

## OUTPUT

Adds `SHIFT.Fun00765c40WheelPlaneRefreshStage/1`. Native code owns the exact four destinations and retail ordering while accepting four source-computed qword payloads explicitly and preserving them bit-for-bit.

The stage is compile-time pinned as `WheelPlaneStateRefresh`, the first stage in `SHIFT.Fun00765c40ResidualPassContract/1`.

## GATES_CHANGED

- four pre-query qword destinations: native-owned;
- exact count/stride/offset order: pinned;
- source arithmetic: remains external;
- semantic/physical interpretation: unpromoted;
- complete `FUN_00765c40`: still incomplete;
- top-level provider: retained;
- external provider count: remains 7.

## NEXT_STEP

Close the source computation feeding these four qwords and the remaining registered wheel-job scheduling. Provider removal remains fail-closed until end-to-end execution exists.
