# Phase 738 — FUN_007618f0 VehicleLoadData source ownership

Phase 737 closed the two pointer-backed vector inputs used by `FUN_007618f0`: `HDVehicle+0x820` and `HDVehicle+0x12a0` are the selected BMW FL/FR wheel BODY pointers, so their current origins come from persistent BODY indices 3 and 4.

Phase 738 closes the other Phase 728 input object and freezes its selected BMW values.

## Exact source owner

PC `SHIFT.exe.c` shows one source-visible direct call from `FUN_0076df50`:

```text
FUN_007618f0(this, this+0x4330, *(this+0x66b4))
```

The same setup function allocates `0x3848` bytes for `HDVehicle+0x66b4`, constructs the object with `FUN_007c3170`, and uses the exact allocation failure text:

```text
Failed to allocate a vehicle load data buffer
```

Therefore `FUN_007618f0 param_2` is the already source-named `VehicleLoadData` object. This identity comes from allocation/callsite continuity, not from guessing the meaning of offsets `+0x338/+0x918`.

PC machine code independently corroborates the ABI at `0x0076e275..0x0076e284`:

```text
mov  ecx,[esi+0x66b4]
push ecx                 ; param_2 = VehicleLoadData*
push ebx                 ; param_1 = HDVehicle+0x4330
mov  ecx,esi              ; this = HDVehicle
call FUN_007618f0
```

The exact span hashes to `e6e953ab0ea9f65c9cfb759d76887ed3852e7a2b415458b54ffba206ed6d12a9`.

The optional Ghidra provenance analyzer added in this phase was corrected to model both explicit arguments. IA-32 pushes arguments right-to-left: the nearest pre-call push is `param_1`; the second-nearest is `param_2`. It remains a machine cross-check rather than the semantic owner proof.

## VehicleLoadData+0x338

`FUN_007618f0` reads `VehicleLoadData+0x338` as the scalar used for the Phase 728 Y replacement.

`FUN_007bfbe0` owns that field. It is invoked with receiver `VehicleLoadData+0x8`, and its `receiver+0x330` store is therefore absolute `VehicleLoadData+0x338`.

For the selected Silverstone + BMW M3 E36 policy:

- physics mode: normal;
- Player Difficulty: 1;
- BMW CDF `CGHeight=0.280`;
- normal `CGHeight Scale[1]=0.6`.

The PC machine sequence at `0x007bff05..0x007bff5a` is precision-sensitive:

```text
call FUN_007a6be0
fstp dword local
fld  dword local
fmul dword [normal_scale + difficulty*4]
fstp qword [VehicleLoadData+0x338]
```

The CGHeight evaluation is explicitly narrowed to f32 before multiplication. The scale is also read as f32. There is **no** f32 store after multiplication: the x87 product is written directly to f64.

Selected exact inputs and output are:

```text
CGHeight f32 bits       0x3e8f5c29
scale 0.6 f32 bits      0x3f19999a
stored f64 product bits 0x3fc5810634bc6a80
stored value            0.16800000739097598
```

A host path that rounds the multiplication result back through f32 would instead produce widened-f64 bits `0x3fc5810640000000`; the native regression explicitly rejects that 1-step precision substitution.

## VehicleLoadData+0x918

The exact retail archive `BMW_M3_E36.bff` contains:

```text
vehicles\physics\chassis\bmw_m3_e36.cdf
```

Archive SHA-256:

```text
c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70
```

Decoded CDF SHA-256:

```text
bbee83f0d2fdcbfc2bbd62ddb2a10bf6fed71bb1b4fa78f303a4730d038b970d
```

The selected resource contains:

```text
CGHeight=0.280
FWCenter=(0.00, -0.100, -0.50)
```

`FUN_007c3170` places the front-wing subrecord at `VehicleLoadData+0x6a0`. `FUN_007c0a20` parses property `FWCenter` into subrecord `+0x278/+0x280/+0x288`, which are absolute `VehicleLoadData+0x918/+0x920/+0x928`.

Thus the exact Phase 728 selected vector is:

```text
source_vec_0918 = (0.0, -0.1, -0.5)
```

with f64 bits:

```text
X 0x0000000000000000
Y 0xbfb999999999999a
Z 0xbfe0000000000000
```

This is read from the actual BMW CDF. The constructor's zero defaults are not used as evidence for the selected value.

## Native contract

`SHIFT.Fun007618f0SelectedBMWSource/1` freezes the selected source values in:

```text
native_runtime/include/shift_fun_007618f0_selected_bmw_source.hpp
```

The native regression verifies the exact f32 source bits, direct f64 product bits, incorrect rounded-f32 witness, and BMW `FWCenter` bits.

Together with Phase 737, all four inputs of the Phase 728 local-sample formula are now source-backed for the selected session.

## Remaining boundary

Phase 738 does not yet replace the complete production `FUN_00765c40` provider. The next join must execute, for each recovered pass:

```text
current BODY3/BODY4 origins
+ selected VehicleLoadData source
-> Phase 728 FUN_007618f0 local sample
-> Phase 727 current BODY0 transform
-> FUN_00765c40 collision-query world_position
```

Pass 1 must observe the persistent BODY array after the first half-step. Collision-provider implementation and any residual `FUN_00765c40` side effects stay external unless separately proved.

The active top-level provider count therefore remains seven in Phase 738.
