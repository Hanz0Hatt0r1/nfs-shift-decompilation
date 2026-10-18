# Instruction-slice exporter parity

The shared-first NFS wrapper and its legacy Java fallback were run against the
same read-only, already analyzed `SHIFT.exe` Ghidra program for the 32-byte
slice beginning at `0x00451280`. Both produced one
`SHIFT.GhidraInstructionSlice/1` row with byte-identical output. The report
retains hashes and counts only; no instruction rows are checked in.

This single slice does not establish parity for other addresses or justify
removing the compatibility fallback.
