# Process 1 — `FUN_00469ab0` / `manager+0x2a0` frontier

## Result

The candidate mutation at `0x00469b1d` is real, but the root object identity is not.

`FUN_00469ab0` captures its receiver (`ESI=ECX`), forms `ECX=ESI+0x2a0` at `0x00469b17`, and calls `FUN_0057f620` at `0x00469b1d`. The callee reaches a body at `0x0057f626` and operates on receiver fields including `+0x38`, `+0x3c`, `+0x40`, and `+0x114`; it mutates receiver-owned state.

That is enough to prove a mutation of **some** `receiver+0x2a0` subobject. It is not enough to prove that `receiver == FUN_00489ad0()` singleton manager.

## Whole-export exclusions

Using the `SHIFT.GhidraEvidenceDatabase/1` export and the retail image:

- direct inbound call edges to `FUN_00469ab0`: **0**;
- membership in the exported 2,533 heuristic vtable candidates: **absent**;
- literal little-endian occurrences of `0x00469ab0` in the retail PE image: **0**.

These exclusions reject the easy direct-call/vtable/literal-registration joins. They do **not** reject computed indirect dispatch.

## Adjacent-function disambiguation

The adjacent `FUN_00469c00` must not be used to infer the receiver class of `FUN_00469ab0`.

`FUN_00469c00` is slot 0 of vtable candidate `0x00ab6154`. Independently, `FUN_004f11d0` allocates `0x10` bytes and stores `0x00ab6154` at object offset 0. That is a separately evidenced small vtable object. Code adjacency is therefore not an object-identity join.

## Gate impact

No semantic gate changes:

- `manager+0x2a0 == FUN_00469ab0 receiver+0x2a0`: **unproven**;
- `manager+0x374 == HDVehicle+0x4330`: **unproven**;
- selected non-sentinel `HDVehicle+0x64e8` writer: **unproven**;
- retail input/control provenance: **unproven**;
- P1.3: **incomplete**;
- external provider count: **7**.

## Next step

Search computed/registration dispatch capable of reaching `FUN_00469ab0`, or independently join a caller/root alias to the `FUN_00489ad0()` singleton manager. Do not promote the `0x00469b1d` mutation to a manager mutation until that root identity is established.
