# Phase 544 — NODE control byte and XML DAMAGE fields

Phase 543 closed the production NODE/SUMM binary object grammar and separated
its LOD/HIERARCHY/OBJECT dispatcher from the alternate XML DAMAGE path.

Phase 544 closes two smaller evidence gaps without inventing additional binary
semantics.

## Common object byte +0x21

The binary common object header contains:

| Offset | Source-backed meaning |
|---:|---|
| +0x20 | signed MatrixNumber |
| +0x21 | raw byte; no binary consumer proven |
| +0x22 | matrices |
| +0x23 | subobjects |

`FUN_0069a6c0` reads +0x20, +0x22 and +0x23, but does not read +0x21.
The parallel XML object loaders expose no property corresponding to that byte.

The IR therefore preserves the value and explicitly records:

```text
binary_consumer_status = unconsumed
xml_counterpart = null
semantic_name = null
```

It is not named as a flag merely because the retail corpus contains zero.

## Cross-variant production observation

`evidence/silverstone_era3_node_control_byte_observation.json` covers the
four supplied Silverstone Era3 visual variants.

Across 181 top-level NODE records and 541 recursively decoded binary objects:

- 178 LOD;
- 361 OBJECT;
- 2 HIERARCHY;
- 0 binary DAMAGE;
- 541 / 541 values at common byte +0x21 are zero.

The corpus confirms stability for these resources while deliberately leaving
the byte semantically unnamed.

## XML-only DAMAGE wrapper fields

DAMAGE remains absent from the binary `FUN_0069a6c0` dispatch. Its runtime
object is nevertheless source-backed through `FUN_00699b10/FUN_0069b1c0`.

Those XML loaders prove:

| Runtime offset | Field |
|---:|---|
| +0x80 | matrices |
| +0x84 | runtime matrix array |
| +0x88 | runtime subobject array |
| +0x90 | MatrixNumber |

The constructor remains `FUN_00698b00`, vtable `0x00af7c88`, allocation
size `0xa0`.

These fields are tagged as XML-path evidence so they cannot be mistaken for
binary NODE payload admission.

## Boundary

The production NODE/SUMM grammar no longer has an unresolved binary field that
must be guessed before placement work can continue.

The next scene step is the source-backed join from recursive
LOD/HIERARCHY/OBJECT graphs into PART/FLAT spatial placement, resolving only the
remaining FLAT fields required by that join.
