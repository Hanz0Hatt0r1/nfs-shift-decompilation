# Process 1A — close the literal direct `+0x4b0` writer surface

## BLOCKER

After the Massive secure-parser rejection, only `0x0076019f` remained in the direct-displacement frontier.

## OUTPUT

The Ghidra export missed the enclosing function boundary, but retail machine code shows a normal thiscall method beginning at `0x0075cfb0` with `ESI=ECX`. The candidate is `0x0076019f: fstp qword ptr [ESI+0x4b0]`.

The method identity is exact. Read-only data at `PTR_FUN_00b09a68` starts with:

```text
slot 0 -> 0x0076b100
slot 1 -> 0x0075cfb0
```

`FUN_0076b060` installs this vtable with `*param_1 = &PTR_FUN_00b09a68`. `FUN_0076b130` constructs four instances at `owner+0x400` with stride `0xa80`.

The selected PhysicsParticipant has a different exact identity: constructor `FUN_0072ed20` installs `PTR_FUN_00b070a0` on the separately allocated `0x2b90` participant. Therefore the `0x0076019f` receiver is not the selected PhysicsParticipant even though the method performs genuine physics calculations.

## GATES_CHANGED

- `0x0076019f`: **rejected** by exact vtable identity.
- unresolved literal direct-displacement `+0x4b0` sites: **0**.
- direct-displacement surface: **exhausted**.
- selected participant runtime `+0x4b0` producer: **still open**.
- P1.1a/P1.1: **incomplete**.
- `contact_response` removal: **not authorized**.
- provider count: **7**.

## LIMITS

Closing the direct-displacement surface is not equivalent to proving that no runtime producer exists. Process 1A must now widen to computed-address, escaped-alias, indirect-dispatch and residual bulk-copy writes capable of reaching selected `PhysicsParticipant+0x4b0`.

## NEXT_STEP

Build a fail-closed non-direct writer frontier and adjudicate each alias/computed/indirect/bulk path before P1.1a can close.
