# Process 1 handoff — `FUN_00791020` rejected

BLOCKER: P1.3 still lacks an exact selected-HDVehicle writer for the four absolute consumer fields used by `FUN_00755950`.

INPUT: `SHIFT.Fun00791020ReceiverFrontier/1`, pinned PC retail `SHIFT.exe`, and existing selected-HDVehicle ownership contracts.

OUTPUT: `SHIFT.Fun00791020HDVehicleRejection/1` proves the candidate receiver descends from a freshly allocated `0x2b90` setup object, not the selected-HDVehicle root.

CONSUMER: Process 1 P1.3 producer tracing.

GATES_CHANGED: `FUN_00791020` is removed from the selected-HDVehicle root writer frontier. No retail input/control semantics are promoted. Provider count remains 7.

LIMITS: No semantic class name is assigned to the allocated setup object or its `+0x340` child.

TESTS: Contract identity, allocation/store chain, HDVehicle layout incompatibility, fail-closed semantics, and next-step gate are regression-covered.

NEXT_OWNER: Process 1.

NEXT_STEP: search direct/machine writers of `HDVehicle+0x938/+0x13b8/+0x1e38/+0x28b8`, requiring selected-HDVehicle receiver/base proof before tracing stored values toward retail input/control ownership.
