# Phase 346: BMW buffer capture intake

Phase 346 turns the Phase 344 capture plus Phase 345 expected-byte generation
into one reproducible intake command.

## Command

`python bmw_runtime_buffer_capture_intake.py CAPTURE.jsonl PAYLOAD_DIR GEOMETRY.json BMW_M3_E36.bff OUT_DIR`

The command:

1. validates and loads the D3D9 JSONL capture;
2. resolves capture-relative `buffer_payload` paths against `PAYLOAD_DIR`;
3. builds the runtime trace and draw snapshots;
4. extracts the exact BMW body MEB from the retail BFF;
5. writes the deterministic MEB-derived VB/IB candidates;
6. runs the Phase 344 byte comparator;
7. writes one `report.json` with the final evidence boundary.

## Output

`OUT_DIR/expected/` contains the reconstructed VB/IB candidates and their
manifest. `OUT_DIR/report.json` combines capture counts, runtime trace metadata,
expected artifact provenance and byte-parity results.

The intake exits with code 0 only when the captured runtime VB and all six
target INDEX16 buffers match the reconstructed bytes and the runtime trace has
no blockers. Otherwise it exits with code 2.

## Boundary

Relative-path normalization is only an intake convenience. It does not alter
payload bytes or weaken event ordering. Runtime identity still requires the
Phase 344 creation-instance and draw-bounded payload checks to pass.
