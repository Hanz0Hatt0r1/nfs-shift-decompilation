# Process 1A / P1.3A — `FUN_00765c40` local-array callee machine closure

## Scope

The merged post-derived inventory classifies four later `FUN_00765c40` pointer families as HDVehicle-local arrays rather than selected wheel roots:

```text
HDVehicle+0x3430
HDVehicle+0x35c8
HDVehicle+0x35f8
HDVehicle+0x36e0
```

Their callee-facing lifetimes were intentionally left open. This closure verifies those lifetimes directly against PC retail 1.02 `SHIFT.exe` and closes only this bounded class.

## Authority

The verifier hash-locks the retail executable, caller materialization/call windows, rel32 call targets, and complete raw machine bodies for:

- `FUN_007afd20` — 49 bytes;
- `FUN_007aefb0` — 83 bytes;
- `FUN_00747b90` — 36 bytes;
- `FUN_007baa70` — 121 bytes.

## `HDVehicle+0x3430`

The 12-iteration loop advances this cursor by `0x18`. It is passed as `param_2` to `FUN_007afd20`, which forwards it once as the data-vector input to `FUN_007aefb0`.

`FUN_007aefb0` reads only qwords `+0x0/+0x8/+0x10` from that input and writes three qwords to a separate output pointer. It has no calls and does not store/reconstruct the input pointer.

## `HDVehicle+0x35c8`

The 12-iteration loop advances this receiver by `0x4` and calls `FUN_007baa70` with the exact cursor in `ECX`.

The complete callee body has no direct calls and writes scalar qwords only at receiver offsets:

```text
+0x48 +0x50 +0x58 +0x60 +0x68 +0x70
```

Across all 12 cursor positions, the write span is `HDVehicle+0x3610..+0x3664`, far outside slot0 `+0x938..+0x93f` and slot1 `+0x13b8..+0x13bf`. The receiver pointer itself is not persisted or transformed back toward a wheel root.

## `HDVehicle+0x35f8`

The 12-iteration cursor advances by `0x8`. The machine path uses it directly at `0x0076618b` as the destination of `FST QWORD PTR [EDX]` after loading `EDX=[EBP-0x14]`.

No callee receives this cursor; there is therefore no callee-created escape or wheel-root reconstruction on this bounded path.

## `HDVehicle+0x36e0`

The four-iteration cursor advances by `0x18`.

Two distinct data uses are bounded:

1. `cursor-0x2b0` maps exactly back into `HDVehicle+0x3430 + iteration*0x18` and is passed as data input to `FUN_007aefb0`;
2. the exact `+0x36e0` cursor is passed in `EDX` to `FUN_00747b90`, which reads qwords `+0x0/+0x8/+0x10` and writes only to a separate stack/output vector.

The later `FUN_007baa70` call in the same loop receives the chassis BODY pointer loaded from `HDVehicle+0x33a0`, not the `+0x36e0` cursor.

## Gate

```text
FUN_00765c40 local-array callee lifetimes complete = true
local-array pointer escape found                    = false
local-array wheel-root reconstruction found         = false
local-array selected slot writer found              = false

other derived aliases ruled out                     = false
runtime-generated selected-wheel stores ruled out   = false
callbacks / indirect entry ruled out                = false
stored-or-escaped aliases ruled out                 = false
slot0 complete                                      = false
slot1 complete                                      = false
P1.3 complete                                       = false
provider count                                      = 7
```

## Reproduce

```bash
python3 tools/ghidra/analyze_p1a_fun00765c40_local_array_callee_machine.py \
  /path/to/SHIFT.exe \
  --output evidence/p1a_p13a_fun00765c40_local_array_callee_machine_closure.json
```

The verifier fails closed on retail SHA drift, upstream array-geometry drift, any caller byte/call-target drift, or any change to the complete bounded callee bodies.

## Next step

Compose this result with the `FUN_00765c40` derived-alias handoff. Then consume the merged direct 16-carrier/direct-callee bulk-opcode absence and trace the two unresolved `FUN_00770e80` indirect callsites plus runtime-generated/copied selected-wheel pointers.
