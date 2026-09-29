# Phase 539 — BMW runtime constant-register permutation filter

Phase 538 turns the statically tied retail BMW shader candidates into a
capture-oriented hash target set without selecting a permutation.

Phase 539 applies a second, already available runtime discriminator: exact
constant-register locations observed at the draw boundary in the committed
frame-30444 BMW material witness.

## Candidate metadata

The material linker now records compact CTAB maps on each FXO candidate:

- `vertex_constant_registers`;
- `pixel_constant_registers`.

Only float constant register-set entries are retained. This is evidence
metadata; it does not change static ranking.

## Runtime filter

`SHIFT.BMWRuntimeRegisterPermutationFilter/1` compares the top-rank logical
permutations against the witness registers for the same material and exact BMW
body MEB SHA-256.

Repeated runtime draws of one material must agree on every witnessed
`(stage, name) -> register` mapping. Conflicting draw witnesses fail closed.

A single surviving permutation is selected only when its vertex-pair selection
is also unique. Two or more survivors remain explicitly ambiguous.

`SHIFT.BMWBodyRuntimeRegisterPermutationFilter/1` applies the same rule to
every selected primitive in `SHIFT.BMWBodyMaterialAdmission/1`.

## Retail v1.02 result

Using the Drive-backed retail archives and the committed frame-30444 witness:

| Material | Phase 537 distinct top permutations | After runtime register witness |
|---|---:|---:|
| BMW_M3_E36_BADGING | 18 | 2 |
| BMW_M3_E36_PAINT | 20 | 4 |
| GENERIC_WINDOWS | 10 | 2 |
| GENERIC_GLOSS_BLACK | 27 | 4 |
| BMW_M3_E36_LIGHTSGLASS | 10 | 2 |

No material is marked ready. The filter therefore narrows the exact next
capture/source-analysis target without substituting a heuristic choice.

The paint survivors additionally retain ambiguous vertex-pair status.

## CLI

```bash
python shift_importer.py bmw-runtime-register-filter \
  out/bmw-admission/admission.json \
  evidence/bmw_m3_e36_kit00_body_loda.runtime_material_witness.json \
  out/bmw-runtime-register-filter.json
```

The material input may also be one material binding/slice for focused
diagnostics.

## Next gate

The remaining 2/4-way sets require evidence that distinguishes shader byte
identity or pass/permutation selection at the same runtime instance. The
register witness alone is intentionally not treated as sufficient.
