# Phase 415 — Runtime SDF solver probe

Phase 415 adds a GDB-Python probe for the builtin SHIFT solver path. It does not patch the retail binary and does not guess object layouts beyond the source-backed ABI.

## Breakpoints

- `FUN_007b0f20` at `0x007b0f20`: `__thiscall`. The probe reads `[ESP+0x04]` as solver state, `[ESP+0x08]` as the row-pointer table, `[ESP+0x0c]` as the RHS/solution vector and `[ESP+0x10]` as scalar count.
- `FUN_007b4110` at `0x007b4110`: `__fastcall`. `ECX` is the physics-system pointer; the probe reads `+0x34` and `+0x40` to capture the solved scalar vector.

The known PE image base is `0x00400000`.

## Output

`tools/gdb_sdf_solver_probe.py` writes `pre_solve_XXXXXX.json` with the complete row-major matrix, RHS, row-index deltas and probe metadata, plus `post_solve_XXXXXX.json` with the solved vector.

The pre-solve JSON fields `scalar_count`, `rhs`, `matrix` and `row_indices` are directly consumable by the Phase 411 normalized capture comparator. Row-index deltas are converted from bytes to double-element indices (`delta / 8`).

## Usage

Attach GDB to the 32-bit Wine process running the retail executable, then:

```text
(gdb) source tools/gdb_sdf_solver_probe.py
(gdb) sdf-probe /tmp/shift-solver-probe
(gdb) continue
```

The breakpoint handlers return `False`, so execution continues automatically after each dump.

The probe targets the builtin solver. When a provider is installed, `FUN_007b0f20` is bypassed; the post-solve breakpoint can still capture the solved vector, but provider-owned matrix preparation remains opaque.

No real runtime capture is committed by this phase.