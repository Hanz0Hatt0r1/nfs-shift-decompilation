# Function-instruction exporter parity

The shared-first NFS wrapper and its legacy Java fallback were run against the
same read-only, already analyzed `SHIFT.exe` Ghidra program for function
`0x00451280`. Each exporter reported one function containing 2,962
instructions. The generic JSONL parity report confirms the full function row
is byte-identical, without retaining program-derived instructions. The program
hash and source commits are pinned in `manifest.json`.

The result covers targeted-function mode only. The generic exporter also has
an all-functions corpus mode that the SHIFT fallback does not implement, so
this parity does not establish equivalence for that mode and does not justify
removing the compatibility fallback.
