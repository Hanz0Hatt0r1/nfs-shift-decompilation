# Global-reference exporter parity

The shared-first NFS wrapper and its legacy Java fallback were run against the
same read-only, already analyzed `SHIFT.exe` Ghidra program for target
`0x00ab4784`. Both produced one `SHIFT.GhidraGlobalReferences/1` row containing
five references, with byte-identical adapted output. The hash-only parity
report, executable identity, Ghidra version, and source commits are pinned in
`manifest.json`.

This is one target query in one analyzed program. The fallback remains in place;
the result does not establish parity for every address or replace caller review.
