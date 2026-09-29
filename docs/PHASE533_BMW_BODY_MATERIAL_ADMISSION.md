# Phase 533 — canonical BMW body material admission

Phase 533 adds one orchestration boundary over the Phase 528–532 material
pipeline. It runs every selected canonical BMW M3 E36 body primitive through
the real BFF material slice builder independently and preserves both successful
and blocked results.

## Input

The normal retail invocation uses:

- BMW_M3_E36.bff as the primary archive;
- BMW_M3_E36_Cockpit.bff as a supplemental vehicle archive;
- RENDER.bff as the renderer shader/resource archive;
- evidence/bmw_m3_e36_kit00_body_loda.golden.json as the canonical six-primitive
  body definition.

Example:

    python shift_importer.py bmw-body-material-admission \
      BMW_M3_E36.bff out/bmw-body-admission \
      --supplemental-bff BMW_M3_E36_Cockpit.bff \
      --supplemental-bff RENDER.bff \
      --vulkan-output-dir out/bmw-body-vulkan

By default every primitive recorded by the golden manifest is attempted.
--primitive-index may be repeated to run a strict subset.

## Per-primitive isolation

One material failure does not abort the remaining primitive analysis. Each row
records:

- canonical primitive index;
- material MTX/BMT reference;
- ready/blocked/error state;
- exact blocking reasons;
- 64-byte-hex shader permutation identity when proven.

Exceptions from one retail resource chain are converted into an explicit
primitive blocker instead of discarding already-produced evidence from other
draws.

## Admission set

Every ready primitive slice is passed to SHIFT.BMWMaterialSliceSet/1. Therefore
the admitted subset still has to agree on exact MEB identity, neutral mesh,
RenderCommand mesh, world transform and DDS provenance.

Ready shader permutation identities are grouped separately from primitive
draws. This matters because the six canonical body primitives use fewer unique
materials/permutations than draw ranges.

If --vulkan-output-dir is supplied and the admitted slice set validates, the
same set is passed directly to the existing Phase 527
BMWMaterialSliceVulkanSet path. Each draw retains its own shader, DDS,
constants, cull, depth and blend state before Phase 525 preparation and
Phase 526 native execution.

## Readiness semantics

The top-level ready flag is intentionally strict. It is true only when every
selected canonical primitive is ready, the combined material slice set is
ready, and any requested Vulkan handoff is ready.

A report with at least one ready primitive but an incomplete body is partial.
This allows the first proven non-paint permutations to be retained without
claiming complete BMW body parity.

## Evidence boundary

Repository CI validates orchestration, fail-closed behavior and Vulkan handoff
with deterministic fixtures. Phase 533 does not itself claim new retail
non-paint shader permutations unless the command is run against the actual
retail BMW/RENDER archives.

The next evidence step is to execute this admission command against the retail
BMW_M3_E36, cockpit and RENDER BFFs and persist the resulting per-primitive
blocker/permutation matrix.
