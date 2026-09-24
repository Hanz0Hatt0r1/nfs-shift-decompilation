# Phase 144 — real BMW material binding from BFF

`bmw_material_from_bff.py` is the first end-to-end offline adapter from the retail
BMW archive to `SHIFT.MaterialBinding/1`.

## Inputs

- primary `BMW_M3_E36.bff`;
- optional supplemental BFFs such as `BMW_M3_E36_Cockpit.bff`.

The extractor requires the exact M3 paint BMT and the exact body MEB:

- `vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt`;
- `vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb`.

It resolves the BMT shader source, collects all `.fxo` entries as permutation
candidates and exposes all `.dds` paths to the existing material linker.

## Output

`SHIFT.RealBMWMaterialBindingEvidence/1` contains:

- the unmodified `SHIFT.MaterialBinding/1` produced by `material_linker.py`;
- BMW paint-contract and shader-gate reports;
- exact BFF/BMT/MEB/FX provenance and per-entry SHA-256;
- FXO candidate and DDS path counts;
- an explicit boundary that runtime instance attribution is not proven.

`ready=true` is only possible when the existing material contract and strict shader
gate both succeed with a unique exact permutation.

## CLI

```bash
python shift_importer.py bmw-material-from-bff /path/BMW_M3_E36.bff material-binding.json \
  --supplemental-bff /path/BMW_M3_E36_Cockpit.bff
```

The command never writes raw extracted BFF payloads to the repository.

## Boundary

This phase is offline and deterministic. A successful result proves the archived
material/linker chain, not that the retail process selected that permutation in a
particular runtime frame. Runtime declaration/shader/draw capture remains separate.