# Phase 620 — exact BMT material constant candidate join

Phase 618 splits unresolved Silverstone draws by the static evidence dimension
that still differs. `material-distinct-candidates` means the surviving static
candidates carry different BMT payload SHA-256 values, so material evidence can
potentially distinguish them before any new capture is considered.

Phase 620 adds:

`SHIFT.IMBMaterialConstantCandidateJoin/1`.

It consumes evidence that already exists:

```text
Phase 618 material-distinct candidates
+ Phase 617/target draw-local event identity
+ captured CTAB-filtered float constant state
+ Phase 619 exact FXO VS/PS pair provenance
+ original BMT/FXO corpus
```

No game execution is required.

## Exact proof chain

For each material-distinct draw and each surviving candidate:

```text
candidate BMT SHA-256
→ exact BMT payload in corpus
→ parsed numeric shader parameter
→ exact candidate VS/PS byte pair
→ Phase 619 verified FXO payload + explicit program offsets
→ canonical CTAB material-uniform binding
→ stage + constant name + register index + register count
→ complete draw-local Set*ShaderConstantF state
→ IEEE-754 float32 bit equality
```

The stage reuses `uniform_linker.link_material_uniforms()` for the
BMT-parameter-to-CTAB mapping instead of guessing register positions from value
similarity.

## Numeric equality

D3D9 float constants are written as 32-bit floats, while JSON serialization may
show a longer decimal spelling. Phase 620 therefore converts both the BMT source
number and captured runtime number to IEEE-754 little-endian float32 and compares
the resulting bits.

A witness is one of:

- `exact-f32-match`;
- `exact-f32-contradiction`;
- `incomplete-runtime-constant`;
- `non-f32-comparable-value`.

Only complete CTAB register evidence can contradict a candidate.

## Candidate policy

A candidate receives:

- `exact-material-constant-match` when at least one material constant is
  comparable, every comparable value matches, and no required witness is
  incomplete;
- `exact-material-constant-contradiction` when any complete exact CTAB witness
  differs at float32 bit level;
- `insufficient-material-constant-evidence` when the BMT, exact shader pair,
  verified FXO payload, reflected binding, or captured register state is
  incomplete.

The draw becomes `single-candidate-by-exact-material-constants` only when:

1. exactly one candidate is an exact match; and
2. every other surviving candidate is explicitly contradicted by complete
   evidence.

This deliberately rejects a weaker rule such as “one candidate matches and the
others have no data”. Missing evidence never eliminates a candidate.

If multiple candidates exactly match, the result remains
`ambiguous-multiple-exact-material-constant-matches`.

If all candidates are contradicted, the stage reports
`material-constant-conflict-no-survivor` and retains the original candidate set.
It does not invent a replacement candidate.

## Static corpus identity

BMT resources are located by exact decoded payload SHA-256, not by filename.
Every source occurrence of the same payload is retained as provenance.

FXO payload admission is inherited from Phase 619: only payload SHA-256 values
whose embedded VS/PS pair was independently reverified at the explicit offsets
are eligible for constant linking.

If content-equivalent FXO occurrences produce different constant contracts, the
candidate fails closed as insufficient instead of selecting one archive copy.

## Existing capture coverage

The historical Silverstone JSONL contains `SetVertexShaderConstantF` and
`SetPixelShaderConstantF` writes, and the draw-local evidence stage already
intersects those register files with the active shader CTAB at every target draw.
Phase 620 therefore consumes existing observations rather than asking for a new
capture.

Sampler-state events, texture snapshots and VB/IB payloads are independent
requirements and are not needed for this constant gate.

## CLI

```bash
python src/scene/imb_material_constant_candidate_join.py \
  out/silverstone_d3d9_draw_local_ambiguity_audit.json \
  out/d3d9_target_draw_local_evidence.json \
  out/silverstone_fxo_pair_provenance.json \
  out/silverstone_material_constant_candidate_join.json \
  --corpus Silverstone_Era3_.zip \
  --corpus /path/to/RENDER.bff
```

The corpus can contain BFFs directly or ZIPs containing BFFs.

## Blocker accounting

### Closed by this stage

- exact BMT payload identity for material-distinct candidates;
- exact BMT numeric parameter to CTAB float-register mapping;
- exact draw-local float32 comparison with last-write-backed captured register
  state inherited from the draw-local evidence artifact;
- deterministic fail-closed candidate narrowing when all alternatives are
  explicitly contradicted.

### Still open

- material candidates differing only in textures when scalar/vector constants do
  not discriminate them;
- exact DDS content identity when descriptors are equal;
- sampler-state values absent from the historical capture;
- metadata-equivalent LOD/geometry alternatives;
- exact geometry payload equality where offline scene identity cannot close the
  ambiguity;
- final scene-instance/render admission.

### Existing data that still merits tooling before recapture

- texture creation/bind history and descriptors;
- BMT -> FX sampler -> DDS references;
- repeated-instance transform/constant signatures;
- exact shader pair use history and FXO provenance.

### Truly absent historical observations already identified

The historical capture lacks `buffer_payload` events, portable runtime
`resource_path + resource_sha256` identity, captured texture snapshots, and
`SetSamplerState` events. These remain conditional boundaries, not automatic
requests for another capture.

## Non-claims

Phase 620 does not rank BMTs, infer material identity from a shared texture, pick
an LOD from its filename, or promote a single static candidate to render
admission. Exact constant evidence only narrows the specific Phase 618 candidate
set to which it applies.
