# Phase 149 — BMW runtime golden same-instance requirement

`SHIFT.BMWRuntimeGoldenGate/1` now requires `SHIFT.D3D9RuntimeBindingEvidence/1`
`same_instance_gate.ready == true` before a captured BMW frame can become `ready=true`.

This composes the runtime evidence layers rather than duplicating declaration matching.
The gate still separately checks shader identity, resource identity, declaration parity,
vertex-input parity, indexed-draw correlation and RenderCommand constant parity.

## Consequence

An old runtime report with only observational fields is intentionally blocked by the
unified golden gate until it is regenerated with the strict same-instance evidence.

## Boundary

This does not claim that a capture exists. The current blocker remains obtaining an
authentic runtime capture from the retail process and feeding it through the strict trace.