# Phase 557 — IMB version and variable prefix

Phase 557 removes the manual fixed-header locator that Phase 556 kept as an
evidence boundary.

The retail version helper and the beginning of
`CMeshPrimitiveType::LoadBinaryMeshFromResource` provide enough information
to locate the fixed IMB mesh header deterministically.

## Packed version

`FUN_0064a250` packs four version components as:

```text
((major << 6 | minor) << 11 | patch) << 11 | build
```

The matching getters prove the bit widths:

| Field | Bits | Getter |
|---|---:|---|
| major | 4 | `FUN_0064a270` |
| minor | 6 | `FUN_0064a280` |
| patch | 11 | `FUN_0064a290` |
| build | 11 | `FUN_0064a2a0` |

Therefore:

- `0.2.0.0 = 0x00800000`;
- `0.4.0.0 = 0x01000000`.

`FUN_00859800` rejects a packed file version newer than `0.4.0.0`.

## Prefix grammar

The file starts with the packed version dword.

### Exact 0.2.0.0

For exactly `0.2.0.0`:

- byte `+0x04` is the control byte;
- the embedded resource name begins at `+0x05`;
- the runtime MeshType field at `+0x04` receives the source value `1`;
- no name padding is applied before the fixed mesh header.

### Other versions below 0.4.0.0

The loader reads a 16-bit control word at `+0x04`:

- low byte: bone-block flag;
- high byte: source for runtime MeshType field `+0x04`;
- the resource name begins at `+0x06`.

Runtime field `+0x04` normalizes the high byte as:

```text
0 -> 0
2 -> 2
anything else -> 1
```

### 0.4.0.0

At version `>= 0.4.0.0` — with the retail maximum this is the 0.4 path:

- the same 16-bit control word remains at `+0x04`;
- an additional raw 16-bit value is present at `+0x06`;
- the resource name begins at `+0x08`;
- the name including its NUL is rounded up to 4-byte storage before the fixed
  mesh header.

The extra 16-bit value is preserved as evidence but is not assigned an
unproven semantic.

## Bone gate

The Phase 556 optional bone block is no longer a manual switch.

It is present when both conditions hold:

1. packed version is at least `0.2.0.0`;
2. the low control byte is non-zero.

That result is passed directly into the existing fixed-header decoder.

## IR

The new prefix contract is:

`SHIFT.IMBBinaryPrefix/1`.

`parse_imb_binary_mesh()` now performs:

```text
packed version
  -> control/prefix variant
  -> embedded resource name
  -> retail alignment
  -> fixed header offset + bone gate
  -> Phase 556 fixed mesh schema
```

The existing low-level `parse_imb_binary_mesh_schema(..., header_offset=...)`
entry point remains available for forensic/manual use.

## CLI

The normal command no longer needs a header offset:

```bash
python shift_importer.py imb-binary-schema mesh.imb out/imb-schema.json
```

The old manual mode remains valid:

```bash
python shift_importer.py imb-binary-schema mesh.imb out/imb-schema.json \
  --header-offset 0x40 --has-bone-block
```

## Boundary after Phase 557

Source-backed now:

- 4/6/11/11 version encoding;
- retail maximum-version gate;
- v0.2 one-byte prefix variant;
- two-byte control variant;
- v0.4 extra word and 4-byte name alignment;
- automatic fixed-header location;
- automatic bone-block admission.

Still open:

- semantic meaning of the raw v0.4 extra word;
- complete per-Type vertex payload byte consumption;
- full primitive-source record parsing;
- neutral IMB geometry/material adaptation;
- IMX XML adaptation.

Evidence:
`evidence/imb_binary_prefix_source.json`.
