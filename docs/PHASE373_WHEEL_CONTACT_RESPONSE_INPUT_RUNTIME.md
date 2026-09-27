# Phase 373 — wheel contact response input source

This phase closes the only unresolved input source identified in the Phase 371
response kernel.

At FUN_00766510 source line 759553, the retail source performs:

FUN_007af0a0(body + 0xd4, body + 0x18, local_200)

and immediately passes that destination to:

FUN_007551e0(body + 0x3950, &local_60, local_200, local_1b8, &local_78)

## Proven boundary

The response-input vector therefore has three distinct locations:

| Role | Location |
|---|---|
| body object | runtime pointer at this + 0x33a0 |
| transform context | body + 0xd4 |
| source vector | body + 0x18 |
| transformed result | stack local_200[3] |
| response consumer | FUN_007551e0 |

The source vector at body +0x18 must not be renamed to linear velocity,
relative velocity, impulse, or force based on this call site alone.

## Scope

FUN_007af0a0 is the established transform boundary used elsewhere in the
physics code, but this phase does not reimplement it. That keeps coordinate
conversion separate from the recovered response arithmetic.

The physical meaning and units of body +0x18 remain unresolved.
