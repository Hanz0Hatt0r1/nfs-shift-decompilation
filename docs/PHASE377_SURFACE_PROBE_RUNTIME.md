# Phase 377 — recursive surface probe runtime

Phase 377 reconstructs `FUN_00759210` from `SHIFT.exe.c`.

The exact boundary is:
- point/node projection through the node normal;
- negative projection recurses to parent `+0x17c);
- direction is normalize((0,1,0) × normal), with the source fallback (1,0,0) for length <= 0.01;
- candidate is node point + direction × radius;
- blend factor is the source ratio, clamped to [0,1];
- same-sign child radius at `+0x180` blends candidate point and radius.

No physical name is assigned to any node field.
