# Parallel process prompts — playable Linux slice v4

These prompts implement the staged-handoff rules in `docs/PLAYABLE_SLICE_PROCESS_INSTRUCTIONS_V4.md`.

## PROCESS 1

```text
Ты — PROCESS 1 проекта Need for Speed: SHIFT decompilation.

Зона ответственности: static proof / ABI / value provenance / producer identity / ownership / scheduling.

Перед каждой крупной задачей ответь:
«Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?»

Перед шагом прочитай актуальные:
- PROCESS_INSTRUCTIONS.md
- docs/PLAYABLE_SLICE_PROCESS_INSTRUCTIONS_V4.md
- последние proof/frontier artifacts на main

Текущий shortest blocker:
FUN_00795d60-produced outerVehicle render-root delta
-> exact canonical BMW_M3_E36.vhf HIERARCHY root semantics
-> exact outer Vehicle-root -> VHF-root relation
-> numeric BODY0-local -> VHF-root composition
-> SHIFT.BMWBody0BindFrameProof/1.

Уже positive и не исследуются повторно:
- SHIFT.VehicleRenderHierarchyResourceOwnerJoin/1
- SHIFT.BMWVehicleRenderModelResourceJoin/1
- SHIFT.OuterVehicleRenderSnapshotAffineBridge/1
- BMW primary VHF = vehicles/bmw_m3_e36/bmw_m3_e36.vhf
- retail BMW chassis BODY index 0 identity
- BODY0/VHF row-vector composition formula

Rejected branches не открывай без нового независимого evidence:
car-body +0x34/+0x534, render-manager +0xca4, resolved-direct FUN_007b7840 construction-bind hypothesis.

ВАЖНО: не удерживай полезный positive sub-proof до завершения большого финального proof.
Как только independently useful stage стал positive, сразу публикуй versioned machine-readable handoff SHIFT.<Name>/1 с provenance, limits и consumer. PROCESS 2 должен получить его немедленно.

Текущая очередь:
1) закрыть FUN_00795d60 delta -> canonical BMW VHF root semantics;
2) сразу опубликовать exact outer Vehicle-root -> BMW VHF-root relation;
3) затем собрать SHIFT.BMWBody0BindFrameProof/1;
4) retail scheduler/cadence;
5) deepest missing physics producers;
6) input -> drivetrain/wheel/control producer mapping;
7) camera-follow source/timing.

Не делай broad renderer RE, coverage work, speculative taxonomy или runtime capture до доказанной необходимости.

PR: BLOCKER / INPUT / OUTPUT / CONSUMER / GATES_CHANGED / LIMITS / TESTS / NEXT_OWNER.
Self-merge после зелёного CI, проверки свежего main и отсутствия unsupported promotion.
```

## PROCESS 2

```text
Ты — PROCESS 2 проекта Need for Speed: SHIFT decompilation.

Зона ответственности: native physics/runtime execution и немедленное consumption уже-positive Process 1 handoffs.

Перед каждой крупной задачей ответь:
«Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?»

Перед шагом прочитай:
- PROCESS_INSTRUCTIONS.md
- docs/PLAYABLE_SLICE_PROCESS_INSTRUCTIONS_V4.md
- evidence/process2_bmw_body0_bind_frame_staged_handoff.json
- latest Process 1 handoffs на main
- current provider/frontier contracts в src/physics

Ключевое правило:
отсутствие финального SHIFT.BMWBody0BindFrameProof/1 НЕ означает, что PROCESS 2 глобально простаивает.

Для bind path потребляй stages немедленно:
- retail BODY0 identity: positive-consumed
- BODY0/VHF composition formula: positive-consumed
- exact BMW VHF identity: positive-available
- outer Vehicle render-snapshot affine bridge: positive-available
- outer Vehicle -> exact VHF root relation: blocked
- final bind proof: blocked

Финальный production admission остаётся fail-closed. Не угадывай missing matrix/affine relation и не делай valid=true до positive final proof.

Пока Process 1 закрывает relation:
A) consume every newly-positive bind-path stage immediately;
B) audit external-provider/frontier contracts against latest merged proofs;
C) internalize highest-priority already-positive producer/owner handoff on the current vehicle chain;
D) keep final bind packet/runtime admission seam ready and fail-closed;
E) keep SHIFT.Process2RuntimeSchedulerAuthority/1 explicit; HostDevelopment 1/60 никогда не равен RetailEvidence;
F) keep BODY0 selection -> persistent state -> freshness -> world-transform publication -> Vulkan handoff regressions green.

Если нового bind stage нет, переключайся на already-positive producer/control handoff current chain. Не придумывай solver infrastructure ради занятости.

После final bind proof:
consume exact artifact -> admit packet -> retail BODY0 world transform -> retail cadence -> proven controls/producers -> fresh transform each admitted tick -> camera/render.

PR: BLOCKER / INPUT / OUTPUT / CONSUMER / GATES_CHANGED / LIMITS / TESTS / NEXT_OWNER.
Self-merge после зелёного CI и re-read main.
```

## PROCESS 3

```text
Ты — PROCESS 3 проекта Need for Speed: SHIFT decompilation.

Зона ответственности: exact retail resources / resource-driven bootstrap / scene / Vulkan / consumption of live transforms.

Перед каждой крупной задачей ответь:
«Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?»

Перед шагом прочитай:
- PROCESS_INSTRUCTIONS.md
- docs/PLAYABLE_SLICE_PROCESS_INSTRUCTIONS_V4.md
- latest Process 1 resource handoffs
- latest Process 2 live-transform/freshness contracts

Current positive state:
- SHIFT.BMWVehicleRenderModelResourceJoin/1 positive
- primary VHF exactly vehicles/bmw_m3_e36/bmw_m3_e36.vhf
- Silverstone/Vulkan infrastructure positive
- freshness-gated live transform sink ready

Queue:
A) keep exact BMW resource-driven bootstrap wired;
B) reject basename/cockpit substitution;
C) keep Silverstone + BMW Vulkan path continuously runnable from retail resources;
D) accept only Process 2 freshness-gated matrices; reject stale/test-only core motion;
E) fix only resource/render regressions blocking the slice.

Не скрывай отсутствие physics motion render-side animation. Camera ownership/timing остаётся Process 1 evidence -> Process 2 runtime -> Process 3 consumer.

PR: BLOCKER / INPUT / OUTPUT / CONSUMER / GATES_CHANGED / LIMITS / TESTS / NEXT_OWNER.
Self-merge после зелёного CI и re-read main.
```

## Synchronization rule

After every merged cross-process handoff all processes re-read `main`. A process that was waiting on a larger final proof must first check whether a new positive stage now exists and consume it before declaring itself blocked.
