# Process 1B — whole-text HDVehicle +0x4330 materialization occurrence closure

A whole-retail `.text` scan for the immediate/displacement `0x4330` yields six instruction occurrences. Four are the already-proven normal runtime materializers: `FUN_00768a4d`, `FUN_00769520`, `FUN_0076b130`, and `FUN_0076df50`. One occurrence at `0x007a28ab` is only the rel32 byte encoding of `call FUN_007a6be0`, not pointer arithmetic. The final arithmetic occurrence is compiler cleanup `Unwind@00a7063f`, whose `add ecx,0x4330` reaches the already-bounded `FUN_00756050` destructor path.

Therefore retail `.text` contains no unknown generic single-instruction `receiver+0x4330` materializer. Combined with the persistence/return closures in this PR, every known normal materializer is bounded and does not export an exact alias.

This does not close multi-instruction arithmetic synthesis or externally supplied/opaque exact pointers. Manager `+0x374` identity and literal `0x004b86cf` remain fail-closed; provider count remains 7.
