# Phase 661 — native recursive surface probe

Phase 661 ports `FUN_00759210` together with its recovered horizontal-perpendicular helper `FUN_007ade70` into `shift_runtime_physics`.

## Exact `FUN_007ade70` boundary

The helper consumes the node vector at `+0x13c`, computes world-up cross source, and uses the retail float32 normalization path:

- source/cross components are float32;
- squared length is stored through a float32 local;
- square-root result is stored through float32;
- normalization occurs only when `length > 0.01f` (`0x3C23D70A`);
- otherwise the exact fallback is `(1, 0, 0)`.

This uses the later, more precise Phase 513 evidence rather than silently retaining the older double-only approximation in the original Phase 377 Python oracle.

## `FUN_00759210` probe

The native probe preserves the recovered node fields:

- point `+0x8c/+0x90/+0x94`;
- normal/direction source `+0x13c/+0x140/+0x144`;
- distance `+0xfc`;
- radius `+0x158`;
- parent `+0x17c`;
- child `+0x180`.

Execution is:

1. `projection = dot(query - node.point, node.normal)`;
2. when projection is negative and a parent exists, recurse to the parent;
3. obtain the horizontal direction from `FUN_007ade70`;
4. build `candidate = node.point + direction * radius`;
5. compute the recovered denominator and clamped blend factor;
6. if a child exists and its radius has the same sign, blend current/child candidates and radius;
7. otherwise return the current candidate and absolute radius.

Zero denominator/radius/distance paths and non-finite inputs fail closed.

## Regression

`shift_runtime_surface_probe_check` covers:

- normalized and fallback `FUN_007ade70` branches;
- behavior below and above the exact float threshold;
- the Phase 377 candidate fixture;
- negative-projection parent recursion;
- same-sign child interpolation;
- zero-path and non-finite rejection.

`native-physics-recent` now executes Phases 656–661.

## Remaining outer kernel

Phase 660 provides native `FUN_00759c90` and Phase 661 provides native `FUN_00759210`. Those are the two major previously external arithmetic dependencies in the recovered `FUN_007675f0` outer kernel. Its distance state update, speed/gap shaping and two `FUN_007ba9e0` submissions can therefore be ported next while keeping source-opaque fields unnamed.
