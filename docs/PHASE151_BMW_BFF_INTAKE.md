# Phase 151 — BMW M3 BFF intake verifier

`SHIFT.BMWBFFIntakeEvidence/1` is a preflight for the real retail `BMW_M3_E36.bff`.

## Checks

- exact archive size: `18,934,688` bytes;
- valid SHIFT BFF header/table structure through the existing `BFF` parser;
- exactly one `BMW_M3_E36_PAINT.bmt` entry;
- exactly one `BMW_M3_E36_KIT00_BODY_LODA.meb` entry;
- extracted MEB size `300,764` bytes;
- extracted MEB SHA-256 `960ac728db8c...b2c2c`.

The report records the exact entry indices, compressed/uncompressed sizes and entry type/CRC.

## CLI

```bash
python shift_importer.py bmw-bff-intake /path/BMW_M3_E36.bff bmw-bff-intake.json
```

A ready intake does not imply that material/shader extraction is ready. It only proves
the required primary archive and its exact M3 body/material entries are intact.

## Environment note

The connected Dropbox exposes the BFF as a temporary binary download URL, but the current
execution sandbox cannot fetch that host. The verifier is therefore committed for the
environment that has direct binary access; no synthetic BFF result is promoted.