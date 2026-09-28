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
