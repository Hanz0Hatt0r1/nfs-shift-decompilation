# Process 1B — Participants Manager vslot +0x0c dispatch closure

## Scope

This slice consumes the merged `SHIFT.HDVehicle64e8Manager374VSlot0cIndirectFrontier/1` together with the older exhaustive retail `SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/2`.

The target class is the exact `FUN_0045ef50` outer object stored at `DAT_00bc185c`, whose primary vtable is `0x00ab5644`. Slot `+0x0c` is `FUN_0045b130`.

## Retail receiver-transfer surface

The exhaustive receiver-transfer analysis covers 95 exact READ xrefs across 80 functions and proves only three indirect first-hop calls with the exact manager object as receiver.

Retail machine code resolves those three calls as:

- `0x0056bcf2`: `MOV EAX,[ESI]`; `MOV EDX,[EAX+0x1c]`; `CALL EDX`.
- `0x0056bd09`: `MOV EAX,[ESI]`; `MOV EDX,[EAX+0x20]`; `CALL EDX`.
- `0x0056bd59`: `MOV EAX,[ECX]`; `MOV EDX,[EAX+0x1c]`; `CALL EDX`.

Therefore the exact-manager first-hop indirect surface reaches only slots `+0x1c` and `+0x20`. It never reaches slot `+0x0c`.

The synthetic slot offsets used by the historical unit-test fixture are not promoted as retail evidence; the machine instructions above are authoritative.

## Adjudication

`FUN_0045b130` is closed as an alternate Participants Manager-root producer for the exhaustive exact `DAT_00bc185c` first-hop dispatch surface. Direct calls were already zero and direct exact-global slot dispatch was already closed by the upstream frontier.

This does **not** close runtime-created/copied aliases of the outer object that might bypass the exact-global first-hop analysis. Those aliases remain the next fail-closed frontier. The manager `+0x374` to `HDVehicle+0x4330` join, literal `0x004b86cf`, P1.3 completion and provider removal remain open. Provider count stays 7.
