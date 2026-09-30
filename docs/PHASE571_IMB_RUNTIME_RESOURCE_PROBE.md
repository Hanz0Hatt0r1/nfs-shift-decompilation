# Phase 571 — IMB runtime resource probe adapter

Phase 570 closes the static resource/draw identity for all Silverstone IMB
primitive bindings. The existing D3D9 runtime evidence layer already has a
strict draw-local same-instance gate, but its historical resource input is
named `meb_resource` and expects a resource descriptor document.

Phase 571 bridges one IMB target binding into that existing contract instead of
duplicating the runtime evidence engine.

## Contract

The new adapter is:

`SHIFT.IMBRuntimeResourceProbe/1`

implemented in:

`src/scene/imb_runtime_resource_probe.py`.

Input:

- `SHIFT.IMBRuntimeShaderTargetSet/1`;
- one exact `binding_index`.

Output includes the resource fields already consumed by
`build_runtime_binding_evidence(..., meb_resource=...)`:

- `resource` — exact normalized IMB path;
- `resource_sha256` — decoded IMB payload SHA-256;
- `property_descriptors` — source-backed Type/Usage/Channel triples.

It also retains:

- archive;
- BFF entry index;
- primitive index;
- Phase 570 draw range;
- shader family;
- target count.

## Property descriptors

The IMB neutral geometry/ranking path stores proven stream identities as the
three-digit repository property id:

`Type ordinal + Usage ordinal + Channel`.

For example:

- `200` → `[2, 0, 0]`;
- `460` → `[4, 6, 0]`;
- `130` → `[1, 3, 0]`;
- `580` → `[5, 8, 0]`.

The adapter accepts only exact three-digit numeric property ids. Future or
unknown encodings stay blocked rather than being guessed.

## Readiness

A probe is ready only when the selected target binding is already:

- shader `capture_ready`;
- resource-identity-ready;
- draw-range-ready;
- `same_instance_match_ready`.

It additionally requires:

- a valid `.imb` path;
- a 64-character hexadecimal decoded payload SHA;
- at least one valid property descriptor.

The adapter does not select a shader permutation.

## Reuse of the D3D9 same-instance gate

The existing runtime trace contract can consume the probe directly:

```python
runtime = build_runtime_binding_evidence(
    events,
    meb_resource=imb_probe,
    usage_ordinal_map=usage_map,
)
```

The `meb_resource` argument name is legacy terminology. Its effective
contract is resource path/hash plus property descriptors.

A new regression test proves that an IMB probe:

1. matches exact IMB path + decoded SHA;
2. maps IMB property `460` through Usage ordinal 6 → D3D9 COLOR usage 10;
3. matches the bound declaration at the exact indexed-draw boundary;
4. causes the existing `same_instance_gate` to become proven.

No alternate or weaker track-specific gate is introduced.

## CLI workflow

Build one probe from the Phase 570 target set:

```bash
python src/scene/imb_runtime_resource_probe.py \
  out/silverstone-runtime-shader-targets.json \
  123 \
  out/imb-binding-123-runtime-probe.json
```

Then build runtime evidence with the existing command:

```bash
python shift_importer.py d3d9-runtime-trace \
  shift_d3d9_capture.jsonl \
  out/imb-binding-123-runtime.json \
  --meb-resource out/imb-binding-123-runtime-probe.json \
  --usage-map evidence/d3d9_usage_ordinal_map.json \
  --require-same-instance
```

The historical `--meb-resource` option can therefore carry the IMB probe
without changing the runtime contract.

## Boundary

Phase 571 proves adapter compatibility, not a retail Silverstone observation.

Still required from an authentic track capture:

- exact IMB resource path/SHA observation on the bound declaration;
- valid bound declaration;
- Usage ordinal mapping;
- indexed draw at the same draw-local snapshot.

The Phase 570 draw range is preserved by the probe for the next matcher, but
the current runtime-trace same-instance gate itself authenticates resource +
declaration + indexed-draw presence rather than the specific primitive range.

## Next

The next step is the IMB runtime shader-target matcher:

`IMBRuntimeShaderTargetSet/1 + D3D9RuntimeBindingEvidence/1
→ exact resource + exact draw range + shader hash match`.

It must accept only draw-local states already covered by the existing
`same_instance_gate` and may promote a static shader candidate only when all
three identities agree.
