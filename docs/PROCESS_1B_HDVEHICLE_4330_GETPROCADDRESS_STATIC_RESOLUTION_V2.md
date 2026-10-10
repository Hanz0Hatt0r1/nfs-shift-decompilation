# Process 1B: CFG-aware GetProcAddress static resolution v2

This supersedes the bounded register-loaded call count from `SHIFT.P1B.HDVehicle4330GetProcAddressStaticResolutionSurface/1` without rewriting the v1 evidence.

The v1 analyzer walked linearly from each imported `GetProcAddress` IAT load until the tracked register was overwritten. That is not control-flow safe: a `pop ebx` on an error-only branch in the `0x00a62353` function stopped the scan before the success path reached later `call ebx` sites.

The v2 analyzer explores direct conditional/unconditional branch successors while the loaded resolver register remains live. It stops a path only on return/terminal instructions, an actual write to the tracked register, or unresolved indirect control flow.

## Corrected bounded surface

- imported IAT load roots: 7;
- register-loaded resolver calls: **89** (v1: 86);
- physical `GetProcAddress` calls: **101** (v1: 98);
- known proc-name instances: **112**;
- unique known names: **108**;
- known patch/protection API names: **0**.

The seven family counts are `2, 4, 5, 2, 6, 67, 3` from load sites `0x0090abf7`, `0x0090aeac`, `0x0091c0b0`, `0x0096daa2`, `0x00999fe7`, `0x009a7e40`, and `0x00a62354`.

The three calls missed by v1 are:

- `0x0099a116` -> `DirectSoundCreate`;
- `0x00a623b8` -> `D3DKMTEscape`;
- `0x00a623c2` -> `D3DKMTOpenAdapterFromHdc`.

No known resolved name intersects the bounded patch/protection API set.

## Gate discipline

This promotes only the CFG-aware static register-loaded resolver surface and marks the v1 linear count superseded. Runtime-created resolver aliases, external resolver pointers, unrelated runtime-populated function-pointer tables, runtime patching, carrier indirect-entry and the P1.3 manager join remain fail-closed.
