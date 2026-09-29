# Phase 539 — same-instance BMW runtime shader target matching

Phase 538 converts statically tied BMW shader candidates into a capture-oriented
hash target set. Phase 539 joins those targets to actual D3D9 indexed draws.

## Exact draw attribution

The Phase 538 target set now also preserves the canonical MEB draw range for
each primitive:

- `first_index`;
- `index_count`;
- D3D9 triangle `primitive_count = index_count / 3`.

This matters for shared materials such as the two BMW paint primitives: a common
shader identity is not enough to distinguish them, while the exact indexed draw
range is.

## Runtime matching

`SHIFT.BMWRuntimeShaderTargetMatch/1` requires three independent joins before
a primitive can be attributed:

1. exact target MEB resource identity;
2. exact `DrawIndexedPrimitive` range;
3. a shader hash match from the Phase 538 target set.

Shader evidence is ranked consistently with the existing runtime selector:

- permutation identity: 100;
- pair byte SHA-256: 90;
- both vertex and pixel byte SHA-256: 80;
- one stage hash only: 40.

Score 40 is reported as a useful prefilter match but cannot establish
attribution.

## Same-instance requirement

Exact attribution additionally requires the runtime
`same_instance_gate.ready == true` and the specific
`(frame, draw_index)` to appear in its candidate set.

Repeated observations of the same shader identity across multiple frames are
not ambiguous. Multiple distinct strong identities for one primitive remain
blocked.

## CLI

```bash
python shift_importer.py bmw-runtime-shader-target-match \
  bmw-runtime-shader-targets.json \
  runtime-binding.json \
  bmw-runtime-shader-target-match.json
```

The next evidence step is now operational rather than architectural: capture a
BMW M3 body frame with the existing D3D9 producer and feed its runtime binding
report into this matcher.
