# Process 1B — HDVehicle +0x4330 static pointer occurrence surface

## Scope

This slice checks whether the exact PC-retail `HDVehicle+0x4330` address `0x00c17a30` is preinitialized anywhere in the executable as a 32-bit pointer that could later be loaded indirectly.

## Result

The little-endian byte sequence `30 7a c1 00` occurs exactly four times in the entire PE. All four occurrences are in `.text`, in the already-known wrapper block around `0x00702710..0x007027be`:

- `0x00702715`: `mov ecx,0xc17a30` before `FUN_00771e40`;
- `0x0070274d`: `mov ecx,0xc17a30` before `FUN_00771e40`;
- `0x00702776`: `mov ecx,0xc17a30` before `FUN_00772350`;
- `0x007027ac`: `mov ecx,0xc17a30` before `FUN_00771e40`.

There are no exact pointer cells in `.rdata`, `.data`, `.tls`, `.rsrc`, or `.secu`. Therefore no alternate static table/global source can load a preinitialized exact `HDVehicle+0x4330` pointer.

## Adjudication

The static exact-pointer-cell surface for `HDVehicle+0x4330` is closed-negative. The four raw occurrences are the already-bounded code immediates and do not introduce new aliases.

Runtime-derived, copied, externally initialized, computed, or differently represented aliases remain open. Global non-literal `HDVehicle+0x64e8` writer closure and the manager `+0x374` join therefore remain fail-closed. Provider count remains 7.
