# D3D9 declaration Type semantics

The recovered conversion switch covers Type codes 0..16 and is represented as source-backed evidence.

## Important paths

- 0..3 use the float payload path;
- 4 uses the packed-color conversion path;
- 5 converts components directly to bytes;
- 8 uses normalized 255.0 conversion;
- 11..12 use 65535.0 scaling;
- 13..14 use the recovered 10-bit packing path;
- 15..16 use the recovered half-float encoder.

## COLOR

Type 4 is the D3D9 D3DCOLOR path.

Combined with the exact MEB triples `[4,6,0]` and `[4,6,1]`, the static BMW COLOR declaration mapping is resolved.

The remaining proof target is runtime same-instance binding.
