# SHIFT Track Scene status

The existing SHIFT.SGB parser is a verified container boundary: 16-byte header, reversed FourCC chunk tags, chunk sizes, payload hashes and preserved trailing bytes.

Phase 6 adds SHIFT.TrackScene/1 aggregation on top of that boundary. Path-like references inside chunk payloads are recovered as provenance records with byte offsets and encoding; supported resource kinds include MEB geometry, BMT/MTX materials, DDS textures, CSM collision meshes, VHF scene sources and FX/FXO shader resources.

Track placement is intentionally not inferred. The current scene manifest reports placement.status=unknown until the NODE/FLAT/SUMM payload grammar is proven against real SGB samples.
