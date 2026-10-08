# Process 1B — HDVehicle root literal persistence surface

## Scope

This slice asks whether any direct literal materialization of the fixed HDVehicle root `0x00c13700` persists the exact root into memory or the stack before the first call/control-flow boundary.

## Retail machine inventory

The whole PE contains 71 raw little-endian occurrences of `0x00c13700`. Machine decoding classifies 69 of them as `MOV full_gpr,0x00c13700` pointer-value seeds; the remaining two are direct numeric memory operands.

For each of the 69 literal seeds, the bounded tracker follows exact full-register copies and zero-displacement LEA until the first call, jump, return, or alias-killing register write.

Result:

- 69 exact literal-root seeds;
- 61 seeds reach a direct call boundary;
- 0 `MOV [memory], exact_root` sinks;
- 0 post-seed `push exact_root` sinks;
- 0 same-block persistent escapes.

## Adjudication

Direct literal HDVehicle-root materialization does not create a persistent same-block memory or stack alias before the first opaque/control boundary.

This does not adjudicate what the 61 reached callees may do with the exact root. It also does not replace the already merged affine/parser/escaped-root closures for specific `root -> +0x4330` paths.

The two-unknown-origin `HDVehicle+0x4330` surface, manager `+0x374` identity join, literal `0x004b86cf`, P1.3 completion, and provider removal remain fail-closed. Provider count remains 7.
