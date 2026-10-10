# Process 1D — 16-carrier call-target composition

This P1.3D slice composes the complete machine `CALL` surface physically present inside the 16 exact-root carrier bodies.

## Composed result

Merged evidence provides:

- 214 immediate direct callsites from `SHIFT.P1D.Slot3DirectCalleeBulkOpcodeClosure/1`;
- 2 call-through-memory sites, `0x00770ec4` and `0x00770f41`;
- both non-immediate sites are resolved by `SHIFT.P1D.Slot3StaticIndirectAA60B4Closure/1` through image slot `0x00aa60b4` to static target `0x00778052`.

Therefore the 16 carrier bodies contain 216 machine callsites total, and the bounded count of runtime-unknown call targets inside those bodies is zero.

This is a carrier-body closure only. It is not a global indirect-entry closure.

## Reproduce

```bash
python3 tools/ghidra/build_p1d_slot3_carrier_call_target_composition.py \
  evidence/p1d_slot3_direct_callee_bulk_opcode_closure.json \
  evidence/p1d_slot3_static_indirect_aa60b4_closure.json \
  --output out/p1d_slot3_carrier_call_target_composition.json
```

The builder fails closed if either upstream contract, callsite counts, site identities, or static-resolution state drift.

## Boundary

Still open:

- callbacks and other external indirect entry into carriers or callees;
- indirect calls in deeper callees;
- runtime code/data patching beyond the pinned image state;
- reconstructed pointer aliases and runtime-generated/copied storage paths.

Accordingly global indirect-entry, callback, stored/escaped-alias, writer-provenance, P1.3D and aggregate P1.3 gates remain false. External provider count remains 7.
