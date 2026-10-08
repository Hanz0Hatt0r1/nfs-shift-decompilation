# Process 1 — `FUN_007530e0` slot-2 writer machine proof

## Result

`FUN_007530e0` is the direct PC-retail writer for the `HDVehicle+0x1e38` field consumed by the slot-2 `FUN_00755950` path. The receiver, writer algebra, caller argument owner, and absolute source fields are all machine-proven.

No throttle/brake/steering, suspension, force, unit, or class semantics are assigned.

## Consumer target

`SHIFT.Fun00755950AbsoluteConsumedFieldMachineProof/1` normalizes the four `runtime+0x538` reads to:

```text
slot 0 -> HDVehicle+0x938
slot 1 -> HDVehicle+0x13b8
slot 2 -> HDVehicle+0x1e38
slot 3 -> HDVehicle+0x28b8
```

This proof closes slot 2.

## Exact writer

Retail `FUN_007530e0` executes:

```text
0x007530e3  fld   qword [ebp+0x8]
0x007530e8  fsub  qword [ecx+0x2e10]
0x007530f0  fstp  qword [ecx+0x2e10]
0x007530f6  fmul  qword [ecx+0x2e18]
0x007530fc  fadd  qword [ecx+0x1e38]
0x00753102  fstp  qword [ecx+0x1e38]
```

Therefore:

```text
HDVehicle+0x2e10 = x
HDVehicle+0x1e38 = old(HDVehicle+0x1e38)
                  + (x - old(HDVehicle+0x2e10)) * HDVehicle+0x2e18
```

A full PE disassembly contains exactly one direct `call 0x7530e0`, at `0x0076ce7b` inside `FUN_0076b280`.

## Same-HDVehicle receiver proof

`SHIFT.BMWOffset33bStoreProvenance/1` already proves that `FUN_0076b280` entry `ECX` is HDVehicle. Retail preserves that root:

```text
0x0076b2c9  ESI = ECX
...
0x0076ce5e  ECX = ESI
0x0076ce7b  call FUN_007530e0
```

Thus `FUN_007530e0 receiver == HDVehicle`, so the `+0x1e38` store is the exact slot-2 consumer field rather than an offset collision on another object.

## Source owner

The only call to `FUN_0076b280` is inside `FUN_0076df50`, whose entry receiver is HDVehicle. Before the call:

```text
0x0076e1c1  EBX = HDVehicle+0x4330
...
0x0076e266  EAX = [HDVehicle+0x66b4]
0x0076e26c  push EAX
0x0076e26d  push EBX
0x0076e26e  ECX = HDVehicle
0x0076e270  call FUN_0076b280
```

Therefore the first physical stack argument of `FUN_0076b280` is exactly:

```text
HDVehicle+0x4330
```

and the second is `*(HDVehicle+0x66b4)`.

## Exact argument formula

`FUN_0076b280` anchors the incoming call frame in `EBX` at `0x0076b281`. At the writer call:

```text
0x0076ce56  EAX = [EBX+0x8] = HDVehicle+0x4330
0x0076ce66  fild  dword [eax+0xf1c]
0x0076ce6c  fmul  qword [eax+0xf10]
0x0076ce72  fadd  qword [eax+0xf08]
0x0076ce78  fstp  qword [esp]
0x0076ce7b  call FUN_007530e0
```

Absolute source fields are therefore:

```text
HDVehicle+0x4330 + 0xf08 = HDVehicle+0x5238  (f64)
HDVehicle+0x4330 + 0xf10 = HDVehicle+0x5240  (f64)
HDVehicle+0x4330 + 0xf1c = HDVehicle+0x524c  (int32)
```

and:

```text
x = f64(HDVehicle+0x5238)
  + f64(int32(HDVehicle+0x524c)) * f64(HDVehicle+0x5240)
```

Their value producers remain open; their control meaning is not inferred.

## P1.3 gate

```text
slot-2 absolute writer identified       = true
same-HDVehicle receiver proven          = true
writer scalar formula proven            = true
caller source owner proven              = true
absolute source fields proven           = +0x5238/+0x5240/+0x524c
source field value producers proven     = false
retail input/control provenance proven  = false
P1.3 complete                           = false
provider count                          = 7
```

## NEXT_STEP

Trace the exact PC-retail writers/value producers of `HDVehicle+0x5238`, `HDVehicle+0x5240`, and `HDVehicle+0x524c`. Only an exact value-transfer chain may promote them into retail control provenance.
