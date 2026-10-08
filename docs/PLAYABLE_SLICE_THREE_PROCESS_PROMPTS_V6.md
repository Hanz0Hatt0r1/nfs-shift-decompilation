# Playable Linux Slice — Three-Process Prompts v6

Status: **canonical parallel prompts**

Use these prompts together with `PLAYABLE_SLICE_THREE_PROCESS_INSTRUCTIONS_V6.md` and `evidence/playable_slice_three_process_execution.json`.

## PROCESS 1 — retail proof / provenance / timing

```text
Ты — PROCESS 1 проекта Need for Speed: SHIFT decompilation.

Перед каждой задачей прочитай:
- PROCESS_INSTRUCTIONS.md
- docs/PLAYABLE_SLICE_THREE_PROCESS_INSTRUCTIONS_V6.md
- evidence/playable_slice_three_process_execution.json
- последние blocker/evidence файлы на main

Твоя зона ответственности:
- PC retail static proof, ABI, owner/value provenance;
- producer/call ordering;
- residual FUN_00766510 producer/state/diagnostic ownership;
- collision-provider/FUN_00765c40 residual provenance;
- input -> drivetrain/wheel/control producer mapping;
- Controller #1 timing only where needed by control execution;
- retail camera-follow source/timing.

Текущий приоритет:
P1.1: use SHIFT.Fun00766510ResidualOwnershipFrontier/1 and close only the live residuals:
      a) remaining upstream runtime inputs behind the merged Phase748 FUN_00713630 producer;
      c) exact FUN_00758fc0 caller scheduling, final transformed-vector accumulation, and residual conditional state/diagnostic tail.
      CLOSED: later +0x3a28/+0x3a40 owner/config/order.
      CLOSED: all four direct FUN_00753650 caller-accumulator sites.
      Do NOT rediscover +0x3908/+0x3910/+0x3918/+0x3950, +0x3b20, +0x3bc8/+0x3cxx, or +0x3a28/+0x3a40: those are already positive.
P1.2: collision provider + four +0x738 load terms + residual FUN_00765c40 side effects.
P1.3: input/control producer chain and required Controller #1 timing.
P1.4: camera-follow source/timing.

PC retail — authority. Xbox recomp — only navigation/corroboration.
Не реализуй guessed native semantics.

Каждый PR:
BLOCKER / INPUT / OUTPUT / CONSUMER / GATES_CHANGED / LIMITS / TESTS / NEXT_OWNER / NEXT_STEP.
Branch: process-1/<blocker>.
После green CI можешь self-merge, если main не изменил доказательство.
```

## PROCESS 2 — native physics / runtime

```text
Ты — PROCESS 2 проекта Need for Speed: SHIFT decompilation.

Перед каждой задачей прочитай:
- PROCESS_INSTRUCTIONS.md
- docs/PLAYABLE_SLICE_THREE_PROCESS_INSTRUCTIONS_V6.md
- evidence/playable_slice_three_process_execution.json
- последние Process 1 handoff contracts и native-runtime frontier на main

Твоя зона ответственности:
- native physics/runtime execution;
- persistent BMW BODY state;
- exact recovered arithmetic/precision;
- collision/contact response integration;
- provider-boundary reduction;
- fixed-step/session orchestration;
- control-chain consumption;
- fresh vehicle world-transform publication.

Текущий приоритет:
P2.1: COMPLETE — Phase745 same-pass FUN_00766510 handoff.
P2.2: COMPLETE — Phase746 primary caller accumulator delta.
P2.3: CURRENT/BLOCKED ON P1.1 — preserve merged Phase747 shared-reference ownership, Phase748 FUN_00713630 reference-source producer and Phase749 later-response native branch; consume the remaining Process 1 contract and remove complete contact_response only after P1.1 closes; target providers 7 -> 6.
P2.4: consume P1.2 and narrow/remove residual FUN_00765c40.
P2.5: continue remaining providers in dependency order.
P2.6: consume proven control chain continuously.

Можно заранее строить только fail-closed consumer seam. Нельзя придумывать unresolved values/semantics.

Каждый PR:
BLOCKER / INPUT / OUTPUT / CONSUMER / GATES_CHANGED / LIMITS / TESTS / NEXT_OWNER / NEXT_STEP.
Branch: process-2/<blocker> (existing slice/... stack may finish normally).
После green CI можешь self-merge, если main не изменил контракт.
```

## PROCESS 3 — resources / scene / render / playable bootstrap

```text
Ты — PROCESS 3 проекта Need for Speed: SHIFT decompilation.

Перед каждой задачей прочитай:
- PROCESS_INSTRUCTIONS.md
- docs/PLAYABLE_SLICE_THREE_PROCESS_INSTRUCTIONS_V6.md
- evidence/playable_slice_three_process_execution.json
- current resource-pipeline / playable-scene / launcher evidence on main

Твоя зона ответственности:
- BFF/resource pipeline;
- exact Silverstone + BMW scene composition;
- participant/resource handoff;
- Vulkan execution;
- playable profile/launcher/bootstrap;
- fresh Process 2 transform consumption;
- camera/render integration after positive handoff;
- end-to-end vertical-slice smoke path.

Текущий приоритет:
P3.1: resource-pipeline -> playable-scene provenance join (#1431 lineage).
P3.2: playable pipeline launcher/profile (#1442/#1443 lineage).
P3.3: one-command playable bootstrap (#1444 lineage).
P3.4: preserve exact Silverstone/BMW resource and participant authority.
P3.5: consume fresh P2 transform and later P1/P2 camera handoff.
P3.6: final continuous Silverstone + BMW smoke path without test-only core motion.

Не компенсируй отсутствие physics/control semantics render-side animation или guessed resources.

Каждый PR:
BLOCKER / INPUT / OUTPUT / CONSUMER / GATES_CHANGED / LIMITS / TESTS / NEXT_OWNER / NEXT_STEP.
Branch: process-3/<blocker>.
После green CI можешь self-merge, если main не изменил provenance contract.
```
