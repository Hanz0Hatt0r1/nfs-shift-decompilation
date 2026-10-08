# Process 1A — reject two `+0x4b0` account/service record writers

## BLOCKER

After the FMOD ChannelMusic rejection, six direct-displacement `+0x4b0` candidates remain. Two byte writers are `FUN_005b0af0` at `0x005b0b1b` and `FUN_005b0e60` at `0x005b0ea6`.

## OUTPUT

Both sites are rejected by exact receiver provenance rather than numeric offset equality.

`FUN_005b0e60` has one direct callsite at `0x005b3057`. Retail transfer sets `ECX` with `lea ECX,[ESP+0xb4]` immediately before the call. Its `+0x4b0` byte therefore belongs to a caller stack-local record and cannot be selected `0x2b90` PhysicsParticipant state.

`FUN_005b0af0` has one direct callsite at `0x005b4c00`. Its caller at `0x005b4be0` passes `ESI+0x10`. That caller is an exact vtable entry: slot `0x00adb49c` in `PTR_LAB_00adb440` contains `0x005b4be0`. The recovered constructor/registration surface `FUN_005b1b00` separately allocates `0x4bc` bytes and installs `PTR_LAB_00adb440`. Thus the candidate receives a subobject of this separate vtable-owned record, not the selected PhysicsParticipant root.

The evidence pins both machine call windows, the vtable bytes, and the recovered-source bodies for `FUN_005b0af0`, `FUN_005b0e60`, and `FUN_005b1b00`.

## GATES_CHANGED

- `0x005b0b1b`: **rejected**;
- `0x005b0ea6`: **rejected**;
- unresolved direct-displacement candidates: **4**;
- selected participant runtime `+0x4b0` producer: **open**;
- P1.1a/P1.1: **incomplete**;
- `contact_response` removal: **not authorized**;
- provider count: **7**.

## LIMITS

The rejection does not require assigning a physical meaning to either record. The exact stack-local and separate-vtable receiver roots are sufficient. Remaining direct and computed/alias/indirect/bulk writer surfaces stay open.

## NEXT_STEP

Adjudicate the remaining four direct-displacement `+0x4b0` sites by exact receiver provenance.
