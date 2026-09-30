# Phase 543 — production NODE / LOD / object layout

Phase 543 replaces the synthetic-only NODE object interpretation with the
layout consumed by the retail Silverstone Era 3 Grand Prix SGB.

## NODE payload is inline

`FUN_006a4b40` iterates each NODE record and calls:

```text
FUN_0069bc50(record + 0x1c, sgb_base)
```

Therefore the dword at NODE `+0x1c` is the **first dword of the object
payload**, not an offset to another payload.

The fixed NODE metadata is `0x1c` bytes:

| Offset | Meaning |
|---:|---|
| +0x00 | record stride |
| +0x04 | unresolved |
| +0x08 | name offset, relative to SGB base |
| +0x0c | resource offset, relative to SGB base |
| +0x10 | variation-palette offset, relative to SGB base |
| +0x14 | instances |
| +0x18 | flags byte |
| +0x1a | signed variation index |
| +0x1c | inline object payload begins |

The concrete runtime NODE wrapper remains the Phase 520 `0x38`-byte
`0x00af78ec` object.

## SGB-relative reference arena

`FUN_006a5270` stops chunk dispatch at the `END ` chunk. It does not make
that point the end of the addressable resource.

NODE names, resource names and embedded-object strings add their serialized
offsets to the base pointer of the complete SGB. In the retail Grand Prix
sample the chunk stream ends at byte 1,961,156, while 215,834 additional bytes
remain addressable after `END `.

The parser now exposes this as the **post-END reference arena** rather than
reporting it as trailing garbage.

## Four embedded object kinds

`FUN_0069a6c0` recognizes:

- `LOD`;
- `HIERARCHY`;
- `OBJECT`;
- `DAMAGE`.

The previous IR omitted `LOD`.

### Common binary header

The first `0x24` bytes contain:

- kind/source/third string offsets relative to SGB base;
- instances;
- sphere centre XYZ and radius;
- signed `MatrixNumber` at `+0x20`;
- one unresolved byte at `+0x21`;
- `matrices` count at `+0x22`;
- `subobjects` count at `+0x23`.

The `matrices` and `subobjects` names are independently confirmed by the
SCENE XML loader `FUN_0069b1c0`.

## MATRIX record

LOD and HIERARCHY store `matrices` fixed `0x24`-byte records immediately
after the common header.

`FUN_006990d0` gives the XML names and `FUN_0069a6c0` gives the binary
copy order:

| Serialized words | Meaning | Runtime |
|---|---|---|
| 0..2 | Offset XYZ | +0x10..+0x18 |
| 3..6 | Orientation XYZW | WXYZ at +0x00..+0x0c |
| 7 | Scale | +0x1c |
| 8 | parent | +0x20 |
| — | reserved/unresolved | +0x24 |

Runtime matrix stride is `0x28`.

## LOD

The LOD wrapper is constructed by `FUN_00698a90`, uses vtable
`0x00af8660`, and allocates `0xa0` bytes.

Proven wrapper fields are:

- +0x80 subobject count;
- +0x84 matrix count;
- +0x88 runtime matrix array;
- +0x8c runtime subobject array;
- +0x94 MatrixNumber;
- +0x98 LOD distance array.

After the matrix table, the serialized LOD payload stores one float distance
per subobject and then one SGB-relative child-object offset per subobject.

## HIERARCHY

The HIERARCHY wrapper remains `FUN_00698a20` / `0x00af8620`.

The former `hierarchy_type` / `hierarchy_count` field names are corrected:

- +0x80 subobject count;
- +0x84 matrix count;
- +0x88 runtime matrix array;
- +0x8c runtime subobject array;
- +0x94 MatrixNumber.

HIERARCHY stores the subobject offset table immediately after its matrix table.

## OBJECT

OBJECT's third string is the RESOURCE/Filename reference. The binary payload
stores:

- `instances` at word 3;
- `userflags` at +0x24;
- when `MatrixNumber == -1`, an embedded MATRIX transform:
  - Offset XYZ at +0x28;
  - Orientation XYZW at +0x34;
  - Scale at +0x44.

The wrapper converts the orientation to runtime WXYZ at +0x88, stores Offset
at +0x98 and Scale at +0xa4.

## Production observation

The Grand Prix NODE chunk contains 41 top-level records:

- 40 LOD, all stride `0xc4`, MatrixNumber -1, matrices=1, subobjects=2;
- 1 HIERARCHY, stride `0x104`, MatrixNumber 0, matrices=3, subobjects=2.

Recursive decoding produces another 82 OBJECT payloads. No guessed pointer or
class identity is needed.

## Boundary

Byte +0x21 remains unnamed. DAMAGE-specific serialized fields beyond the
common header remain partial. Those are the next scene targets; the production
NODE container/object layout itself is now closed.
