# Phase 486 — scalar reset callsite attribution

## Goal

Phase 486 maps the raw caller return address captured by Phase 485 to the exact machine call that invoked `FUN_007b2210`.

## Exact callsites

| Return address | Group | Ordinal | Width |
|---:|---|---:|---:|
| `0x007B4029` | JOINT/HINGE | 0 | 3 |
| `0x007B4034` | JOINT/HINGE | 1 | 3 |
| `0x007B403F` | JOINT/HINGE | 2 | 3 |
| `0x007B407E` | SECONDARY | 0 | 2 |
| `0x007B4089` | SECONDARY | 1 | 2 |
| `0x007B40CB` | BAR | 0 | 1 |

These are the return addresses immediately following the six direct `CALL FUN_007b2210` instructions in the retail PE at the three source call groups.

## Runtime correlation

At `FUN_007b2210` entry the Phase 485 probe records `[ESP]`. Phase 486 uses that value as a strict lookup key. Unknown or missing return addresses remain unattributed instead of being guessed.

The attribution result retains:

- source constraint group;
- selector ordinal within that group's 3/2/1 width;
- source line identifier;
- selector value from the capture.

## Why this matters

The static chain is now executable on both sides:

`constraint record → selector source → direct CALL site → FUN_007b2210(selector)`

`FUN_007b2210 → provider vtable +0x1c(selector)`

This closes the gap between source-derived selector provenance and real runtime capture events.

## Scope boundary

Callsite attribution does not infer the semantic meaning of the selector, nor does it identify a matrix coordinate or physical constraint quantity. It only authenticates where the reset call came from.