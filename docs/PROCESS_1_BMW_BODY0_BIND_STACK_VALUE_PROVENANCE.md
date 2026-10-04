# Process 1 — BMW BODY0 bind stack-value provenance

## Playable-slice blocker reduced

Process 1 PR #1210 emits `SHIFT.BMWBody0BindPoseWriterABI/1` and converts the broad `FUN_007b7840` ABI problem into exact register storage plus a finite `stack_value_worklist`. The remaining mechanical blocker is the value placed in each proven stack slot at every exact direct caller.

This stage adds:

```text
SHIFT.BMWBody0BindStackValueProvenance/1
```

Tool:

```text
tools/ghidra/analyze_bmw_body0_bind_stack_value_provenance.py
```

It consumes the #1210 ABI result plus targeted `SHIFT.GhidraFunctionInstructions/2` rows. It does not execute the original game and does not request a new runtime capture.

## Proof model

For each exact ABI callsite the analyzer starts at the direct `CALL FUN_007b7840` and walks backwards through machine predecessors. The proof is accepted only while every visited instruction has one unique predecessor on the required lane.

The ABI stack offset, not lexical order alone, decides which PUSH supplies a parameter:

```text
callee Stack[0x4]  <- newest caller PUSH before CALL
callee Stack[0x8]  <- second-newest PUSH
callee Stack[0xc]  <- third-newest PUSH
...
```

The return address is inserted by CALL itself, so the newest explicit caller PUSH becomes callee `Stack[0x4]`.

For a register PUSH, the analyzer continues farther backwards until it finds the nearest older writer of that register. Only direct `MOV` and `LEA` producers with a non-register, non-ESP-relative source are accepted. A `MOV reg,other_reg` remains unresolved rather than silently transferring semantics.

## Fail-closed boundaries

Before the required stack worklist is resolved, the pass rejects:

- a callsite that is not a direct call to exact `0x007b7840`;
- zero or multiple CFG predecessors on the proof lane;
- an intervening CALL;
- POP or an explicit ESP writer between the required argument PUSH instructions;
- a malformed PUSH;
- an unsupported register writer;
- a transitive register source that is not yet reduced to a concrete memory/address/immediate expression;
- an ESP-relative value producer;
- missing caller instruction rows;
- upstream ABI input that already claims stack values or the final BODY0 bind frame.

Therefore the lexical pre-call window emitted by PR #1205 remains discovery evidence only; it is not reused as path proof.

## Retail-shaped lanes already frozen by the supplied instruction export

The user-supplied targeted instruction export fixes two exact direct callsites:

```text
0x007b7840 -> 0x007b7d75 -> FUN_007b7840
0x007b8260 -> 0x007b82f4 -> FUN_007b7840
```

The regression fixture reproduces the exact relevant machine lanes, including the real Ghidra negative-offset spelling and the x87 instructions between the external caller's PUSH operations.

At `0x007b7d75` the nearest PUSH/value producers are structurally:

```text
Stack[0x4]  <- 0x007b7d74 PUSH EDX <- 0x007b7d6e LEA EDX,[EBP + 0xfffffd50]
Stack[0x8]  <- 0x007b7d6b PUSH ECX <- 0x007b7d63 MOV ECX,[EBX + 0xc]
Stack[0xc]  <- 0x007b7d6a PUSH EDI <- 0x007b7d5d MOV EDI,[EBP + -0x24]
Stack[0x10] <- 0x007b7d66 PUSH EAX <- 0x007b7d60 MOV EAX,[EBP + -0x28]
```

At `0x007b82f4`:

```text
Stack[0x4]  <- 0x007b82f1 PUSH ECX <- 0x007b82ee LEA ECX,[EBP + -0x80]
Stack[0x8]  <- 0x007b82ed PUSH EAX <- 0x007b82e6 MOV EAX,[ESI + 0x18]
Stack[0xc]  <- 0x007b82e9 PUSH EDX <- 0x007b82dc MOV EDX,[EBX + 0x8]
Stack[0x10] <- 0x007b82df PUSH ECX <- 0x007b82d3 MOV ECX,[EBX + 0xc]
```

These are physical value expressions only. This stage does **not** call any one of them BODY, bind origin, bind basis, flag, transform, or world pose.

## Current limitation

The repository now contains the generic #1210 ABI join, but the exact retail `functions.jsonl` storage record for `FUN_007b7840` is not available in the current attached/project files. Therefore this stage does not fabricate a committed retail `SHIFT.BMWBody0BindPoseWriterABI/1` input and does not claim a generated retail stack-value artifact.

The new analyzer is the direct reusable consumer for that missing finite input. Once a real #1210 result is present, no new runtime capture is needed: the existing targeted instruction export is sufficient for this pass.

## Preserved semantic blockers

Even after stack values resolve, the following remain false:

```text
pose_writer_ABI_semantic_roles_ready = false
BODY0_pointer_at_bind_callsite_ready = false
BODY0_bind_origin_basis_values_ready = false
BODY0_bind_frame_proof_ready = false
```

The next static proof must inspect `FUN_007b7840` machine/p-code behavior to identify which already-proven physical parameter actually controls the BODY target and which values participate in pose/bind construction. Only after that role proof may the value be joined to exact BMW chassis BODY index 0 and promoted into `SHIFT.BMWBody0BindFrameProof/1`.

## Vertical-slice position

After PR #1208, global vehicle -> BODY-owner -> BMW chassis BODY0 identity is positive. Process 2 already owns persistent BODY/world-transform composition, while Process 3 Phase 649 gates persistent live Vulkan upload on the current Phase 706 state. Therefore this work stays on the shortest remaining transform-producer path rather than reopening renderer transport or unrelated physics kernels.
