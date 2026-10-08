# Process 1 — reject `FUN_00791020` as the `HDVehicle+0x938` writer

## Result

`FUN_00791020` is **not** the writer for the slot-0 field consumed by `FUN_00755950`.

The earlier candidate existed only because both sites used the literal numeric offset `+0x938`. PC-retail machine code now closes the receiver/base chain and proves that the two offsets are relative to different objects.

## Machine owner chain

The manager record constructor path stores a constructed participant pointer at record offset zero:

```text
FUN_007125e0
0x0071263e  [manager_record+0x0] = constructed participant pointer
```

The participant constructor is `FUN_0072ed20`; its inline `+0x340` child is constructed at `0x0072ed48`.

When `FUN_0074ddb0` selects the manager record, retail writes:

```text
0x0074dde6  [0x00c10b34] = manager_record
```

The selected HDVehicle init path subsequently loads that exact global and passes it as `FUN_0076df50 param_1`:

```text
0x0074dabe  ECX = [0x00c10b34]
...
0x0074dadf  call FUN_0076df50
```

Inside `FUN_0076df50`, the same value is retained at:

```text
0x0076e157  [HDVehicle+0x3fe8] = param_1
```

This joins the local setup record to the already-established owner contract:

```text
HDVehicle+0x3fe8 = manager_record
actual_participant = *([HDVehicle+0x3fe8])
```

## `FUN_00791020` receiver

`FUN_0074e1a0` receives that manager record and performs:

```text
0x0074e2b6  ECX = [manager_record+0x0]
0x0074e2b8  ECX += 0x340
0x0074e2be  call FUN_00799ff0
```

`FUN_00799ff0` preserves the receiver into `FUN_00791020`.

Therefore:

```text
FUN_00791020 receiver = actual_participant+0x340
```

Its `receiver+0x938` writes normalize to:

```text
actual_participant + 0x340 + 0x938
= actual_participant + 0xc78
```

They do **not** normalize to `HDVehicle+0x938`.

## Consumer comparison

The positive consumer proof remains:

```text
FUN_00755950 receiver = HDVehicle+0x400+slot*0xa80
read receiver+0x538
```

For slot zero this is:

```text
HDVehicle+0x938
```

So the candidate and consumer bases differ:

```text
FUN_00791020  -> actual_participant+0xc78
FUN_00755950  -> HDVehicle+0x938
```

A matching numeric `+0x938` is not object identity.

## P1.3 gate

```text
manager record -> HDVehicle+0x3fe8 join complete = true
FUN_00791020 receiver resolved                    = actual_participant+0x340
FUN_00791020 rejected as slot-0 writer            = true
retail input/control provenance                    = false
P1.3 complete                                      = false
provider count                                     = 7
```

No throttle/brake/steering, suspension, force, or class-name semantics are inferred here.

## NEXT_STEP

Continue the writer search using the **absolute HDVehicle fields** proven by `SHIFT.Fun00755950AbsoluteConsumedFieldMachineProof/1`:

```text
HDVehicle+0x938
HDVehicle+0x13b8
HDVehicle+0x1e38
HDVehicle+0x28b8
```

Every future candidate must prove the same HDVehicle receiver/base before its value producer can be promoted into P1.3.
