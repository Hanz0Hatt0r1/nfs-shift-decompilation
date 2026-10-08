# Process 1B — Participants Manager constant multi-register reconstruction surface

## Scope

This slice extends the simple same-register arithmetic scan to constant-only synthesis across multiple general-purpose registers. It targets the exact Participants Manager singleton root `0x00bc9fc0` in the PC retail 1.02 executable.

## Result

The bounded constant propagator tracks EAX/EBX/ECX/EDX/ESI/EDI/EBP through:

- `mov r32, imm32`;
- `mov r32, r32`;
- `add/sub r32, imm32`;
- `add/sub r32, r32`;
- `lea r32, [base + index*scale + disp]` when every participating term is already constant.

State is reset at `call`, `jmp`, `ret`, and `int3`; unknown writes kill the destination register. The scan observes the same three known literal productions and evaluates 834 constant arithmetic transitions. Zero non-literal chains produce `0x00bc9fc0`.

## Adjudication

Constant-only multi-register synthesis is closed-negative as an alternate Participants Manager root source. Combined with the direct immediate, static pointer-cell, and same-register arithmetic closures, the remaining reconstruction risk is runtime-derived: memory loads, opaque helper returns, indirect/external initialization, or unrecognized transforms.

The manager `+0x374` join and literal `0x004b86cf` remain fail-closed. Provider count remains 7.
