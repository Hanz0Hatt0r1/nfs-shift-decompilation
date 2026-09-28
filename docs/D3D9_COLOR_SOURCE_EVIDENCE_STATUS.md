# D3D9 COLOR source-evidence status

## Static chain

`MEB descriptor → Type ordinal → Usage ordinal → Channel → D3D9 declaration record`

Recovered source shows Type/Usage table resolution, Channel→UsageIndex propagation, the Colour stream family and the Type-4 packed-color path.

## Current result

- 460 → `[4,6,0]`
- 461 → `[4,6,1]`
- Type 4 → D3D9 D3DCOLOR
- Usage ordinal 6 → D3D9 COLOR, numeric 10

The static COLOR mapping is resolved.

## Runtime boundary

Same-instance execution still requires correlation of:

`MEB/resource identity + declaration + VB + IB + VS/PS + DrawIndexedPrimitive`

A static source match is not substituted for runtime object identity.
