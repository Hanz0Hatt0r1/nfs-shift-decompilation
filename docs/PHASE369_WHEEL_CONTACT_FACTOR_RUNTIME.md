# Phase 369 — wheel contact-angle factor runtime

Phase 369 closes the small helper embedded in FUN_00765c40.

## FUN_00758ad0

The instruction stream performs:

1. absolute value of the input;
2. subtracts DAT_00c10f94 multiplied by 0.5;
3. clamps the result to [0, 6] through FUN_00715a60;
4. multiplies by 3.1415927410125732 and divides by 6.0;
5. calls FUN_00900b10, whose implementation reaches the x87 FCOS instruction;
6. multiplies the cosine by 0.02500000037252903;
7. adds 0.9750000238418579;
8. rounds the final value through the 32-bit float store used by the function.

The threshold at DAT_00c10f94 remains a runtime input.

## FUN_00765c40 four-wheel storage

When its external gate is active, FUN_00765c40 computes one scalar input per
wheel and stores the result at +0xa78 + i*0x150. The value at +0xa70 + i*0x150
receives DAT_00c12c38 when DAT_00c12c3c equals DAT_00c12c38, otherwise zero.

When the helper is externally disabled, the wheel factor is explicitly one.

This phase does not infer what physical property the factor represents. It only
recovers the exact arithmetic and storage topology.
