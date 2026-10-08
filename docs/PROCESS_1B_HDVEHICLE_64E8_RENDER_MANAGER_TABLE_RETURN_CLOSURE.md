# Process 1B — table-only returned render-manager root closure

## Scope

The direct-caller contract left two conditional exact-`EAX` residue functions open because they have no rel32 callers: `FUN_004b7350` and `FUN_004b73c0`. Their only static references are adjacent cells `0x00abed00` and `0x00abed04`.

Retail machine transfer now connects those cells to one exact registered table object.

## Table ownership and registration

`FUN_004b7250` installs table base `0x00abec20` into object field `+0x0`. Within that table:

- `+0xe0` (`0x00abed00`) = `FUN_004b7350`;
- `+0xe4` (`0x00abed04`) = `FUN_004b73c0`.

`FUN_004c2cf0` allocates `0x10` bytes, calls `FUN_004b7250`, and stores the constructed table object at owner `+0x118`.

`FUN_004c65d0` later loads owner `+0x118`, passes it through the service getter at `0x006e8da0`, and calls `FUN_006e8c80`. `FUN_006e8c80` stores that exact object at service `+0x424`, inserts it into service `+0x280`, and publishes the exact same pointer at globals `0x00c0f808` and `0x00c0f7f4`.

## Exact dispatches

`FUN_006f28c0` consumes exact registered global `0x00c0f808` and dispatches the two remaining slots four times:

- `0x006f2933`: table `+0xe4` -> `FUN_004b73c0`;
- `0x006f29aa`: table `+0xe4` -> `FUN_004b73c0`;
- `0x006f2a35`: table `+0xe0` -> `FUN_004b7350`;
- `0x006f2a7c`: table `+0xe0` -> `FUN_004b7350`.

The conditional exact-root `EAX` residue is never consumed as a pointer:

- after `0x006f2933`, control tests `BL` and a later call clobbers `EAX`;
- after `0x006f29aa`, floating-point status is written to `AX` by `FNSTSW`, destroying exact 32-bit identity before integer `EAX` use;
- after `0x006f2a35`, the caller only updates its own state and later overwrites `EAX` with `MOVZX`;
- after `0x006f2a7c`, `FUN_006310c0` is called before the final `MOVZX EAX`, so caller-saved `EAX` is clobbered.

## Adjudication

The two table-only callbacks are no longer an open returned-root consumer frontier. Combined with the earlier direct-caller closure, the conditional exact-root return-residue consumer surface is closed-negative for persistence, forwarding, or indirect dispatch.

This does not close the separate cross-block memory-store alias surface; the merged `SHIFT.PlayerVehicleRenderManagerMemoryEscapeSurface/1` analyzer still needs the exhaustive retail v2 instruction export to be replayed. The manager `+0x374` join, literal `0x004b86cf`, P1.3 completion, and provider removal remain fail-closed. Provider count remains 7.
