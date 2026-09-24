# Phase 128 — BMW runtime golden gate

`SHIFT.BMWRuntimeGoldenGate/1` объединяет runtime parity и RenderCommand readiness.

Он не разрешает golden render, пока одновременно не выполнены:

- exact VS/PS permutation identity;
- exact BMW MEB resource identity;
- sampler parity;
- constant register parity;
- captured constant-value parity;
- the currently evidenced D3D9 declaration subset;
- `RenderCommand/1` ready.

The gate always requires an explicit Usage-ordinal → D3D9 Usage-byte map because the
project does not synthesize this mapping from naming conventions.

## CLI

```bash
python shift_importer.py bmw-runtime-golden-gate bmw-paint-slice.json runtime-evidence.json bmw-runtime-gate.json --usage-map usage-map.json
```

When the gate is ready, the resulting report is the acceptance token for the next
`bmw-reference-render` invocation.