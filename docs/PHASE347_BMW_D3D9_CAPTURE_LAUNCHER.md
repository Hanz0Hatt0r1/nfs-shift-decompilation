# Phase 347: reproducible BMW D3D9 capture launcher

Phase 347 adds a small Linux/Wine launcher that enables exactly the raw VB/IB
capture required by Phase 344 and writes all capture products under one output
directory suitable for Phase 346 intake.

## Usage

`tools/run_bmw_d3d9_buffer_capture.sh --prefix /path/to/prefix --output-dir /path/to/out -- /path/to/NFS.exe`

Optional `--wine` selects a non-default Wine binary. Arguments after the
`--` separator are passed unchanged to the game.

## Enabled capture

- `WINEDLLOVERRIDES=d3d9=n` is prepended so the local proxy is selected;
- `SHIFT_D3D9_CAPTURE_BUFFER_PAYLOADS=1`;
- `SHIFT_D3D9_CAPTURE_BUFFER_PAYLOAD_DIR=<out>/buffer_payloads`;
- JSONL flush is enabled by default;
- screenshots and texture snapshots remain disabled by default.

The launcher does not alter the game command line and does not invent any
resource identity. Its only purpose is to make the capture configuration
reproducible.

## Handoff

After the game exits, feed the resulting files to Phase 346:

`python bmw_runtime_buffer_capture_intake.py <out>/shift_d3d9_capture.jsonl <out>/buffer_payloads evidence/bmw_m3_e36_kit00_body_loda.runtime_geometry.json BMW_M3_E36.bff <out>/intake`

Phase 346 will return exit code 0 only when the bounded runtime payloads match
the reconstructed BMW MEB candidates.
