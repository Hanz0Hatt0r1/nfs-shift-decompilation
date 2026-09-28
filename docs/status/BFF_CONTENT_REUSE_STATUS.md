# Raw BFF payload reuse status

## Current capability

tools/audit_bff_content_reuse.py adds a content-addressed audit layer above the
logical-path parity report.

It groups exact stored payload SHA-256 values across BFF archives even when the
same payload appears under different logical paths. The audit reads only BFF
entry metadata and raw stored payload bytes; it does not decompress Type-2/Oodle
resources or infer decoded/runtime semantics.

This is useful for identifying candidates for renderer/resource deduplication
while preserving logical-path identity as a separate contract.

## Reproduction

For the vehicle corpus:

python tools/audit_bff_content_reuse.py BMW_M3_E36.bff BMW_M3_E36_Cockpit.bff Vehicles.zip -o payload_reuse.json

Increase --minimum-archives when only broadly reused payloads are wanted.

## Interpretation boundary

- Same logical path + same raw SHA-256: exact stored-byte reuse at that path.
- Different logical paths + same raw SHA-256: exact stored-byte reuse with distinct path identities.
- Raw SHA-256 equality alone does not prove decoded-format, material, shader,
  or runtime-object equivalence.
- RENDER.bff can be included deliberately, but vehicle-specific parity evidence
  remains a separate scope.

## Next use

Join high-reuse FXO/DDS clusters to material and DrawPacket evidence before
treating them as renderer-level shared resources.
