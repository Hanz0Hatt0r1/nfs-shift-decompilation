# S6 — `FUN_007682c0` BODY0 `+0x50` destination closure

## Blocker removed

The active provider frontier previously kept `fun_007682c0_delta_consumer`
external because the concrete record receiving the visible `+0x50` application
had not been joined to the retail BMW chassis BODY0 identity.

A fresh audit of the exact PC retail `SHIFT.exe.c` on the project Google Drive
closes that boundary without runtime capture.

## PC retail source authority

Source identity:

```text
SHIFT.exe.c SHA-256
512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9

SHIFT.exe MD5
705af8b420e5eb1e3834ac43d5533c6b
```

The recovered outer path forwards the same HDVehicle receiver through both
physics passes and into the `FUN_007682c0` tail:

```text
SHIFT.exe.c:765666  FUN_0076d100(this,param_3)
SHIFT.exe.c:765669  FUN_0076d100(this,param_3)
SHIFT.exe.c:763047  FUN_00769ef0(this)
SHIFT.exe.c:761492  FUN_007682c0(param_1,local_30,local_18)
```

Inside `FUN_007682c0`, the actual destination is not the call receiver itself:

```text
SHIFT.exe.c:760240
  iVar1 = *(int *)((int)this + 0x33a0)

SHIFT.exe.c:760242-760243
  *(double *)(iVar1 + 0x50) =
      (double)((float)*(double *)(iVar1 + 0x50) +
               (float)(fVar3 * (float10)param_2))
```

The already-positive `SHIFT.BMWBody0VehicleRootBindRelation/1` independently
identifies:

```text
global HDVehicle              = 0x00c13700
HDVehicle+0x33a0              = chassis BODY pointer
0x00c13700 + 0x33a0           = 0x00c16aa0
selected BMW chassis BODY     = BODY0
```

Therefore the visible `FUN_007682c0` scalar application destination is the
retail BMW chassis BODY0 record at offset `+0x50`.

## Native consumption

The native chain now applies the delta internally on the same persistent BODY
byte vector used by the following half-step:

```text
FUN_0076d100 pass tail
  -> typed FUN_007682c0 effect provider
  -> internal BODY0 +0x50 application
  -> FUN_00765470 half-step provider/integration
```

The writer preserves the PC source numeric shape rather than replacing it with a
plain host-double addition:

```text
current f64 -> f32
incoming delta -> f32
f32 + f32
result f32 -> f64 store
```

`motion_read_delta_consumer` remains in the public compatibility structure only
as an optional observer. It is no longer an active correctness/provider
boundary.

## Frontier effect

```text
legacy Phase 699 external providers = 9
current active external providers   = 8
closed provider                     = fun_007682c0_delta_consumer
```

The adjacent `fun_007682c0_effect_provider` remains external. Exact magnitude,
x87/store-reload behavior, complete `FUN_007595d0` input production, and the
remaining provider semantics are not inferred by this closure.

## Xbox 360 recomp scope

The Drive also contains the Xbox 360 recompilation and it may be used to speed
future symbol/structure searches or corroborate behavior. It is not substituted
for the PC proof here: this closure is based on the exact PC retail source plus
existing PC BMW BODY identity evidence.

## Contract

Machine-readable proof:

```text
SHIFT.Fun007682c0Body0DeltaDestination/1
evidence/fun_007682c0_body0_delta_destination.json
```

No original-game execution or new runtime capture is required.
