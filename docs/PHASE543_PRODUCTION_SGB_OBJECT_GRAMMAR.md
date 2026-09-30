# Phase 543 — production SGB object grammar

Phase 543 corrects the binary NODE/SUMM object model against both retail
control flow and the Silverstone Era 3 Grand Prix SGB.

## Shared NODE/SUMM wrapper grammar

`FUN_006a4b40` (NODE) and `FUN_006a4900` (SUMM) consume the same
variable-stride source record:

```text
+0x00  record stride
+0x08  Name offset from SGB base
+0x0c  Resource offset from SGB base
+0x10  VariationPalette offset from SGB base
+0x14  Instances
+0x18  wrapper flags byte
+0x1a  signed variation index
+0x1c  inline object payload
```

The old model treated NODE `+0x1c` as an external relative pointer and SUMM
as a fixed 0x38-byte record. Both assumptions fail on the production corpus.

All string and recursive object offsets use the complete SGB base, so data after
the `END ` chunk is a legal reference arena rather than trailing garbage.

## Binary object dispatcher

`FUN_0069bc50 -> FUN_0069a6c0` handles three binary kinds:

- `LOD`;
- `HIERARCHY`;
- `OBJECT`.

The previously recorded DAMAGE constructor is real, but belongs to the parallel
XML object-loading path (`FUN_00699b10/FUN_0069b1c0`) rather than the binary
NODE/SUMM dispatcher. Historical phase documents are left unchanged; the
operational IR now records this distinction.

## Proven common object fields

The XML cross-path gives exact names to three binary bytes:

| Binary offset | Field |
|---:|---|
| `+0x20` | signed `MatrixNumber` |
| `+0x22` | `matrices` |
| `+0x23` | `subobjects` |

Byte `+0x21` remains unresolved.

## MATRIX records

LOD/HIERARCHY matrix records are nine dwords (0x24 bytes). The parallel XML
MATRIX loader `FUN_006990d0` identifies them as:

- three-float `Offset`;
- four-float `Orientation`;
- float `Scale`;
- signed integer `parent`.

The binary runtime copies them into 0x28-byte elements with the proven order:

```text
runtime +00 <- source word 6
runtime +04 <- source word 3
runtime +08 <- source word 4
runtime +0c <- source word 5
runtime +10 <- source word 0
runtime +14 <- source word 1
runtime +18 <- source word 2
runtime +1c <- source word 7
runtime +20 <- source word 8
```

This corrects the older compatibility-only `runtime_copy_order` alias.

## LOD/HIERARCHY recursion

After the matrix table:

- LOD stores one float distance per subobject;
- both LOD and HIERARCHY store one SGB-relative dword object offset per
  subobject;
- every non-zero offset recursively enters `FUN_0069bc50`.

LOD zero distances remain explicitly source-backed as fallback inputs to the
retail distance rule; Phase 543 does not replace them with guessed distances.

## OBJECT transform

OBJECT retains its resource object at runtime `+0x80` and MatrixNumber at
`+0x84`. When MatrixNumber is -1, the serialized payload carries an explicit
Offset/Orientation/Scale transform, mapped through the same source-backed
matrix convention.

## Retail Silverstone closure

The observation file
`evidence/silverstone_era3_grandprix_sgb_object_observation.json` identifies
the source SGB by SHA-256 and contains no raw game payload.

Production results:

- NODE: 41 variable-stride records, exact chunk consumption;
- SUMM: 7,348 variable-stride records, exact chunk consumption;
- recursive kinds: 7,117 LOD, 13,652 OBJECT, 257 HIERARCHY;
- recursive edges: 13,123 LOD→OBJECT, 512 HIERARCHY→LOD,
  2 HIERARCHY→OBJECT;
- maximum recursive depth: 2;
- structural errors: 0;
- DAMAGE observed in the binary corpus: no.

The SGB contains 215,834 bytes after END that are legally referenced by the
earlier wrapper/object records.

## Boundary

Phase 543 does not assign semantics to common object byte `+0x21`, does not
invent higher-level scene roles for individual LOD/HIERARCHY objects, and does
not conflate the XML DAMAGE path with the binary NODE/SUMM dispatcher.

The next scene step is to join these proven transforms/subobject graphs to the
PART/FLAT placement structures and only then expose placement data to
RenderBinding.
