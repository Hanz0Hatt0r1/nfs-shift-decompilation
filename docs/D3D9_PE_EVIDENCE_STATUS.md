# Direct PE evidence status

## Evidence path

`SHIFT.exe → PE header → image base → sections → VA → file offset → table bytes`

The pure-Python resolver can decode the recovered D3D9 declaration Type/Usage tables when their storage is file-backed.

## Current result

The supplied executable provides the evidence needed for:

- Type 4 = D3DDECLTYPE_D3DCOLOR;
- Usage ordinal 6 = D3D9 Usage 10 (COLOR).

These values participate in the static MEB descriptor bridge.

## Limitation

Loader-initialized/BSS-only globals are not treated as recovered initializer data. The resolver reports unavailable/file-backed state instead of fabricating zeros.

PE evidence does not identify the declaration bound at a specific runtime draw.
