# Phase 538 — BMW runtime shader target set

Phase 537 proves that the retail BMW body corpus is resource-complete for BMT,
FX and DDS, but the five unique body materials still have multiple distinct
static FXO identities at the best evidence rank.

Phase 538 converts that ambiguity into a compact runtime-capture target set
instead of selecting one permutation heuristically.

## Contract

`SHIFT.BMWRuntimeShaderTargetSet/1` is built from
`SHIFT.BMWBodyMaterialAdmission/1`, including blocked primitive slices.

For each selected canonical primitive it retains every FXO candidate whose
static evidence rank equals the best candidate rank. Statically dominated
candidates are excluded from the capture target set.

Candidate locations are deduplicated by the strongest available identity:

1. `ShaderPermutationIdentity.identity_sha256` when the vertex/pixel pair is
   unique;
2. pair byte SHA-256 when the pair is unique;
3. pixel or vertex byte SHA-256 as a prefilter-only target when a complete pair
   is not yet statically unique.

The last case is important for BMW paint: a pixel shader can still be used to
reduce capture noise without claiming that the matching vertex permutation is
already known.

## Two readiness levels

`capture_ready=true` means every selected primitive has at least one shader
hash that can be used to filter runtime evidence.

`attribution_ready=true` is stricter: every retained target is backed by a
unique complete shader pair/permutation identity.

Neither state implies material/render admission. The target-set boundary has
`render_admission=false` and `selects_permutation=false`.

## Runtime handoff

The existing D3D9 runtime pipeline already records shader permutation, pair,
vertex and pixel byte identities. The target set gives that producer/post-
capture path a compact whitelist of relevant hashes and preserves mappings back
to primitive indices and material references.

Typical flow:

```bash
python shift_importer.py bmw-body-material-admission \
  BMW_M3_E36.bff out/bmw-admission \
  --supplemental-bff BMW_M3_E36_Cockpit.bff \
  --supplemental-bff RENDER.bff

python shift_importer.py bmw-runtime-shader-target-set \
  out/bmw-admission/admission.json \
  out/bmw-runtime-shader-targets.json
```

The next step is to apply this target set directly to captured
`SHIFT.D3D9RuntimeBindingEvidence/1` draw snapshots and report exact
same-instance matches per canonical primitive.
