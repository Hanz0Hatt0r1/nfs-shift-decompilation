# Process 1B — final pre-cluster `manager+0x374` literal rejections

## Scope

Merged `SHIFT.HDVehicle64e8Manager374VptrReceiverRejections/1` reduces the exhaustive literal `[base+0x374]` writer worklist to five sites. This slice closes two more without inferring identity from the shared numeric displacement.

PC retail 1.02 machine transfer is authoritative. Ghidra SQLite is navigation/fingerprint support only.

## `0x00865013`

`FUN_00864c10` captures its exact receiver and eventually executes `fstp dword ptr [receiver+0x374]` at `0x00865013`.

The exact receiver family is independently identified by vptr `0x00b1d508`, installed at `0x0085afda`. The two direct calls to `FUN_00864c10` are `0x0085b6f2` and `0x0085c38f`; their enclosing methods occupy adjacent vtable cells `0x00b1d520 -> 0x0085b6e0` and `0x00b1d524 -> 0x0085c370` under that same vtable. This receiver is therefore not the Participants Manager root (`0x00ab9190`) or embedded `manager+0x20` subobject (`0x00ab916c`).

## `0x0097ed06`

Inside `FUN_0097eacc`, `0x0097ecbe xor ebx,ebx` establishes a zero payload. The target path later copies the destination pointer through `this+0x2f4` and executes `0x0097ed06 mov [eax+0x374],ebx`.

This site does not require destination identity adjudication: it can only write zero, so it cannot install `HDVehicle+0x4330` into `manager+0x374`.

## Result

The literal worklist becomes three sites, all in `FUN_0097d8c4`:

- `0x0097da09`
- `0x0097daf8`
- `0x0097dc63`

Those three remain fail-closed pending exact callback/argument receiver provenance. Computed-address writer forms also remain open. `manager+0x374 -> HDVehicle+0x4330`, literal `0x004b86cf`, P1.3 completion, and provider removal remain blocked. Provider count remains 7.
