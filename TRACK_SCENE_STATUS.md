# SHIFT Track Scene status

The existing SHIFT.SGB parser is a verified container boundary: 16-byte header, reversed FourCC chunk tags, chunk sizes, payload hashes and preserved trailing bytes.

Phase 6 adds SHIFT.TrackScene/1 aggregation on top of that boundary. Path-like references inside chunk payloads are recovered as provenance records with byte offsets and encoding; supported resource kinds include MEB geometry, BMT/MTX materials, DDS textures, CSM collision meshes, VHF scene sources and FX/FXO shader resources.

Track placement is intentionally not inferred. The current scene manifest reports placement.status=unknown until the NODE/FLAT/SUMM payload grammar is proven against real SGB samples.


## Phase 250/251: binary SGB and embedded object runtime

The binary SGB container now has a source-backed runtime decoder for NODE, PART, SUMM, OCCL and FLAT boundaries. NODE payload offsets are further decoded through FUN_0069bc50/FUN_0069a6c0 for OBJECT/HIERARCHY/DAMAGE dispatch. Unresolved FLAT body semantics and deeper object field names remain explicitly opaque.


## Phase 252: FLAT runtime tree

SGB FLAT payloads now decode through the recovered runtime tree container: 0x20-byte headers, direct leaf count, 24-bit span, recursive subtrees and 0x40-byte leaf records. Leaf semantics are retained raw until the vtable-backed consumers are normalized.
