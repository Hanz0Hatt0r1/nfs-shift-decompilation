# Process 1 — BMW BODY0 bind pose-writer ABI join

## Playable-slice blocker reduced

Process 1 #1205 recovers all-path physical register origins at every exact direct
callsite of the broad BODY pose-writer candidate `FUN_007b7840`, but deliberately
leaves parameter storage and stack arguments unbound.

This stage joins that physical callsite evidence to the ordinary Ghidra
`functions.jsonl` function ABI record and emits:

```text
SHIFT.BMWBody0BindPoseWriterABI/1
```

Tool:

```text
tools/ghidra/join_bmw_body0_bind_pose_writer_abi.py
```

It does not execute the original game and does not require a new runtime capture.

## Inputs

```text
SHIFT.BMWBody0BindCallsiteRegisterProvenance/1
SHIFT.GhidraDatabase/1 functions.jsonl
```

The exact target is fixed to retail `FUN_007b7840` at `0x007b7840`.

The `functions.jsonl` record already retains Ghidra's physical parameter storage,
for example:

```text
ECX:4 (auto)
EDX:4
Stack[0x4]:4
Stack[0x8]:4
```

The join uses those strings only as ABI storage observations. Ghidra parameter
names and reported types are retained for audit but never promoted to semantic
roles.

## Register-backed parameters

For register storage the join maps byte/word aliases to the containing IA-32
register tracked by the #1205 fixed-point engine and attaches the exact
`registers_before_call` origin set for every frontier callsite.

A register value is ready only when the predecessor analysis reports one exact
origin and no `unknown:`, `ambiguous:`, `derived:` or `value:` origin.

This closes the mechanical question:

```text
Ghidra parameter ordinal -> physical register storage -> all-path callsite value origin
```

without declaring what the parameter means.

## Stack-backed parameters

A storage such as `Stack[0x8]:4` proves the physical ABI slot but does not prove
which value the caller places there. The result therefore emits an exact finite
`stack_value_worklist` containing every stack offset/width required by the
retail pose-writer ABI.

The next stack stage must track ESP changes and PUSH/MOV stores path-wise at every
relevant caller. A lexical pre-call window is not accepted as proof.

## Remaining semantic boundary

This stage intentionally keeps these facts false:

```text
pose_writer_ABI_semantic_roles_ready      = false
BODY0_pointer_at_bind_callsite_ready      = false
BODY0_bind_origin_basis_values_ready      = false
BODY0_bind_frame_proof_ready              = false
```

In particular, neither `ECX`, parameter ordinal 0, a Ghidra name such as `this`,
nor a reported pointer type is enough to claim a BODY pointer.

The next source-backed proof must inspect `FUN_007b7840` machine/p-code behavior
to establish which physical parameter controls the target BODY, flags and pose
source values. If the proven ABI contains stack parameters, the new finite stack
worklist must also be resolved.

## Fail-closed policy

The join rejects:

- a physical report that does not cover every frontier callsite;
- a target other than exact `0x007b7840`;
- missing, duplicated, external or thunk target functions;
- missing calling-convention or parameter-storage metadata;
- unsupported/composite storage not represented by the current IA-32 model;
- a register parameter whose containing register is absent from the #1205 report.

It records but does not promote Ghidra semantic parameter names/types.

## Vertical-slice position

After Process 1 #1208, retail BODY-owner identity is positive. Process 2 Phases
704–706 and Process 3 Phases 645–648 already provide the composition, persistent
matrix ABI and Vulkan transport. The remaining transform producer boundary is
therefore dominated by the static `M_BODY0_bind` witness plus proven Phase 706
commit scheduling.

This ABI join narrows the former open-ended pose-writer ABI question to concrete
register origins and exact stack slots, moving directly toward
`SHIFT.BMWBody0BindFrameProof/1`.
