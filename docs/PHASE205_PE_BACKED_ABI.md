# Phase 205 — PE-backed D3D9 ABI propagation

The supplied retail SHIFT.exe is now an explicit optional evidence input to the
MEB COLOR bridge.

When present, the bridge validates:
- file-backed Type 4 = RGBA32 / D3DDECLTYPE_D3DCOLOR / 4 bytes / 4 components;
- file-backed Usage ordinal 6 = Colour / numeric D3D9 Usage 10.

The PE layer does not by itself prove a runtime draw instance. It only validates the
declaration ABI that downstream runtime evidence must match.

The bridge remains backward-compatible: when no PE report is supplied, the previously
proven descriptor-triple + source-backed Type-4 path continues to operate. A malformed
or conflicting PE ABI is fail-closed.
