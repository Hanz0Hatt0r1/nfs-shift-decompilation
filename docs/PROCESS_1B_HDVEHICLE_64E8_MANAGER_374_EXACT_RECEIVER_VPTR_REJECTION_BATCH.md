# Process 1B — Participants Manager `+0x374` exact-receiver vptr rejection batch

## Scope

This slice adjudicates seven sites from the corrected 20-site literal `[base+0x374]` worklist. Every rejection is based on exact retail machine receiver identity: either the receiver itself receives a concrete vptr before the store, or the receiver is recovered through an exact owner-field/constructor chain.

The Participants Manager root vptr installed by `FUN_00488dc0` is `0x00ab9190`. No semantic class name is needed for the negative proofs below.

## Rejected receivers

- `0x0074874b` / `FUN_00748280`: entry receiver is preserved in `ESI`; `0x007482b2` installs vptr `0x00b07938`, which remains installed through the `+0x374` store.
- `0x008169c3` / `FUN_008167f0`: constructor vptr sequence ends at `0x00816825 [ESI]=0x00b16158`, then the same receiver reaches the `+0x374` store.
- `0x00816c9c` / `FUN_00816c70`: the caller obtains `[owner+0x56c]` through `FUN_0080b8f0`. That exact owner field is populated by a `0x390` allocation passed to `FUN_008167f0`, so the method receiver is the `0x00b16158` object above, not the manager root.
- `0x00833972` / `FUN_00833760`: the receiver's final installed vptr is `0x00b190a8`.
- `0x00844343` / `FUN_00844320`: `0x0084432b` installs `0x00b190a8` on the exact receiver before the store.
- `0x00844b67` / `FUN_00844a20`: `0x00844a3a` installs `0x00b190a8` on the exact receiver before the store.
- `0x00d7f104` / `FUN_00d7f040`: `0x00d7f057` installs vptr `0x00ac1fc4` before the zero-initialization run containing `+0x374`.

All four concrete receiver vptr values (`0x00b07938`, `0x00b16158`, `0x00b190a8`, `0x00ac1fc4`) differ from manager vptr `0x00ab9190`.

## Worklist transition

The corrected literal writer frontier changes from:

```text
20 sites / 16 functions
```

to:

```text
13 sites / 9 functions
```

Remaining sites:

```text
0x007c0fa0
0x007c1ace
0x00818157
0x008446cb
0x008446e3
0x008446f8
0x00865013
0x0097da09
0x0097daf8
0x0097dc63
0x0097ed06
0x00a38974
0x00a44ac5
```

## Boundaries

This is a receiver-identity rejection batch only. It does not close the remaining literal stores, computed-address manager `+0x374` writers, or the global identity join `manager+0x374 == HDVehicle+0x4330`.

Therefore `0x004b86cf`, P1.3 completion, and provider removal remain fail-closed; external provider count remains 7.
