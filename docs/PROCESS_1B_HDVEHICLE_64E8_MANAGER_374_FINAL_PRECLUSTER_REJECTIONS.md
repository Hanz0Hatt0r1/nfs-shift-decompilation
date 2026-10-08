# Process 1B — final pre-cluster `manager+0x374` literal narrowing

## Scope

Merged `SHIFT.HDVehicle64e8Manager374VptrReceiverRejections/1` reduces the exhaustive literal `[base+0x374]` worklist to five sites. This slice closes one site by payload semantics and explicitly keeps `0x00865013` open after correcting its target-base provenance.

PC retail 1.02 machine transfer is authoritative. Ghidra SQLite is navigation/fingerprint support only.

## `0x00865013` remains open

`FUN_00864c10` does **not** use its ECX receiver as the target base. At `0x00864c67`, `ESI` is loaded from `[EBX+0x8]`, which is the function's first stack argument. The target later executes:

```text
0x00865013 fstp dword ptr [esi+0x374]
```

Its two direct callers push their own `[ebp+0x8]` as that first argument before calls at `0x0085b6f2` and `0x0085c38f`. Although those caller methods belong to a vtable family rooted at `0x00b1d508`, that proves only their `this` identity, not the identity of the separately supplied first argument.

Therefore `0x00865013` remains fail-closed pending exact first-argument provenance.

## `0x0097ed06`

Inside `FUN_0097eacc`, `0x0097ecbe xor ebx,ebx` establishes a zero payload. The target path later copies the destination pointer through `this+0x2f4` and executes:

```text
0x0097ed06 mov [eax+0x374],ebx
```

This is a payload-only negative for the nonzero identity producer question: the site can only write zero, so it cannot install `HDVehicle+0x4330` into `manager+0x374`. Destination identity itself remains unresolved and is not claimed negative.

## Result

The literal worklist becomes four sites:

- `0x00865013`
- `0x0097da09`
- `0x0097daf8`
- `0x0097dc63`

The three `FUN_0097d8c4` sites remain fail-closed pending callback/argument provenance. Computed-address writer forms also remain open. `manager+0x374 -> HDVehicle+0x4330`, literal `0x004b86cf`, P1.3 completion, and provider removal remain blocked. Provider count remains 7.
