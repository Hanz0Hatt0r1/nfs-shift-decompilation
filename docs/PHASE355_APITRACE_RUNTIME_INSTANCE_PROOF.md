# Phase 355 — apitrace runtime declaration instance proof

Phase 355 preserves the D3D9 object identity that exists at the exact BMW DrawIndexedPrimitive boundary in the compact apitrace extraction path.

## What changed

tools/extract_apitrace_unique_bmw.py now records a vertex_declaration resource beside the existing vertex/index buffers. For each deduplicated target geometry binding it preserves:

- declaration pointer;
- SetVertexDeclaration binding call;
- CreateVertexDeclaration creation call and raw provenance;
- same_instance.

The resource is also included in the compact resource index, so the declaration creation call remains part of the deterministic callset.

bmw_apitrace_runtime_instance_proof.py turns that data into the strict SHIFT.BMWM3APITRACERuntimeDrawInstanceProof/1 contract.

For each known BMW primitive count (28, 50, 192, 204, 2098 and 2462), the proof requires:

1. a target draw with 3,550 vertices;
2. a declaration bound before that draw;
3. a declaration creation instance before the binding;
4. the same declaration pointer in state and resource evidence;
5. a created/bound target vertex-buffer instance;
6. a created/bound target index-buffer instance;
7. the configured target VB/IB pointers to match.

The proof uses ordered creation/binding call numbers and active object identity, so a pointer reused after Release cannot masquerade as the earlier object instance.

## Explicit evidence boundary

The phase proves runtime object identity only. It does not infer:

- declaration bytes;
- MEB resource identity;
- shader permutation identity;
- constant values;
- texture identity.

Those remain separate proof boundaries and are not fabricated from apitrace geometry signatures.

## One-command integration

tools/run_apitrace_bmw_buffer_proof.py now writes runtime_draw_instance_proof.json when unique_bmw_geometry.json is available. The existing seven-object raw-buffer parity result and SHIFT.BMWM3RuntimeGeometryProof/1 readiness remain independent, so this new evidence cannot silently turn byte parity into shader/material proof.

## Usage

After the existing compact BMW extraction has identified the target geometry:

```bash
python bmw_apitrace_runtime_instance_proof.py \
  bmw-buffer-proof/unique_bmw_geometry.json \
  bmw-buffer-proof/runtime_draw_instance_proof.json
```

The combined pipeline also emits the same report automatically:

```bash
python tools/run_apitrace_bmw_buffer_proof.py \
  /path/to/shift.trace \
  /path/to/unique_bmw_geometry.json \
  /path/to/BMW_M3_E36.bff \
  ./bmw-buffer-proof
```

A ready: true result at this phase means the declaration/VB/IB object identity is proven at the selected BMW draw instances; it does not mean that the full SHIFT.BMWRuntimeGoldenGate/1 is ready.
