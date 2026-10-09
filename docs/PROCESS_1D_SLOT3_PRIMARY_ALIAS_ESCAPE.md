# Process 1D — slot3 primary selected-wheel alias escape

## Result

The primary `FUN_00758b50` per-wheel loop now has an exact retail-machine one-hop alias proof.

At entry, `FUN_00758b50` preserves the selected `HDVehicle` root in `EDI`:

```text
0x00758b98  EDI = entry ECX = HDVehicle
0x00758bb4  ESI = HDVehicle + 0x848
...
0x00758ccf  ECX = ESI - 0x448
0x00758d6b  call FUN_00755950
0x00758d7d  ESI += 0xa80
```

Therefore the receiver at `0x00758d6b` is exactly:

```text
HDVehicle + 0x400 + slot*0xa80
```

For slot3 this is `HDVehicle+0x2380`; `FUN_00755950` then reads local `+0x538`, which is selected `HDVehicle+0x28b8`.

## Other calls in the primary wheel body

The other direct calls do not receive the selected wheel root:

- `0x00758be6 -> FUN_007aefb0`: external/body object `+0xd4`;
- `0x00758bf2 -> FUN_00753590`: stack local `EBP-0x80`;
- `0x00758c1f -> FUN_007aefb0`: `[HDVehicle+0x33a0]+0xd4`;
- `0x00758c34 -> FUN_00753590`: stack local `EBP-0x80`;
- `0x00758c71 -> __CIsqrt`: scalar runtime helper, not a wheel-root thiscall receiver.

Thus the exact selected wheel root has one direct target in this primary per-wheel body: `FUN_00755950`.

## Consumer escape boundary

`FUN_00755950` copies its receiver to `EDX` and reads the target field:

```text
0x00755956  EDX = ECX
0x00755958  read f64 [EDX+0x538]
```

Its direct writes are only:

```text
[EDX+0x528]
[EDX+0x530]
[EDX+0x548]
```

None overlaps `[+0x538,+0x540)`.

The function has one direct callee:

```text
0x00755964  ECX = EDX + 0x80
0x00755983  call FUN_007555b0
```

So the exact wheel root itself does not escape to that callee; only the `wheel+0x80` child receiver does.

## Gate

```text
primary-loop exact wheel-root one-hop forwarding complete = true
primary-loop exact wheel-root only direct target            = FUN_00755950
FUN_00755950 target +0x538 field read-only                  = true
FUN_00755950 exact wheel root escapes to direct callee       = false

global interprocedural wheel-alias surface complete         = false
escaped/stored alias surface complete                        = false
slot3 writer provenance                                      = false
P1.3D complete                                               = false
provider count                                               = 7
```

This is intentionally not a global alias theorem. Other lifecycle functions, stored aliases, indirect calls, callbacks, custom copies and deeper carriers remain open.

## Reproduction

```bash
python3 tools/ghidra/verify_p1d_slot3_primary_alias_escape.py \
  /path/to/SHIFT.exe \
  --output out/p1d_slot3_primary_alias_escape.json
```

The verifier requires the authoritative PC retail 1.02 executable SHA-256 and checks exact machine byte windows plus every relevant rel32 call target.

## Next step

Trace selected-wheel aliases from the other proven wheel lifecycle functions, especially aliases that are stored or forwarded across a function boundary. Only a callee or copy/init path that receives exact selected-HDVehicle-derived provenance may be promoted for target-byte analysis.
