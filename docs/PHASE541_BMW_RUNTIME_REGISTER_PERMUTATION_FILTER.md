# Phase 541 — runtime constant-register permutation filter

Phase 539 adds the exact same-instance shader-hash matcher and Phase 540 adds a
raw-capture prefilter for new D3D9 captures. The committed frame-30444 BMW
witness predates raw shader-byte capture, but it already contains draw-local
constant-register observations.

Phase 541 reuses that existing evidence as an independent fail-closed
permutation discriminator.

## Candidate metadata

The material linker now records compact CTAB maps on every FXO candidate:

- `vertex_constant_registers`;
- `pixel_constant_registers`.

Only float constant-register entries are retained. Static ranking is unchanged.

## Register filter

`SHIFT.BMWRuntimeRegisterPermutationFilter/1` requires:

- the exact BMW body MEB SHA-256 when both sides expose it;
- a consistent runtime witness for one material;
- the same top static evidence rank used by the retail target-set pipeline;
- exact `(stage, constant-name) -> c-register` agreement.

Candidates are deduplicated by the existing compiled permutation identity rule.

A single surviving logical permutation is reported ready only if its vertex
pair is itself unique. Multiple survivors remain ambiguous.

`SHIFT.BMWBodyRuntimeRegisterPermutationFilter/1` applies the same rule to
all canonical primitive slices in one Phase 533 admission report.

## Retail v1.02 result

Using the Drive-backed retail BMW/Cockpit/RENDER archives and committed
frame-30444 witness:

| Material | Before | Register-compatible |
|---|---:|---:|
| BMW_M3_E36_BADGING | 18 | 2 |
| BMW_M3_E36_PAINT | 20 | 4 |
| GENERIC_WINDOWS | 10 | 2 |
| GENERIC_GLOSS_BLACK | 27 | 4 |
| BMW_M3_E36_LIGHTSGLASS | 10 | 2 |

No material is marked ready. The paint survivors also retain ambiguous
vertex-pair status.

The exact remaining FXO identities and byte hashes are persisted in
`evidence/bmw_m3_e36_runtime_register_permutation_filter.json`.

## CLI

```bash
python shift_importer.py bmw-runtime-register-filter \
  out/bmw-admission/admission.json \
  evidence/bmw_m3_e36_kit00_body_loda.runtime_material_witness.json \
  out/bmw-runtime-register-filter.json
```

This path complements Phases 539–540. A new capture carrying raw shader hashes
should use the raw prefilter and same-instance matcher; existing register-only
witness data can use Phase 541.

## Next gate

The remaining 2/4-way sets require same-instance shader-byte identity or a
stronger source-backed pass/permutation discriminator. Register coincidence
alone is not treated as exact shader attribution.
