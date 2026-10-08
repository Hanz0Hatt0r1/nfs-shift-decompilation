# Process 1B — Participants Manager direct singleton reference surface

## Scope

This slice closes direct whole-image immediate materialization of the exact Participants Manager singleton address `0x00bc9fc0`. PC retail 1.02 machine code is authoritative; the Ghidra SQLite export is navigation-only.

## Result

The exact immediate `0x00bc9fc0` occurs only three times in the retail image:

- `0x00489ae3`: `mov ecx,0x00bc9fc0` before `FUN_00488dc0`, the singleton initialization path.
- `0x00489afa`: `mov eax,0x00bc9fc0`, the getter return.
- `0x00a9c5a0`: `mov ecx,0x00bc9fc0; jmp FUN_004891b0`, the static cleanup thunk registered by the getter/init path at `0x00489aed..0x00489af2`.

No independent runtime function directly reconstructs the manager root from the singleton absolute address. The cleanup thunk is lifecycle destruction, not a new producer.

## Adjudication

Direct immediate singleton reconstruction is closed-negative as a source of an unrelated value at manager `+0x374`. This does not close object-field/global persistence, arithmetic/non-immediate reconstruction, or other escaped aliases. The last literal `0x004b86cf` remains fail-closed and provider count remains 7.
