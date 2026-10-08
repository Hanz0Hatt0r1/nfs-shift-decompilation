# Process 1B — render-manager same-basic-block escape surface

## Scope

This slice examines every direct machine load of the exact outer-object global `0x00bc185c` in the retail `.text` section. It propagates exact pointer identity only through straight-line register copies inside the same basic block and stops at the first call, branch, jump, or return.

## Result

There are 112 direct exact-global loads in retail machine code:

- `EAX`: 43
- `ECX`: 47
- `EDX`: 5
- `EBX`: 4
- `ESI`: 10
- `EDI`: 3

Exact identity is propagated through `MOV reg,reg` and zero-offset `LEA reg,[alias+0]`. Before the first control-flow/call boundary, the scan finds:

- 0 pushes of the exact outer pointer as a data argument;
- 0 stores of the exact outer pointer into stack locals;
- 0 stores of the exact outer pointer into object/global memory.

Thus no direct exact-global load creates a persistent exact outer-object alias in the same basic block.

## Limits

This does not close aliases created after a branch merge, inside a callee, from a returned pointer, or by reconstructing the root from an interface/subobject. Derived pointers such as `outer+4`, `outer+0x780`, and `outer+0xc4c` are intentionally not promoted back to exact-root identity.

The manager `+0x374` join, literal `0x004b86cf`, P1.3 completion, and provider removal remain fail-closed. Provider count remains 7.
