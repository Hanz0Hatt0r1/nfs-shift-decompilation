# Phase 684 — `FUN_0076d100` required anchor sequence

Process 1 `SHIFT.GhidraBodyUpdateScheduleFrontier/2` proves a required relative
order among direct-call anchors inside `FUN_0076d100`:

```text
FUN_00765c40
FUN_00758b50
FUN_00766510
FUN_00769ef0
```

The same frontier uniquely recovers `FUN_00769ef0` as the physics-pass tail
callee whose required direct anchors are:

```text
FUN_007675f0
FUN_007682c0
```

Phase 684 ports only these ordering facts. It does not claim that the listed
anchors are adjacent in retail code or that intervening local arithmetic and
other calls have been reconstructed.

## Native contract

New files:

```text
native_runtime/include/shift_fun_0076d100_anchor_sequence.hpp
native_runtime/src/fun_0076d100_anchor_sequence.cpp
```

Format:

```text
SHIFT.NativeFun0076d100AnchorSequence/1
```

The API requires five external callback boundaries corresponding to the leaf
anchors:

- `FUN_00765c40` contact-factor anchor;
- `FUN_00758b50` wheel-update anchor;
- `FUN_00766510` contact-response anchor;
- `FUN_007675f0` contact-outer anchor inside recovered tail `FUN_00769ef0`;
- `FUN_007682c0` motion-read-gate anchor inside that same tail.

The native sequence executes them only in the relative order proven by the
Ghidra frontier. `tail_invocation_count=1` records entry through the recovered
`FUN_00769ef0` boundary before its two required anchors.

All callbacks are mandatory; a missing callback fails closed.

## Reference oracle

Python contract/oracle:

```text
src/physics/fun_0076d100_anchor_sequence_runtime.py
```

Regression:

```text
tests/test_fun_0076d100_anchor_sequence_runtime.py
```

The oracle freezes:

```text
required_pass_order =
  FUN_00765c40 -> FUN_00758b50 -> FUN_00766510 -> FUN_00769ef0

required_tail_order =
  FUN_007675f0 -> FUN_007682c0
```

and explicitly reports:

```text
complete_fun_0076d100_semantics = false
complete_fun_00769ef0_semantics = false
intervening_local_work_modeled = false
callback_bodies_external = true
```

## Nested native regression

`shift_runtime_fun_0076d100_anchor_sequence_check` first verifies the standalone
leaf-anchor order. It then nests Phase 684 inside the Phase 683
`FUN_00770e80` two-half-step scheduler.

For each of the two proven outer passes, the regression executes the Phase 684
required physics-pass anchors before the Phase 683 `FUN_00765470` half-step
anchor. The half-step callback uses the existing Phase 682 raw BODY integration
path.

The expected visible anchor trace is therefore:

```text
pass 0:
  FUN_00765c40
  FUN_00758b50
  FUN_00766510
  FUN_007675f0
  FUN_007682c0
  FUN_00765470
  FUN_007b8810
pass 1:
  FUN_00765c40
  FUN_00758b50
  FUN_00766510
  FUN_007675f0
  FUN_007682c0
  FUN_00765470
  FUN_007b8810
```

The fixture carries one raw `0x170` BODY record with `motion_triplet.x=4.0` and
`outer_dt=0.5`, so the two admitted half-step integrations preserve the Phase
683 deterministic persistent-state result:

```text
origin.x: 0 -> 1 -> 2
motion.x: 4 -> 4 -> 4
```

An unrelated record byte is also required to remain unchanged.

This gives a larger source-backed native chain while preserving the distinction
between proven anchor ordering and still-unported callback bodies.

## Evidence boundary

Phase 684 does **not** prove or implement:

- complete arithmetic or side effects of `FUN_00765c40`;
- complete `FUN_00758b50` wheel update;
- complete `FUN_00766510` response application;
- complete `FUN_00769ef0` tail behavior;
- complete `FUN_007675f0` or `FUN_007682c0` behavior;
- unlisted/intervening local work inside `FUN_0076d100` or `FUN_00769ef0`;
- complete `FUN_0076d100` semantics;
- rendered-frame cadence or higher-level input ownership.

The next native phase should replace an external callback only when its own
source/static contract is sufficient; this anchor sequence must not be used to
infer adjacency or semantics not present in the Process 1 frontier.
