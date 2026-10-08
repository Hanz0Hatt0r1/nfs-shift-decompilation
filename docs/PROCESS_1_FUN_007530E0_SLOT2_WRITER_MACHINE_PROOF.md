# Process 1 — `FUN_007530e0` slot-2 writer machine proof

## Result

The P1.3 absolute writer search now has one positive result.

`FUN_007530e0` is the direct PC-retail writer for the `HDVehicle+0x1e38` field consumed by the slot-2 `FUN_00755950` path.

This proof assigns no throttle/brake/steering, suspension, force, or unit semantics. It closes only receiver identity and exact scalar algebra.

## Consumer target

`SHIFT.Fun00755950AbsoluteConsumedFieldMachineProof/1` normalizes the four `runtime+0x538` reads to:

```text
slot 0 -> HDVehicle+0x938
slot 1 -> HDVehicle+0x13b8
slot 2 -> HDVehicle+0x1e38
slot 3 -> HDVehicle+0x28b8
```

The target here is slot 2, `HDVehicle+0x1e38`, width `f64`.

## Writer body

Retail `FUN_007530e0` is a small one-argument receiver helper:

```text
0x007530e3  fld   qword [ebp+0x8]       ; x
0x007530e8  fsub  qword [ecx+0x2e10]
0x007530f0  fstp  qword [ecx+0x2e10]
0x007530f6  fmul  qword [ecx+0x2e18]
0x007530fc  fadd  qword [ecx+0x1e38]
0x00753102  fstp  qword [ecx+0x1e38]
0x00753109  ret   0x8
```

Therefore, preserving the retail x87 operation order:

```text
old_reference = old(HDVehicle+0x2e10)
old_target    = old(HDVehicle+0x1e38)
scale         = HDVehicle+0x2e18

HDVehicle+0x2e10 = x
HDVehicle+0x1e38 = old_target + (x - old_reference) * scale
```

## Receiver proof

A complete PE disassembly finds exactly one direct call to `FUN_007530e0`:

```text
0x0076ce7b  call FUN_007530e0
```

It is inside `FUN_0076b280`.

The existing `SHIFT.BMWOffset33bStoreProvenance/1` contract already proves the source-backed HDVehicle identity for `FUN_0076b280` entry `ECX`. Machine code then keeps that exact root in `ESI`:

```text
0x0076b2c9  ESI = ECX
...
0x0076ce5e  ECX = ESI
0x0076ce7b  call FUN_007530e0
```

So the helper receiver is the same HDVehicle root. The store at helper `receiver+0x1e38` is therefore the exact absolute field consumed by slot 2, not a numeric-offset collision on another object.

## Argument producer

`FUN_0076b280` uses `EBX` as an anchor to the original incoming stack before its aligned local frame is built:

```text
0x0076b280  push ebx
0x0076b281  EBX = ESP
```

At the sole writer call it loads:

```text
0x0076ce56  EAX = [EBX+0x8]
```

That is the first physical stack argument to `FUN_0076b280`. Retail computes the helper argument as:

```text
0x0076ce66  fild  dword [eax+0xf1c]
0x0076ce6c  fmul  qword [eax+0xf10]
0x0076ce72  fadd  qword [eax+0xf08]
0x0076ce78  fstp  qword [esp]
```

Thus:

```text
x = f64([source+0xf08])
  + f64(int32([source+0xf1c])) * f64([source+0xf10])
```

where `source` is the first physical stack argument of `FUN_0076b280`.

The owner and higher-level meaning of that source object are deliberately still open.

## P1.3 gate

```text
slot-2 absolute writer identified       = true
same-HDVehicle receiver proven          = true
writer scalar formula proven            = true
explicit argument formula proven        = true
source argument owner proven            = false
retail input/control provenance proven  = false
P1.3 complete                           = false
provider count                          = 7
```

## NEXT_STEP

Trace the first physical stack argument of `FUN_0076b280` to its exact PC-retail owner, then trace the producers of `+0xf08/+0xf10/+0xf1c`. Only an exact value-transfer chain may promote this writer into a retail control producer.
