# Compact instruction-stream exporter parity

The shared generic exporter and the legacy NFS fallback were run on the same
read-only, already analyzed `SHIFT.exe` Ghidra program. Each stream contains
2,204,481 instruction rows plus one identity header. The gzip-aware generic
parity tool reports identical ordered JSON records after decompression and
object-key normalization (`same_records: true`, no mismatch). The compressed
file hashes differ (`same_bytes: false`), so this is record parity rather than
byte parity. The report retains only hashes, counts, and the mismatch result.

This covers the compact whole-program stream for this analyzed program. The
fallback remains available; the result does not establish behavioral
equivalence or instruction semantics.
