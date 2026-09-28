# BMW runtime shader join status

## Current capability

`SHIFT.BMWRuntimeShaderJoin/1` correlates material permutation identity with
draw-local D3D9 runtime shader state and resource identity.

The join now also reports `shader_byte_hash_checks` for vertex, pixel, and pair
bytes when both sides expose the corresponding hashes.

## Interpretation

- `match` is direct byte-hash agreement between material and runtime evidence.
- `mismatch` is preserved as diagnostic evidence and does not silently select
  another permutation.
- `not-comparable` is non-blocking when the corresponding hashes are absent.

The authoritative runtime match still requires the existing permutation identity
and resource identity gates. Byte-hash diagnostics do not replace same-instance
draw evidence.


## Runtime render propagation

The same provenance is carried into `SHIFT.BMWRuntimeRenderContract/1`: the selected
FXO candidate retains `payload_sha256`, while runtime evidence exposes the derived
vertex/pixel/pair byte hashes separately.

This preserves the distinction between source payload identity and runtime
same-instance identity through the final renderer-facing contract.
