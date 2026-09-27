# Phase 352 — BMW runtime geometry proof contract

Phase 351 proved the raw BMW body VB/IB uploads byte-for-byte against the
deterministic MEB-derived artifacts. Phase 352 promotes that result into one
strict contract consumed by later renderer/golden stages.

## Inputs

The gate joins:

- `SHIFT.BMWM3MEBRuntimeGeometryParity/1` from the frame-30444 runtime geometry
  correlation;
- `SHIFT.BMWM3DirectBlobParity/1` from the direct apitrace TYPE_BLOB comparison.

The geometry report establishes the exact BMW resource SHA-256, vertex-buffer
pointer/stride/size and the six primitive-specific index-buffer pointers. The
direct parity report retains those runtime pointers alongside its seven byte
comparisons.

## Fail-closed behavior

An older Phase 351 parity report that contains only sizes/hashes is not promoted
to the proof contract. This is intentional: byte equality without the resource
pointer metadata cannot authenticate which runtime object supplied the bytes.

The output format is `SHIFT.BMWM3RuntimeGeometryProof/1`.

When ready, the contract explicitly records:

- BMW M3 MEB identity;
- vertex buffer `0x27b39460`, stride 76, 269800 bytes;
- six runtime index-buffer pointers and their primitive triangle counts;
- raw runtime VB/IB bytes as proven;
- MEB byte parity as proven;
- creation-instance identity as proven.

The contract is suitable as a downstream input gate; it does not replace the
separate shader/material same-instance proof.
