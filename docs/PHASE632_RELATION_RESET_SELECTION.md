# Phase 632 — relation-state reset selection for FUN_007b2210

Phase 631 refreshes relation-owned endpoint samples and regenerates the
provider-absent matrix/RHS on every admitted fixed step, but reset rows still
come from the prepared SBFR packet.

Phase 632 ports the remaining source-backed selection boundary immediately
before the builtin sparse solve.

## Source evidence

The audited executable source is `SHIFT.exe.c` SHA-256:

`512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`.

The reset-selection loop is in `FUN_007b3f40`.

A previous project note called the tested flag `sample+0x70 & 1`. Direct
source audit corrects that wording:

```text
relation + 0x70, bit 0
```

The BODY-owned sample is reached separately through the positive endpoint
pointer stored at `relation+0x7c`.

The relation constructors temporarily receive their scalar base through
`relation+0x70`, allocate positive then negative BODY-owned samples, and then
clear `relation+0x70`. Therefore the later `FUN_007b3f40` low-bit test is a
relation runtime-state flag, not the retained scalar base.

## Exact reset widths

For every relation whose `relation+0x70 & 1` is set, retail reads the scalar
base from the positive BODY-owned sample and calls `FUN_007b2210` over:

| Relation | Positive sample scalar-base field | Reset width |
|---|---:|---:|
| JOINT | sample `+0x30` | 3 |
| HINGE | sample `+0x94` | 2 |
| BAR | sample `+0x30` | 1 |

The selector preserves top-level source order: JOINT, HINGE, BAR.

## CRRF packet

Phase 632 adds:

`SHIFT.NativeConstraintRelationResetFramePacket/1` (`CRRF`).

The packet contains only one normalized low-bit value per source-order relation:

- JOINT relation state bit 0;
- HINGE relation state bit 0;
- BAR relation state bit 0.

It deliberately does not serialize:

- scalar bases;
- reset-node indices;
- matrix/RHS values;
- BODY sample values.

Proof flags require explicit relation-state readiness, source-order readiness
and provider absence.

The scalar bases are recovered only by joining CRRF to the exact CSRF endpoint
identity and GBCF BODY-owned samples.

## Fail-closed selector

`select_fun_007b3f40_reset_nodes()` requires:

1. CRRF relation cardinality exactly matches CSRF;
2. CSRF BODY indices and sample indices are valid in GBCF;
3. positive endpoint side flag is 1;
4. negative endpoint side flag is 0;
5. paired endpoint scalar bases are equal;
6. each JOINT/HINGE/BAR scalar span fits the solver domain;
7. relation scalar spans do not overlap;
8. the relation layout covers the complete scalar domain.

Only then can a set relation-state bit emit reset rows.

The six-scalar regression uses:

```text
JOINT state = 1 -> rows 0,1,2
HINGE state = 0 -> no rows
BAR state   = 1 -> row 5

selected reset nodes = [0,1,2,5]
```

No reset node is stored in CRRF.

## Fixed-step integration

`shift_runtime` adds:

```text
--constraint-relation-reset-frame FILE.crrf
```

CRRF requires CSRF, which already requires GBCF.

For each admitted fixed step the provider-absent path is now:

```text
CSRF
  -> FUN_007b3ed0 refreshed GBCF
  -> FUN_007bc680 / FUN_007bb8d0 / FUN_007ba570
  -> exact generated matrix/RHS == SBFR gate
CRRF + CSRF + GBCF
  -> FUN_007b3f40 relation-state selection
  -> source-derived reset nodes
  -> FUN_007b2210
  -> FUN_007b0f20
```

When CRRF mode is active, the runtime does not consume
`PreparedBuiltinSolverFrame.reset_nodes` as the reset source. The existing
SBFR path remains unchanged when CRRF is absent.

The current SBFR still carries its historical reset list and solution oracle,
so Phase 632 does not yet redefine the SBFR packet format. It changes the
runtime source of reset-node execution while preserving all earlier packet
compatibility.

## Regression coverage

Native checker:

```bash
native_runtime/build/shift_runtime_constraint_relation_reset_frame_check \
  frame.gbcf relations.csrf relation-reset.crrf
```

Linux CI covers:

- selective six-scalar reset selection `[0,1,2,5]`;
- state-cardinality rejection;
- endpoint side-identity rejection;
- scalar overlap/gap rejection;
- 11-BODY BMW structural fixed-step shape;
- 4 JOINT + 4 HINGE + 20 BAR relation states;
- all 40 solver rows selected when all relation bits are set;
- three fixed steps using relation-derived reset nodes;
- unchanged GBCF→SBFR matrix/RHS equality;
- Vulkan validation with zero errors.

## Boundary after Phase 632

The provider-absent fixed-step path no longer needs SBFR's prepared reset list
as the runtime reset-node source when CRRF evidence is supplied.

Still evidence-gated:

- authentic per-frame BODY transforms/positions and raw relation inputs;
- authentic per-frame production of the relation `+0x70` state bit;
- provider-present dispatch and provider numeric behavior;
- persistent solved BODY state into vehicle transform/motion integration.

The next safe integration step is to replace static prepared BODY/relation/reset
state with an authentic per-frame state source, without weakening the existing
identity, matrix/RHS or reset-selection gates.
