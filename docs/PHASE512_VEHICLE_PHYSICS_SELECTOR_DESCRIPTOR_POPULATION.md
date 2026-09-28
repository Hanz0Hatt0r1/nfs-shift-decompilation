# Phase 512 — selector descriptor population and bitfield layout

## Goal

Record the exact source-backed transformation performed when a selector source
record is copied into the repeated descriptor table owned by DAT_00bbc600.

Contract:

SHIFT.VehiclePhysicsSelectorDescriptorPopulation/1

## Storage and capacity

FUN_00410490 constructs 16 descriptor records. The selector context stores:

- capacity at +0x28 = 0x10;
- active count at +0x1c;
- descriptor table base at +0xb8;
- descriptor stride 0x90.

FUN_00409290 inserts only while:

context+0x1c < context+0x28

then calls thunk_FUN_00d36a00(this, count, source+0x10) and increments
the active count.

## Packed token fields

thunk_FUN_00d36a00 reads a 32-bit token from source +0x10 and packs it into:

| Descriptor offset | Source operation |
|---|---|
| +0x00 | bits 0..3 |
| +0x04 | bits 4..7 |
| +0x08 | bits 8..10 |
| +0x0c | bits 11..14 |
| +0x78 | bits 15..18 |
| +0x7d | source byte +0x14, bit 0 |

No semantic label is assigned to these fields.

## Direct copies

The population function copies source regions into descriptor fields:

| Source | Descriptor |
|---|---|
| +0x05 | +0x10 |
| +0x25 | +0x14 |
| +0x45 | +0x18 |
| +0x76 | +0x24 |
| +0x96 | +0x28 |

It also copies 14 dwords (56 bytes) from source +0xa8 to descriptor +0x38.

## State-related writes

The same population path explicitly initializes:

- descriptor +0x74 = 0;
- descriptor +0x88 = 0.

It conditionally initializes descriptor +0x70 by calling
FUN_00542620() when descriptor +0x08 == 0.

This closes the evidence gap identified while reviewing Phase 510:
the +0x74 eligibility field is populated to zero by thunk_FUN_00d36a00;
it should not be attributed to FUN_0040eec0 or to the unrelated selector-context
+0x74 field in FUN_00410350.

## Selection relation

Phase 510/508 selection then consumes the same table through
thunk_FUN_0043af50:

descriptor+0x74 == 0 -> selected pointer + ordinal

with the selected ordinal written into descriptor +0x8c.

## Evidence boundary

The bitfields and offsets are source-backed, but their gameplay/physics
semantics are intentionally not inferred. Provider identity and runtime
numeric parity remain capture-dependent.
