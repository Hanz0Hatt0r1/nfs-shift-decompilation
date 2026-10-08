# Process 1 — slot-2 `VehicleLoadData+0x3a0/+0x3a8` bootstrap zero

## Result

The remaining two source fields feeding the proven slot-2 `FUN_007530e0` chain now have exact fresh-construction values:

```text
VehicleLoadData+0x3a0 = f64 0.0
VehicleLoadData+0x3a8 = f64 0.0
```

This is bootstrap provenance only; later runtime/load writers remain open.

## Receiver normalization

`FUN_007c3170(VehicleLoadData)` constructs a nested object at `VehicleLoadData+0x8`:

```text
0x007c31a3  ECX = VehicleLoadData+0x8
0x007c31aa  call FUN_007c0db0
```

Inside `FUN_007c0db0`, `ESI` is that nested receiver. Therefore:

```text
nested+0x398 = VehicleLoadData+0x3a0
nested+0x3a0 = VehicleLoadData+0x3a8
```

The exact stores are:

```text
0x007c11fa  fst qword [ESI+0x398]
0x007c1200  fst qword [ESI+0x3a0]
```

## x87 value proof

Two retained zero lanes are seeded by:

```text
0x007c1087  fldz
0x007c108f  fldz
```

The later initialization sequence uses balanced `FLD`/`FSTP` pairs. The twelve-iteration block at `0x007c1160..0x007c1173` swaps `ST(0)` with `ST(3)` twice per iteration, so it returns the stack ordering after every iteration. `0x007c1175` removes the temporary top value; the subsequent constant loads are again balanced by stores/pops.

Immediately before the target stores:

```text
0x007c11ea  fxch ST(1)
...
0x007c11f8  fxch ST(2)
0x007c11fa  fst qword [ESI+0x398]
0x007c1200  fst qword [ESI+0x3a0]
```

The selected top x87 value is one of the retained `FLDZ` lanes, and neither `FST` changes it. Both target qwords therefore receive `0.0`.

## Join to slot-2 chain

The merged `SHIFT.Fun007530e0Slot2SourceProducer/1` already proves:

```text
VehicleLoadData+0x3a0 -> HDVehicle+0x5238
VehicleLoadData+0x3a8 -> HDVehicle+0x5240
```

So fresh construction also gives:

```text
HDVehicle+0x5238 = 0.0
HDVehicle+0x5240 = 0.0
```

only until a later writer replaces those source fields.

## P1.3 state

```text
VLD+0x3a0 bootstrap writer/value = proven zero
VLD+0x3a8 bootstrap writer/value = proven zero
runtime writers                  = open
HDVehicle+0x64e8 runtime writer  = open
retail input/control provenance  = false
P1.3 complete                    = false
provider count                   = 7
```

## NEXT_STEP

Trace post-construction writers of `VehicleLoadData+0x3a0/+0x3a8` and the first selected `HDVehicle+0x64e8` writer that changes its constructor sentinel `-1`. Bootstrap values must not be frozen as runtime constants.
