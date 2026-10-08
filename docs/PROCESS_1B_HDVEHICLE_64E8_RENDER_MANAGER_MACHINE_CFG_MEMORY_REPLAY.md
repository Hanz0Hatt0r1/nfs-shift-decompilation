# Process 1B — render-manager machine-CFG memory replay

## Scope

This slice independently replays the exact `DAT_00bc185c` render-manager root through retail machine control flow to answer one narrow question: can a direct exact global load persist the exact outer-object pointer into memory through `MOV [memory], exact_alias` before identity is lost?

PC retail 1.02 `SHIFT.exe` is authoritative. `objdump` is only the instruction decoder. `shift_ghidra.sqlite` is navigation-only and is not used to promote semantic identity.

## Seed inventory

The whole retail `.text` contains 112 machine instructions of the exact shape `MOV full_gpr,[absolute 0x00bc185c]`. The replay starts immediately after every one of those 112 seeds, so Ghidra function-boundary gaps do not silently drop coverage.

As a navigation cross-check, 91 seeds map into SQLite function ranges and 21 fall into boundary gaps. Of the mapped seeds, 88 are reachable from the nominal function entry under the bounded decoder CFG and three are not. All 112 are still analyzed by the seed-local replay.

## Transfer rules

The pass follows direct `jcc`/`jmp` edges and sequential execution. Full-register copies preserve exact identity; zero-displacement `LEA` preserves exact identity. Partial-register writes and unknown arithmetic/transforms destroy exact 32-bit identity. At calls, `EAX/ECX/EDX` are invalidated and the pass does not follow the alias into the callee.

The only promoted sink shape is an actual machine `MOV [memory], exact_outer_alias`. Stack, register-relative and absolute destinations would all be reported.

## Retail result

Across 112 seeds, the largest seed-local CFG exploration visits 380 states, below the 20,000-state safety cap; zero seeds hit the cap. The analysis crosses 303 call boundaries originating from 82 seeds, but finds **zero memory-store sinks**.

Therefore direct exact `DAT_00bc185c` loads do not create a persistent cross-block memory alias through this bounded machine transfer surface.

## Fail-closed boundary

This does not replace the separate `SHIFT.PlayerVehicleRenderManagerMemoryEscapeSurface/1` replay on an exact exhaustive `SHIFT.GhidraFunctionInstructions/2` v2 artifact when that artifact is reacquired. It also does not close aliases created inside opaque callees, returned by helpers, externally initialized, or reconstructed from unknown memory/two-unknown-origin dataflow.

The `manager+0x374 -> HDVehicle+0x4330` join, literal `0x004b86cf`, P1.3 completion and provider removal remain open. External provider count remains 7.
