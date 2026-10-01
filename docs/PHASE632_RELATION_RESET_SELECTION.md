# Phase 632 — relation-state reset selection for FUN_007b2210

Phase 631 refreshes relation-owned endpoint samples and regenerates the
provider-absent matrix/RHS on every admitted fixed step, but the rows selected
for `FUN_007b2210` still come from the prepared SBFR packet.

Phase 632 reconstructs that selection independently from retail relation state
and requires it to agree with SBFR before the existing reset/solve oracle may
execute.

## Source evidence

The audited executable source is `SHIFT.exe.c` SHA-256:

`512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`.

The relevant control flow is `FUN_007b3f40`.

Direct source audit corrects an older project label: the tested low bit is

```text
relation + 0x70, bit 0
```

rather than a BODY-owned sample `+0x70` field.

For each relation whose bit is set, retail follows the positive endpoint
pointer at relation `+0x7c`, obtains the scalar base from the BODY-owned
sample, and issues these `FUN_007b2210` calls:

| Relation | Scalar-base field | Calls |
|---|---:|---|
| JOINT | sample `+0x30` | `base`, `base+1`, `base+2` |
| HINGE | sample `+0x94` | `base`, `base+1` |
| BAR | sample `+0x30` | `base` |

The array order is JOINT, then HINGE, then BAR.

## CRRF packet

Phase 632 adds
`SHIFT.NativeConstraintRelationResetFramePacket/1` (`CRRF`).

CRRF contains only one normalized low-bit value per source-order relation:

- JOINT relation state bit 0;
- HINGE relation state bit 0;
- BAR relation state bit 0.

Proof flags require explicit relation-state readiness, source-order readiness
and provider absence.

The packet deliberately does not contain scalar bases, reset-node indices,
matrix/RHS values or BODY sample values. Scalar identity is recovered by
joining CRRF to CSRF relation endpoints and GBCF BODY-owned samples.

## Source-faithful selector

`select_fun_007b3f40_reset_nodes()` validates the evidence needed to follow
the retail pointer path:

1. CRRF relation cardinality matches CSRF;
2. endpoint BODY/sample indices are in range;
3. positive endpoint side flag is 1;
4. negative endpoint side flag is 0;
5. paired endpoint scalar bases agree;
6. each type-specific scalar span fits the solver domain.

The selector preserves the retail reset-call sequence, including repeated
nodes if the supplied relation evidence names the same scalar more than once.
It does not invent a requirement that relation spans uniquely cover the whole
solver domain; `FUN_007b3f40` itself has no such check.

The deterministic six-scalar regression uses:

```text
JOINT state = 1 -> calls 0,1,2
HINGE state = 0 -> no calls
BAR state   = 1 -> call 5

reset call sequence = [0,1,2,5]
```

## SBFR evidence join

CRRF does not replace the prepared solver oracle.

`normalize_fun_007b3f40_reset_nodes()` converts the exact call sequence into
the semantic reset-node set, and
`verify_fun_007b3f40_reset_nodes_match()` requires that set to equal the
reset set already stored in SBFR.

A mismatch fails closed before solve execution. The existing
`execute_prepared_builtin_solver_frame()` path therefore remains unchanged:
SBFR still supplies the reset nodes used by the Python/native oracle, while
CRRF independently proves that retail relation state selects the same set.

This avoids recalculating an SBFR expected solution under a different reset
selection.

## Fixed-step integration

`shift_runtime` adds:

```text
--constraint-relation-reset-frame FILE.crrf
```

CRRF requires CSRF, which already requires GBCF and SBFR.

For each admitted fixed step the provider-absent chain is:

```text
CSRF
  -> FUN_007b3ed0 refreshed GBCF
  -> FUN_007bc680 / FUN_007bb8d0 / FUN_007ba570
  -> exact generated matrix/RHS == SBFR gate

CRRF + CSRF + GBCF
  -> FUN_007b3f40 relation-state reset-call selection
  -> normalized reset set == SBFR reset set gate

SBFR
  -> FUN_007b2210
  -> FUN_007b0f20
```

Telemetry reports relation counts, selected relation counts, raw reset-call
count, normalized reset-node count, the SBFR-match flag and per-fixed-step
selection/join count.

## Regression coverage

The native checker covers:

- the exact 3/2/1 call widths;
- the six-scalar `[0,1,2,5]` selection;
- state-cardinality rejection;
- endpoint side-identity rejection;
- repeated reset-call preservation;
- partial relation-layout handling without invented full-domain constraints;
- fail-closed CRRF-to-SBFR reset-set mismatch.

Linux Vulkan CI also exercises the 11-BODY BMW structural fixture with
4 JOINT, 4 HINGE and 20 BAR relations. All relation bits are set, producing
40 reset calls / 40 normalized nodes, and three fixed steps must pass both the
generated matrix/RHS gate and the CRRF-to-SBFR reset gate with zero Vulkan
validation errors.

## Boundary after Phase 632

The provider-absent fixed-step path can now independently reconstruct and
verify the retail `FUN_007b2210` reset selection from relation-state evidence.

Still evidence-gated:

- authentic per-frame BODY transforms/positions and raw relation inputs;
- authentic per-frame production of relation `+0x70` bit 0;
- provider-present dispatch and numeric behavior;
- persistent solved BODY state into vehicle transform/motion integration.

The next safe step is an authentic per-frame state source that feeds the
existing GBCF/CSRF/CRRF gates without weakening any identity or oracle check.
