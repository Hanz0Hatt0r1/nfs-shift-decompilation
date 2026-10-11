# Process 1B: HDVehicle+0x4330 base/index direct-callee provenance

## Result

The five direct-call argument escapes discovered by the implicit-stack carrier scan are classified on authoritative PC retail 1.02 machine paths. All **5/5** are consumed as string/data, with **0** bounded `CALL/JMP` dispatches through the escaped value.

- `0x004b1c1b -> 0x006329e0`: byte-scan to NUL, then source+length to `0x00631230` for copy.
- `0x00d74308 -> 0x006329e0`: same string-scan/copy path.
- `0x004cd46b -> 0x00632c70`: byte-scan to NUL and direct string-copy helpers `0x00631290` / `0x00631740`.
- `0x005f51ed -> 0x00403c90`: escaped value is `%s` data for exact literal `0x00ac03c4 == "%s="`; formatter path is direct.
- `0x008d1960 -> 0x008b4c70`: reaches `0x009f1df0`, which byte-scans to NUL, allocates a ref-counted string buffer and copies the bytes.

## Aggregate effect

`SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/13` increases bounded coverage classes from **16 to 17**. The five implicit-stack escapes are no longer unclassified callable-target candidates in this bounded callee surface. Exact carrier hits remain **0**.

## Boundary

Global incoming indirect entry remains open. Still unresolved: inter-block/phi carry; aliases and heap/runtime mutation; runtime-generated/copied function pointers; unrelated indirect target classes; the `manager+0x374 -> HDVehicle+0x4330` identity join; final `0x004b86cf` / slot2; aggregate P1.3. Provider count remains **7**.

## Next

Bound inter-block carry for base/index writable-data provenance, then continue remaining alias/runtime target classes before considering the global indirect-entry gate.
