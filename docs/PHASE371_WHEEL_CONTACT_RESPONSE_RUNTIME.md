# Phase 371 — wheel contact-response kernel

Phase 371 closes the first response stage immediately after FUN_00765c40.

## Query scalar

FUN_00766510 clamps runtime state +0x38e0 to the inclusive interval
[0, +0x38e8]. It then forms the scalar

(+0x3910 * clamped + +0x3908) * FUN_00755340(+0x3918, local_60, local_50)

and stores the result at +0x39d0.

The physical name and unit of this scalar are intentionally unresolved.

## FUN_00752f10 / FUN_00755340

FUN_00752f10 stores four doubles:

- input 0 unchanged;
- input 1 multiplied by 2;
- pi / input 1 when input 1 > 0, otherwise 0;
- (input 2 - 1) / 2.

The consumer FUN_00755340 then computes:

- angle = atan2(local_60, -local_50);
- an optional angular multiplier when the stored fourth field is non-zero and
  abs(angle) is strictly below the stored doubled width;
- planar ratio = (local_50² / (local_60² + local_50²))⁴;
- final factor = angular multiplier ×
  (1 - (1 - planar ratio) × stored amplitude).

The x87 call at FUN_00900b10 is the cosine operation reached by the instruction
stream; the atan2 ordering is verified directly from the x87 stack setup around
FUN_0090285a.

## FUN_007551e0

The helper consumes a separate explicit 3-vector input. For each component it:

1. squares the component;
2. selects one of two 3-vectors according to component sign;
3. adds selected_vector × squared_component into a 3-vector result;
4. writes squared_component × scalar[component] to the auxiliary output and
   negates it only when the component is strictly positive.

The six stored vectors are paired per input component, with exact offsets:

| Input component | <= 0 vector | > 0 vector |
|---:|---:|---:|
| 0 | +0x00 | +0x18 |
| 1 | +0x48 | +0x30 |
| 2 | +0x78 | +0x60 |

The auxiliary scalar coefficients are +0x90, +0x98 and +0xa0.

FUN_00766510 passes local_200 as the helper's input vector. The producer
of local_200 is not established at this boundary, so this phase does not
equate it to the transformed wheel velocity used by FUN_00755340.

## Application boundary

The generated response vectors are subsequently transformed back through the
body pose and passed to FUN_007baa70. This phase records that call boundary but
does not assign an undocumented PhysX force/torque name to the outputs.

## Unresolved

Physical names/units, FUN_007baa70 semantics, and the producer of local_200
remain explicit next targets.
