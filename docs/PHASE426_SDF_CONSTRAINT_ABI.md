# Phase 426 — SDF constraint ABI correction and descriptor schema

Phase 426 corrects a previously merged BAR endpoint-counter mapping and adds the exact reflective SDF constraint descriptor schema.

## BAR correction

A direct audit of FUN_007b3150 shows both BAR endpoint paths increment the source BODY runtime counter at +0xA0:

- positive BAR endpoint: +0xA0
- negative BAR endpoint: +0xA0

The previous Phase 424 construction IR incorrectly described the positive BAR counter as +0x98. The regression suite now locks both values to +0xA0.

JOINT and HINGE continue to use +0x98 for positive and +0x9C for negative references.

## SDF descriptor schema

FUN_007b42f0 registers:

| Field | Offset | Type-id |
| --- | ---: | ---: |
| type | +0x10 | 3 |
| Label | +0x14 | 0 |
| Pos Body | +0x18 | 0 |
| Neg Body | +0x1C | 0 |
| Copy Body | +0x20 | 0 |
| opaque field A | +0x28 | 0x13 |
| opaque field B | +0x40 | 0x13 |
| opaque field C | +0x58 | 0x13 |

The three 0x13 fields retain their decompiler global identifiers rather than guessed semantic names.

The machine-readable aliases only cover the four explicitly named descriptor properties. In particular, the parser-level pos field is not forced onto an opaque slot.

## Integration

This closes the descriptor ABI between the text SDF parser and the existing constraint-construction IR. The next physics target remains runtime application of these descriptor properties at the SDK/provider boundary.
