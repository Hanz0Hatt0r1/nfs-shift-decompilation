# Phase 495 — scalar-reset callsite extractor

## Goal

Phase 495 removes a hard-coded dependency from the callsite evidence pipeline. Instead of manually copying the six `FUN_007b2210` caller addresses, the project can now derive them from an objdump-style disassembly of the retail PE.

## Extraction

The parser scans `FUN_007b3f40` for direct `CALL` instructions whose destination is `FUN_007b2210`.

For each match:

`return_address = call_address + encoded_instruction_length`

On the shipped i386 PE all six direct calls are 5-byte `CALL rel32` instructions.

## Verification

The CLI compares the extracted return addresses against the source/disassembly-backed Phase 486 table:

- `0x007B4029`
- `0x007B4034`
- `0x007B403F`
- `0x007B407E`
- `0x007B4089`
- `0x007B40CB`

A mismatch makes the extraction report not ready instead of silently updating the runtime attribution table.

## CLI

    python tools/extract_scalar_reset_callsites.py SHIFT.exe

Optional:

    python tools/extract_scalar_reset_callsites.py SHIFT.exe -o callsites.json

## Why this matters

This makes the selector attribution reproducible from the actual binary image and provides an integrity check for future retail builds/variants.

## Scope boundary

The extractor identifies direct call topology only. It does not infer constraint semantics, selector meaning, matrix coordinates, provider class identity, or physical units.