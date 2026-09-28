# Phase 417 — Retail PE validation for the SDF probe

Phase 417 removes one remaining runtime risk: attaching the probe to a binary whose layout does not match the recovered source.

The supplied retail `SHIFT.exe` is PE32/i386 with image base `0x00400000` and SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

The validator maps the three probe VAs into the `.text` section and checks their exact first 16 bytes:

- `FUN_007b0f20` → `558bec83ec208b5510535633f685d257`;
- `FUN_007b3f40` → `558bec51568bf1837e48005775368b4e`;
- `FUN_007b4110` → `538bdc83ec0883e4f883c404558b6b04`.

The CLI is `tools/validate_sdf_probe_pe.py`.

By default it enforces the supplied executable SHA. `--allow-other-sha256` keeps PE/prologue validation but permits another binary, which is useful for detecting compatible rebuilds without silently treating them as the supplied retail image.

The validator does not attach to a process and does not modify the executable.