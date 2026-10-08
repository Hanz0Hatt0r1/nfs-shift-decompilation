# Process 1B — manager+0x374 getter register alias surface

## Scope

This slice follows exact `FUN_00489ad0` returns that are copied immediately into a non-`ECX` general-purpose register. Direct `ECX` forwarding is owned by the previously merged exact-root direct-callee contract; immediate stack-local aliases are owned by the getter-local contract. PC retail 1.02 machine transfer is authoritative.

## Result

There are exactly ten immediate non-`ECX` register-alias callsites. While the alias still denotes the Participants Manager root, every site is restricted to the `+0x2a0`, `+0x2c4`, `+0x2d4`, `+0x2d8`, or `+0x2fc` domains. None writes `manager+0x374`.

Two cases need explicit disambiguation. In `FUN_004bad20`, `ESI` initially carries the manager root, but before later accesses around `+0x2174..+0x21ac` it is replaced by a selected entry obtained from `manager+0x2d8` or `manager+0x2a0`; those offsets are therefore entry-relative, not manager-relative. In `FUN_0051df70`, the root is retained in `EDX` and later `[ebp-0x4]`, but the call to `FUN_0051cb90` uses an output slot in `ECX`; that four-byte helper ignores `EDX`, so the manager root is not forwarded.

The audit also found zero immediate object-field stores of the live getter return.

## Adjudication

Immediate non-`ECX` register aliases and immediate object-field stores are closed-negative as new producers of `manager+0x374`. Delayed/reconstructed aliases outside this class remain open. The last literal `0x004b86cf` stays fail-closed, P1.3 remains incomplete, and provider count remains 7.
