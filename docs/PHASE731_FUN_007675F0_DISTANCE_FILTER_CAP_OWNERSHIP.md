# Phase 731 — FUN_007675f0 distance-filter-cap ownership

Phase 731 removes `distance_filter_cap` from the production per-pass `FUN_007675f0` provider payload.

## PC retail ownership

The existing PC retail Phase 379/662 oracle already records the filter update as:

```text
FUN_00783a30(previous, distance, body_field+0xa0, 0.5)
```

The `body_field` in this caller is `HDVehicle`, so the cap consumed by `FUN_007675f0` is `HDVehicle+0xa0`. It is not a value produced anew by the typed per-pass contact-outer provider.

Phase 731 therefore treats this field as immutable selected-session setup state. Its upstream initializer and selected BMW value are still unproven, so the native runtime requires an explicit one-time `Fun007675f0DistanceFilterCapSetup` seed rather than inventing a constant.

## Xbox 360 corroboration

The European Xbox 360 retail `default.xex` independently preserves the same ownership in the PowerPC analog of `FUN_007675f0` around `0x8259a9f0`:

```text
0x8259aaa8  lfd   0, 160(31)      ; HDVehicle+0xa0
0x8259aab0  frsp  3, 0            ; argument passed to filter
0x8259aab8  bl    0x825b7e10      ; FUN_00783a30 analog
0x8259aabc  stfs  1, 16512(31)    ; HDVehicle+0x4080 writeback
```

The same function also matches the PC path through the `HDVehicle+0x4080` persistent state, BODY0 planar-speed lanes, and rare contact constants. This Xbox evidence is corroboration only: PC layout and native ownership remain grounded in the PC retail source oracle. No PC initializer or runtime value is inferred from Xbox code.

The source XEX SHA-256 is `8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58`; the extracted PowerPC PE SHA-256 is `23844dbba0cf72bc11512821b90008ea5d2b06ee886d921f416ca6caae43a628`.

## Native boundary

New setup contract:

```text
SHIFT.Fun007675f0DistanceFilterCapSetup/1
```

Production `ContactOuterSessionInput` now contains six unresolved per-pass fields:

```text
planar_delta
surface_scalar
base_scalar
projected_scalar
alignment_scalar
param_3
```

`distance_filter_cap` remains present in the lower historical `ContactOuterExternalInput` and complete `ContactOuterKernelInput`, because those interfaces describe the already-native arithmetic boundary. The session adapter resolves that lower field from the one-time setup value.

Historical fixtures can supply their former cap exactly once through a compatibility-only seed. That seed is not retail evidence and cannot refresh the value on later passes.

## Scope

Phase 731 does not:

- infer the selected BMW `HDVehicle+0xa0` value;
- claim the upstream initializer is known;
- change `FUN_00783a30` arithmetic;
- assign new physical semantics to the cap;
- reduce the active top-level external-provider count below seven.

The change only moves a source-owned field out of the per-pass provider frontier into explicit setup state.
