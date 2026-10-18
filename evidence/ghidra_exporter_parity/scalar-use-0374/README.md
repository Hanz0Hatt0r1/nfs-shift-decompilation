# Scalar-use exporter parity

The shared-first NFS wrapper and its legacy Java fallback were run against the
same read-only, already analyzed `SHIFT.exe` Ghidra program for scalar `0x374`.
The installed game executable and the executable in the Ghidra project have the
same SHA-256 recorded in `manifest.json`. Ghidra was `12.1.2_DEV`.

Both paths emitted 170 `SHIFT.GhidraScalarUses/1` records. The generic
`revenginstr-jsonl-export-parity` report confirms byte and record equality; it
stores only hashes, counts, and mismatch position, not the program-derived
rows. The shared path runs `ExportGhidraScalarUses.java` and adapts its format
field; the fallback runs `ShiftScalarUseExporter.java` directly.

This is one program-wide scalar query. The compatibility fallback remains
because broader same-input coverage and caller review are still outstanding.
The scalar-use rows identify instruction operands only and do not assign
semantic meaning to `0x374`.

To reproduce, use `tools/ghidra/run_shift_scalar_uses.sh` twice with the same
project, program, output location, and scalar: once with
`REVENGINSTR_REPO` pointing to the pinned shared checkout and once pointing to
a path without the shared exporter. Compare the two JSONL outputs with
`revenginstr-jsonl-export-parity`.
