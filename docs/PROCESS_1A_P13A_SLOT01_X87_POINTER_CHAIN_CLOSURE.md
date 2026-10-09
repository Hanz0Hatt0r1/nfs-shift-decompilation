# Process 1A / P1.3A — final shallow x87 semantic closure

After the first two merged x87 tranches, four `FLDZ -> FST/FSTP` candidates remain. Direct PC-retail machine transfer rejects all four.

## Guarded optional output

`FUN_0075c0d0` is statically reachable below `FUN_007b1790`, but the bounded P1A caller pushes literal zero for the relevant optional output. `FUN_007b1790` tests that pointer and skips the call when null, so the candidate x87 store cannot execute on this path.

## Stack-output vectors

`FUN_007682c0` passes four explicit stack-local output pointers (`EBP-0x8/-0xc/-0x18/-0x24`) to `FUN_0075ada0`. Its zero branch writes only through those outputs.

## Separate heap object graph

`FUN_0076df50` captures the HDVehicle root, allocates exactly `0x60` bytes, constructs the allocation through `FUN_007b3070`, and stores the returned pointer at `HDVehicle+0x339c`. The constructor installs exact vptr `0x00b0cd90`.

`FUN_00770e80 -> FUN_007b8810 -> FUN_007b8630` follows that pointer and nested children before the x87 stores. `FUN_007b8630 -> FUN_007b8260 -> FUN_007b7840` remains inside the same separately allocated graph. None of these stores target inline `HDVehicle+0x938` or `HDVehicle+0x13b8`.

## Gate

```text
x87 frontier candidates                 = 18
resolved before this tranche            = 14
resolved here                            = 4
x87 zero-init semantics complete        = true
selected slot0/slot1 x87 writer found   = false
SSE/vector copy-init complete           = false
deeper direct aliases ruled out         = false
indirect/callback aliases ruled out      = false
slot0 complete                           = false
slot1 complete                           = false
P1.3 complete                            = false
provider count                           = 7
```

Next: bound shallow SSE/vector copy and zero-initialization; only then widen exact selected-HDVehicle-derived deeper/indirect aliases.
