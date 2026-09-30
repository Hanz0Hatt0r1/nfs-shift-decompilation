# Phase 544 — binary NODE kind boundary and XML-only DAMAGE

Phase 544 corrects the embedded-object admission boundary established by the
production NODE work.

## Binary dispatcher

`FUN_0069a6c0` computes and compares only three kind hashes in the binary
NODE path:

- `LOD`;
- `HIERARCHY`;
- `OBJECT`.

There is no `DAMAGE` comparison or `FUN_00698b00` construction in that
function.

The binary parser therefore exposes:

```text
BINARY_KINDS = {LOD, HIERARCHY, OBJECT}
XML_ONLY_KINDS = {DAMAGE}
```

A serialized NODE payload whose kind string is `DAMAGE` is reported as
`xml-only-kind` and is not claimed as decoded binary scene data.

## DAMAGE is still source-backed

This does not remove the DAMAGE runtime wrapper.

Both XML scene loaders, `FUN_00699b10` and `FUN_0069b1c0`, explicitly
recognize `DAMAGE`, allocate the `0xa0` object through `FUN_00698b00` and
install vtable `0x00af7c88`.

The source-backed wrapper fields remain:

| Runtime offset | Meaning |
|---:|---|
| +0x80 | matrix count |
| +0x84 | runtime matrix array |
| +0x88 | runtime subobject array |
| +0x90 | MatrixNumber |

The distinction is now explicit: these facts belong to the XML scene path, not
to the retail binary NODE grammar.

## Common byte +0x21

The common binary object header still contains one byte between
`MatrixNumber` at `+0x20` and the `matrices/subobjects` counts at
`+0x22/+0x23`.

`FUN_0069a6c0` does not read that byte. The matching XML loader has no
corresponding property.

The IR therefore preserves it as raw `byte_21` with:

- no semantic name;
- binary consumer status `unconsumed`;
- no claimed XML counterpart.

## Production corpus

The observation
`evidence/silverstone_era3_node_kind_boundary_observation.json` covers all
four supplied Silverstone Era3 visual variants.

Across 181 top-level NODE records and 541 recursively decoded object payloads:

- 178 are LOD;
- 361 are OBJECT;
- 2 are HIERARCHY;
- 0 are DAMAGE;
- all 541 byte-`+0x21` values are zero.

The corpus supports the source boundary but does not convert zero into an
invented semantic meaning.

## Boundary

Phase 544 closes the mistaken binary DAMAGE admission and the operational
status of byte `+0x21`.

The next scene target is the remaining FLAT direct-record payload/class
semantics and deeper scene placement/streaming behavior.
