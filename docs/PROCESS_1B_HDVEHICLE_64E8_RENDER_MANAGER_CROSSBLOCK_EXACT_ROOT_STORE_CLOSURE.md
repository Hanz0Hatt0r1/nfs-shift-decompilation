# Process 1B — render-manager cross-block exact-root store closure

## Scope

This slice independently replays exact `DAT_00bc185c` register provenance against the authoritative PC retail 1.02 machine code without requiring the missing exhaustive `SHIFT.GhidraFunctionInstructions/2` v2 artifact.

The scan seeds every direct machine load of `[0x00bc185c]`, reconstructs function boundaries from the Ghidra SQLite function-start index, follows direct intra-function CFG edges, preserves only exact register identity, and treats partial-register writes or arithmetic transforms as identity-destroying. Calls clobber `EAX/ECX/EDX` and preserve the IA-32 callee-saved register set.

## Result

The retail image contains exactly 112 direct exact-root loads, matching the already-merged same-basic-block inventory.

Across all reachable local CFG paths from those seeds:

- exact-root `MOV [memory], register` stores: **0**;
- pushes of an exact-root alias: **0**;
- unmodelled exact-alias transfers: **0**;
- derived-subobject LEA transitions: **3**.

The three derived transitions are:

- `FUN_0040d6a0`: `0x0040d83d lea esi,[eax+0x4]`;
- `FUN_00498b80`: `0x00498b93 lea ecx,[edi+0x780]`;
- `FUN_00499240`: `0x004995bf lea ecx,[ebx+0x780]`.

Those values are no longer the exact outer root and are intentionally left as a separate frontier.

For completeness the same trace observes 47 exact-root call-receiver sinks, 9 conditional `EAX` return sinks, and 77 exact-root dereference sinks. Those categories are not re-adjudicated here: the merged first-hop/returned-root contracts remain authoritative for them.

## Adjudication

Persistent cross-basic-block storage of the **exact** render-manager outer root is closed-negative. This narrows the missing-v2 replay gap without pretending that opaque callees, external reconstruction, LEA-derived subobjects, or two-unknown-origin `HDVehicle+0x4330` aliases are solved.

`manager+0x374 -> HDVehicle+0x4330`, literal `0x004b86cf`, P1.3 completion, and provider-count reduction remain fail-closed. Provider count remains 7.
