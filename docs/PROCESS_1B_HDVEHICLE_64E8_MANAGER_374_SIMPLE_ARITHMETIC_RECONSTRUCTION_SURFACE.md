# Process 1B — Participants Manager simple arithmetic reconstruction surface

## Scope

This slice closes the simple non-literal reconstruction class for the exact Participants Manager singleton root `0x00bc9fc0`. The authoritative input is the PC retail 1.02 executable; disassembly is used only to enumerate bounded instruction patterns.

## Result

The whole retail `.text` scan examined `38,128` `mov r32, imm32` seeds across EAX/EBX/ECX/EDX/ESI/EDI/EBP. Three seeds are the already-known exact literal singleton references covered by `SHIFT.HDVehicle64e8Manager374DirectSingletonReferenceSurface/1`.

For every other seed, the scan followed the same register through at most 15 instructions, applying only direct `add`, `sub`, or same-register `lea` arithmetic and stopping at `call`, `jmp`, `ret`, `int3`, or an overwrite of that register. This produced 499 same-register arithmetic transitions to adjudicate.

No non-literal chain reconstructs `0x00bc9fc0`.

## Adjudication

Simple straight-line immediate arithmetic reconstruction is closed-negative as a source of an unrelated Participants Manager root and therefore cannot introduce a new manager `+0x374` value.

This is deliberately not a global reconstruction closure. Memory-load/table-derived roots, multi-register arithmetic, opaque helper returns, and indirect dataflow remain open. The literal `0x004b86cf` candidate therefore stays fail-closed and provider count remains 7.
