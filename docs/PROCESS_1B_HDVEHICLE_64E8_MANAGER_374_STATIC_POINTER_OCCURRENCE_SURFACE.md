# Process 1B — Participants Manager static pointer occurrence surface

## Scope

This slice checks whether the exact Participants Manager singleton root `0x00bc9fc0` is preinitialized anywhere in the PC retail 1.02 PE image as a 32-bit pointer that code could later load indirectly.

## Result

The little-endian byte sequence `c0 9f bc 00` occurs exactly three times in the entire executable. All three occurrences are in `.text` and are the immediate operands of the already-known singleton init/getter/cleanup instructions:

- operand at `0x00489ae4` for instruction `0x00489ae3`;
- operand at `0x00489afb` for instruction `0x00489afa`;
- operand at `0x00a9c5a1` for instruction `0x00a9c5a0`.

There are no occurrences in `.rdata`, `.data`, `.tls`, `.rsrc`, or `.secu`. Therefore the retail image contains no preinitialized exact pointer cell that could be loaded from a table or global as an alternate Participants Manager root.

## Adjudication

The static exact-pointer-cell surface is closed-negative. Together with the direct literal and simple arithmetic scans, this removes direct static tables/globals as an unrelated source of manager root identity.

Runtime-synthesized pointers, externally initialized storage, relocation-derived representations, multi-register arithmetic, and opaque helper-return provenance remain open. The manager `+0x374` join and literal `0x004b86cf` therefore remain fail-closed. Provider count remains 7.
