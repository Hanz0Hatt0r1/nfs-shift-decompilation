# Phase 488 — BODY scalar-group population

## Goal

Phase 488 makes the scalar-index population path into the BODY-local storage used by `FUN_007ba2b0` explicit and machine-checkable.

The already recovered solver domain supplies, for every ordered runtime constraint, a section, scalar width, scalar base, and `posbody`/`negbody` endpoints. This phase traces that block into the corresponding BODY group domain.

## Exact helper mapping

| Runtime section | Helper | BODY group | Group storage | Record stride | Scalar-index field |
|---|---|---:|---:|---:|---:|
| JOINT | `FUN_007ba8b0` | width 3 | `+0x160` | `0x40` | `+0x30` |
| HINGE | `FUN_007ba900` | width 2 | `+0x164` | `0xa0` | `+0x94` |
| BAR | `FUN_007ba990` | width 1 | `+0x168` | `0x60` | `+0x30` |

For every runtime constraint, the helper is invoked once for the `+0x78` endpoint and once for the `+0x80` endpoint. The same scalar block is therefore witnessed at both referenced BODY objects.

HINGE also carries the already observed auxiliary value into `+0x90`; this phase records that field without assigning new semantics.

## Scalar-block invariant

For a record with width `w` and scalar base `b`, the witness requires:

`scalar_indices = [b, b+1, ..., b+w-1]`

The block must remain inside the solver scalar domain.

This prevents the BODY matrix builder from silently accepting malformed or shifted scalar blocks.

## Relation to Phase 486

Phase 486 consumes the same runtime constraint records to build BODY-local `BodyGroup` objects and then reproduces the Cartesian-product `1.0` writes of `FUN_007ba2b0`.

Phase 488 now provides the missing traceability layer:

`solver-domain scalar block → endpoint helper → BODY group storage → structural matrix seed`

## BMW shape

For the real BMW suspension domain, the expected upstream shape remains 28 runtime constraints and 40 scalar nodes. The provider-independent witness itself does not hard-code a BMW ordering; it consumes whatever ordered solver domain is supplied.

## Scope boundary

This phase records storage population and scalar-index traceability. It does not assign physical semantics to the scalar variables, does not reconstruct later numeric coefficient accumulation, and does not infer provider identity.
