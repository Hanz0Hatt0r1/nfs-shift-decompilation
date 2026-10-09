# Process 1B: reject the direct computed `+0x374` writer

## Scope

`SHIFT.HDVehicle64e8Manager374ComputedAddressUseClassification/1` leaves exactly one materializer that directly writes through the computed pointer: `0x00985bd3` in `FUN_00985bc0`.

## Exact receiver chain

The owning static descriptor at `0x00b98c88` installs callback `0x0093fa0f` at `0x00b98cb0` and records a `0x76c` descriptor size field. The callback receives an external state argument, subtracts `0x1c` with a null mask, and enters `FUN_0093f4d3`.

Machine transfer then remains exact:

```text
0x0093f4ea  ESI = ECX
0x0093f5d4  EBX = ESI + 0x12c
0x0093f5df  ECX = EBX
0x0093f5e4  call FUN_00986a67
0x00986a6c  EBX = ECX
...
0x00986b86  ECX = EBX
0x00986b88  call FUN_00985bc0
0x00985bc6  ESI = ECX
0x00985bd3  ESI += 0x374
```

Whole-text direct-call inventory gives one direct caller for `FUN_00986a67` and one direct caller for `FUN_00985bc0`, exactly the two sites above. Thus the write-through receiver is the descriptor-owned embedded state `callback_state + 0x12c`, not Participants Manager root/subobject.

The source path `lib/sfx/foreverb/aSfxDsp.cpp` is supporting context only; descriptor ownership and machine transfer adjudicate identity.

## Result

The unique direct write-through computed `+0x374` candidate cannot write Participants Manager `+0x374`. The computed runtime frontier reduces from 19 to 18 paths: one returned-pointer escape plus 17 callee-forwarding paths.

The final `0x004b86cf` candidate, P1.3 completion and provider removal remain fail-closed. Provider count remains 7.
