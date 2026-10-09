# Process 1D / P1.3D — shallow canonical SIMD store closure

## Scope

After shallow ordinary-MOV, x87 and string-copy surfaces were bounded, selected slot3 `HDVehicle+0x28b8..+0x28bf` still retained a canonical SSE/MMX vector copy/zero-init class.

`tools/ghidra/analyze_p1d_slot3_shallow_simd_store_frontier.py` scans the four proven wheel/physics lifecycle roots through direct call depth 4, maps the reachable sized-function ranges, and inventories explicit memory-destination canonical MMX/SSE/SSE2 move stores. Direct callgraph reachability remains navigation evidence only.

## Retail result

Pinned inputs:

- PC retail 1.02 `SHIFT.exe` SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`;
- `shift_ghidra.sqlite` SHA-256 `ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e`.

The depth<=4 scan covers 377 reachable sized functions. It observes 497 instructions with XMM/MMX operands in 8 functions, but only 14 explicit canonical SIMD memory stores in 4 functions:

- `FUN_009011e0`: 3 `MOVQ` stores;
- `FUN_00909e0e`: 2 `MOVLPD` stores;
- `FUN_0090a37e`: 3 `MOVLPD` stores;
- `FUN_00911e19`: 6 `MOVLPD` stores.

Every store destination is an exact `ESP`-relative stack slot (`[esp+0x4]` or `[esp+0x10]`). The scan finds zero non-stack explicit SIMD stores and zero `MASKMOVQ/MASKMOVDQU` implicit-store instructions.

Therefore no candidate in this bounded canonical SIMD move-store class can write selected `HDVehicle+0x28b8..+0x28bf`.

## Gate

```text
shallow mapped canonical SIMD store surface = complete
explicit SIMD stores                         = 14
stack SIMD stores                            = 14
non-stack SIMD stores                        = 0
implicit mask stores                         = 0
selected slot3 SIMD writer found              = false
slot3 shallow SSE/vector copy-zero subset     = complete
deeper direct aliases                         = open
indirect/callback aliases                     = open
slot3 writer provenance                       = false
P1.3D complete                                = false
provider count                                = 7
```

## Limits

This is deliberately not a whole-program “no SSE writer” theorem. It closes only explicit canonical MMX/SSE/SSE2 move stores mapped into sized function ranges reachable within four direct edges. Out-of-line chunks outside those ranges, deeper direct paths, implicit/custom vector writes outside the enumerated class, and indirect/callback paths remain open.

Function-range and callgraph data are used for navigation only. The semantic rejection rests on the exact retail machine destination being stack-relative.

## Run

```bash
python3 tools/ghidra/analyze_p1d_slot3_shallow_simd_store_frontier.py \
  /path/to/shift_ghidra.sqlite \
  /path/to/SHIFT.exe \
  --output out/p1d_slot3_shallow_simd_store_frontier.json
```

## Next step

Remove the shallow canonical SIMD copy/zero-init class from the P1.3D slot3 frontier. Continue only with deeper direct or indirect/callback paths that carry an exact selected-wheel-derived alias; do not widen from callgraph reachability alone.
