# Phase 742 scope

In scope:

- freeze the exact PC retail primary `FUN_00766510` response-application sequence;
- reuse native `FUN_007aefb0` and `FUN_007baa70` implementations;
- reproduce exact `FUN_00753650` cross-product ordering;
- carry the source-visible `+0x40a0/+0x40a8/+0x40b0` accumulation;
- carry the three-lane caller-local auxiliary accumulation;
- keep all unresolved caller-state producers explicit;
- preserve the seven-provider active frontier.

Out of scope:

- removing the session-level `contact_response` provider;
- assigning physical names or units to `+0x38f0`, `+0x40a0`, caller reference vectors, or auxiliary lanes;
- guessing production of `+0x38f0/+0x38f8/+0x3900`;
- reconstructing every other branch in `FUN_00766510`;
- joining the final auxiliary accumulator transform/application at lines `759753..759760`;
- generalizing any selected-session state beyond source-backed evidence.
