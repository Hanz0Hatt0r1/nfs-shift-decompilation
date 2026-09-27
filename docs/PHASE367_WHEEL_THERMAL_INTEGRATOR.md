# Phase 367 — wheel thermal integrator runtime

Phase 367 continues the physics path through FUN_00755a60, called once per wheel
from FUN_00770e80 before the existing FUN_00760b50 thermal-reserve update.

## Direct call topology

The caller keeps a double-pointer at this +0x740 and passes that pointer minus
0x68 elements to FUN_00755a60. Because the pointer arithmetic is on double,
this is exactly this +0x400. The loop advances by 0x150 bytes, yielding four
thermal substructures within the larger 0xA80 wheel runtime objects.

## Recovered state

The function updates three temperature nodes:

- +0x7b0
- +0x7b8
- +0x7c0

and one shared reservoir:

- +0x7c8

The reservoir is clamped through FUN_00753620 to [273.16, 546.32].
FUN_00752fc0 derives +0x7d8 from the clamped reservoir and updates its
auxiliary thermal field from +0x7f0 and +0x7e8.

## Recovered arithmetic

Ambient channels receive the constant 273.16.

For positive activity at +0x740:

source_heat = abs(+0x350) * +0x818 * +0x740

Otherwise source heat is zero.

A shape branch uses sqrt(+0x3e0) when +0x3e0 <= 1. Values below 0.5 are
replaced by value squared plus 0.25. The resulting shape factor is one minus
that adjusted value.

The secondary source is:

shape_factor * +0x738 * (+0x668)^2 * +0x820

Two clamped steering terms determine three timestep fractions:

f0 = (1.5 + 0.5*b - a) / 3 * dt
f1 = (1.5 - b) / 3 * dt
f2 = (1.5 + a + 0.5*b) / 3 * dt

Each temperature receives its fraction of both source terms, an ambient-A
exchange when activity is positive, an ambient-B exchange, and a transfer with
the shared reservoir. The reservoir transfer is subtracted immediately for
each node, so transfers are sequential across the three nodes.

The average temperature is then used for the abrasion/wear accumulator.
When the wear gate is enabled and +0x7f8 exceeds 0.6875, the state is reduced
by the global wear scale and clamped back to 0.6875 if crossed.

The final factor uses the average-temperature delta from +0x758, selects
+0x770 for non-negative delta or +0x768 otherwise, and adds the reservoir
spread term using +0x790 divided by the pre-clamp reference
+0x780 + +0x788*+0x738.

The final output is:

+0x800 = (1 - 0.5 * max(1, factor)^2) * +0x7f8

## Scope boundary

This phase does not infer physical units, names for the three temperature
nodes, the meaning of the final output, exact FUN_0070e2c0 side effects, or
semantic ownership of the decompiler-aliased param_3 stack slot.
