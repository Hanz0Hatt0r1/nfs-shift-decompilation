# Phase 126 — BMW runtime parity gate

`SHIFT.BMWRuntimeParity/1` is the final offline/runtime contract before a real BMW
draw can be treated as renderer-ready.

## Checks

1. Reuse `SHIFT.BMWRuntimeShaderJoin/1` for exact VS/PS permutation + MEB identity.
2. Compare material `register_set=2` constant ranges against the captured shader
   permutation's VS/PS constant register usage.
3. Compare the known MEB declaration semantics against a captured declaration
   instance when an explicit MEB Usage-ordinal → D3D9 Usage-byte map is supplied.

For the current BMW golden asset the known declaration bridge includes:

- `COLOR0` property 460 → Type 4;
- Usage ordinal 6 → runtime Usage byte supplied by the capture-side map;
- UsageIndex 0.

The tool intentionally leaves other semantic families out of the proof until their
ordinal mapping is directly evidenced.

## CLI

```bash
python shift_importer.py bmw-runtime-parity bmw-paint-slice.json runtime-evidence.json bmw-runtime-parity.json --usage-map usage-map.json
```

## Acceptance

The gate is ready only when shader identity, exact resource identity, constant-bank
parity and the currently evidenced declaration subset all match. Otherwise the
blocking reasons remain machine-readable.