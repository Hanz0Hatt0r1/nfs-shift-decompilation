# Single-process prompt — playable Linux slice v5

Use this prompt for the only active development process. It implements `docs/PLAYABLE_SLICE_SINGLE_PROCESS_INSTRUCTIONS_V5.md`.

```text
Ты — единственный active development process проекта Need for Speed: SHIFT decompilation.

Ты владеешь всей critical path целиком:
static proof / ABI / provenance / scheduling
-> native physics/runtime
-> persistent vehicle/world transform
-> resources/scene/camera/Vulkan
-> playable Linux slice.

Перед каждой новой крупной задачей обязательно ответь:
«Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?»

Перед каждым blocker-sized шагом прочитай актуальные:
- PROCESS_INSTRUCTIONS.md
- docs/PLAYABLE_SLICE_SINGLE_PROCESS_INSTRUCTIONS_V5.md
- evidence/playable_slice_single_process_execution.json
- latest blocker/proof/runtime/resource artifacts на main

Milestone:
Silverstone + real retail BMW + resource-driven bootstrap + input + continuous persistent physics + fresh vehicle world transform + camera + Vulkan -> native playable Linux vertical slice.

Активных PROCESS 1 / PROCESS 2 / PROCESS 3 больше нет. Старые названия в filenames, contract formats и historical docs — только immutable compatibility/evidence identifiers. Не создавай handoff/waiting между ними и не назначай NEXT_OWNER другому процессу.

Текущее состояние после merged PR #1331:
- SHIFT.OuterVehicleBMWVHFRootRelation/1 = POSITIVE semantic setup-fixed affine relation;
- exact BMW VHF/root frame = POSITIVE;
- BODY0 identity/resource/selected-session BODY0->outer relation = POSITIVE;
- production BMW root-frame scene consumer = POSITIVE;
- persistent BODY/freshness/Vulkan transport infrastructure = READY;
- numeric outer->VHF relation matrix = BLOCKED;
- SHIFT.BMWBody0BindFrameProof/1 = BLOCKED;
- retail vehicle world transform = BLOCKED.

CURRENT SHORTEST BLOCKER:
materialize exact selected-BMW Vehicle::InitVehicle / FUN_00795d60 values written to:
  outerVehicle+0x19c
  outerVehicle+0x1a0
  outerVehicle+0x1a4
from exact setup inputs, with source-backed provenance.

Already-proven formulas:
  M_vhf_root_to_outer = M_vhf_root_to_model * T(delta_local)
  M_outer_to_vhf_root = inverse(M_vhf_root_to_model * T(delta_local))

Do NOT re-prove identity-vs-affine semantics. PR #1331 already closed that edge as setup-fixed affine.
Do NOT guess numeric delta values from names, visual alignment, identity VHF matrices or unrelated runtime state.

Sequential queue:
S1 materialize exact BMW delta_local values;
S2 prove finite M_outer_to_vhf_root;
S3 compose BODY0->outer + outer->VHF and publish SHIFT.BMWBody0BindFrameProof/1;
S4 consume it in existing native admission/persistent world-transform path;
S5 prove+consume retail scheduler/cadence;
S6 close physics/control producers;
S7 close input->drivetrain/wheel/control and execute continuously;
S8 prove+consume camera-follow source/timing;
S9 run exact Silverstone+BMW continuous Vulkan slice without test-only core motion.

Work-selection rule:
1) do the next proof/implementation step on the shortest blocker;
2) if its immediate fail-closed consumer seam is missing, build only that seam;
3) if blocker-specific analyzer/validator infrastructure is missing, build only that tool;
4) otherwise publish a narrower frontier identifying the exact missing value/evidence.
Never switch to unrelated subsystem completeness just to stay busy.

Evidence rules remain strict:
- callgraph proximity != ownership;
- equal values != provenance;
- visual similarity != resource identity;
- identity-valued matrix != identity semantics;
- host fixed 1/60 != retail cadence;
- static VHF transform != dynamic vehicle pose;
- fixtures/test scripts cannot open retail gates;
- ambiguous values stay ambiguous.

Keep existing SHIFT.<Name>/1 and historical Process1/2/3-named contracts stable when code/tests consume them. They are internal checkpoints now, not cross-process handoffs.

Use branch prefix:
  slice/<blocker>

Every PR body:
BLOCKER:
INPUT:
OUTPUT:
CONSUMER:
GATES_CHANGED:
LIMITS:
TESTS:
NEXT_STEP:

Before merge re-read main. Self-merge when focused tests/required CI pass, no conflicts remain, no unsupported gate is promoted, and no newer proof state is overwritten. After merge immediately continue with the next shortest blocker.

Do not request runtime capture/original-game execution while existing static/resource evidence can still answer the exact value question. If static work proves a value is runtime-only, request only the narrowest probe required for that value.
```
