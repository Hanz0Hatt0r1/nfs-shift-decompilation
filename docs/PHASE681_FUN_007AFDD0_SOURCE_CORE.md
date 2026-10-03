# Phase 681 — `FUN_007afdd0` recovered source core

Phase 680 deliberately stopped before implementing the BODY basis writer because
the repository lacked a targeted machine/p-code slice for `FUN_007afdd0`.
Afterward the existing Ghidra corpus on Google Drive exposed the recovered
`SHIFT.exe.c` body, including `FUN_007afdd0` at source line 810824 and its
`FUN_007bab70` callsite at line 819073.

Phase 681 ports the arithmetic that is actually explicit in that recovered C
body while keeping the unresolved x87/CRT scalar production outside the native
kernel.

## Recovered call boundary

`FUN_007bab70` forms three f64 values from the persistent BODY cross-vector and
timestep, then calls:

```text
FUN_007afdd0(BODY + 0xd4, cross_vector * dt)
```

The receiver is a contiguous nine-float basis at BODY `+0xd4..+0xf4`.  The
argument is three doubles.

## Recovered zero test and normalization

The source performs the following typed boundary:

```text
ext80(z*z + x*x + y*y)
  -> f32 cast for != 0 test
  -> __CIsqrt
  -> f32 sqrt magnitude
  -> f32 reciprocal
  -> each input f64 cast to f32
  -> normalized x/y/z stored as f32 temporaries
```

A zero f32 magnitude-test value returns without touching the basis.

Phase 681 does not call host `sqrt`, `sin` or `cos`.  Instead the source-core API
requires four explicit f32 scalar boundary values:

```text
squared_magnitude_test
sqrt_magnitude
sine
cosine
```

This leaves the exact x87/CRT behavior available for a later machine-backed
implementation.

## Trigonometric helper roles

The recovered source calls:

```text
FUN_00900c40 -> f32 result used in sine terms
FUN_00900b10 -> f32 result used as cosine / 1-c
```

Their surrounding CRT implementations independently corroborate the roles:

- the `FUN_00900c40` fast path reaches `FUN_0090a37e`, whose tiny-input branch
  returns approximately the input (`sin(x) ~ x`);
- the `FUN_00900b10` fast path reaches `FUN_00909e0e`, whose tiny-input branch
  returns approximately one (`cos(x) ~ 1`).

Both dispatchers inspect MXCSR and the x87 control word, which is why replacing
them with host libm is not admitted yet.

## Recovered coefficient graph

With normalized axis `(x,y,z)`, source f32 sine `s` and source f32 cosine `c`,
the recovered nine coefficient slots are structurally:

```text
c + (1-c) x^2        (1-c)xy - zs          (1-c)xz + ys
(1-c)xy + zs         c + (1-c) y^2         (1-c)yz - xs
(1-c)xz - ys         (1-c)yz + xs          c + (1-c) z^2
```

The shape is the standard axis-angle/Rodrigues coefficient pattern, but Phase
681 treats that observation only as a description of the recovered expression
graph.  Machine parity still depends on the retail evaluation precision/order.

## In-place basis update order

The basis is not first copied wholesale.  The source processes exactly three
stripes:

```text
{0,3,6}
{1,4,7}
{2,5,8}
```

For each stripe all three old f32 values are loaded into temporaries before any
of the corresponding three destinations are overwritten.  The native source
core preserves that sequence.

## New native API

Files:

```text
native_runtime/include/shift_fun_007afdd0_source_core.hpp
native_runtime/src/fun_007afdd0_source_core.cpp
```

Entry point:

```text
execute_fun_007afdd0_source_core(...)
```

Format:

```text
SHIFT.NativeFun007afdd0SourceCore/1
```

It returns:

- whether the non-zero path executed;
- normalized f32 axis;
- nine source-shaped f32 rotation coefficients;
- updated nine-float basis.

The implementation rejects non-finite basis/input/scalar data on the supported
finite path.  The zero path consumes only the magnitude-test value, matching the
recovered early return.

## Python oracle and evidence

The reference implementation is:

```text
src/physics/fun_007afdd0_source_core.py
```

The machine-readable evidence summary is:

```text
evidence/fun_007afdd0_source_core.json
```

Both explicitly state:

```text
machine_precision_gate_required = true
native_callback_replacement_ready = false
```

## Regression

Phase 681 verifies:

- exact zero-path no-op behavior;
- f64 -> f32 input casts before normalized-axis multiplication;
- source coefficient placement;
- a deterministic Z-axis quarter-turn;
- exact in-place stripe ordering on a non-identity basis;
- rejection of missing/non-finite scalar boundary values on the non-zero path;
- absence of host sqrt/sin/cos from the source core;
- C++ and Python contract metadata agree on the unresolved machine gate.

## Why Phase 679 still uses an external basis callback

This phase intentionally does not wire the new source core into
`execute_fun_007b2270_body_buffer_with_basis_callback()`.

The recovered C body does not by itself prove:

1. the exact x87 stack value presented to both trig dispatcher calls;
2. whether compound f32 expressions retain extended precision before stores;
3. ambient x87 control-word and MXCSR state at the callsite;
4. exact instruction-level memory/load ordering under all aliases.

Those are exactly the blockers represented by
`SHIFT.Fun007afdd0BasisRotationStatic/1` from Phase 680.

## Next gate

Run the Phase 680 targeted exporter against the existing analyzed Ghidra project
and join its instruction/p-code report with this source contract.  Once the
scalar argument/result and excess-precision boundaries are machine-proven, the
external basis callback can be replaced by an exact native `FUN_007afdd0` path.
