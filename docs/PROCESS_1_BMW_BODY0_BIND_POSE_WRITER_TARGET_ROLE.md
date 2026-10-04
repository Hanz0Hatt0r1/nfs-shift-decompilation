# Process 1 — BMW BODY0 bind pose-writer target role

## Playable-slice blocker reduced

The first playable Linux slice still cannot produce a retail Phase 706 vehicle
world transform because `SHIFT.BMWBody0BindFrameProof/1` remains negative.

Process 1 #1210 closes the physical parameter-storage ABI of `FUN_007b7840`.
Process 1 #1212 adds path-aware stack-value provenance for those physical stack
slots.  Neither stage is allowed to infer what any parameter means.

This stage narrows the next semantic question:

```text
which exact physical FUN_007b7840 ABI parameter is the target
persistent 0x170-byte BODY pose record?
```

Machine-readable format:

```text
SHIFT.BMWBody0BindPoseWriterTargetRole/1
```

Tool:

```text
tools/ghidra/analyze_bmw_body0_bind_pose_writer_target_role.py
```

No original game execution or new runtime capture is used or required.

## Inputs

The analyzer consumes:

```text
SHIFT.BMWBody0BindPoseWriterABI/1
SHIFT.GhidraFunctionInstructions/2 for exact FUN_007b7840
```

The instruction exporter already carries structured instruction p-code, so this
stage reuses the existing static export format rather than introducing another
Ghidra exporter.

## Reused persistent BODY layout

The native BODY adapter already freezes the persistent `0x170` record layout
used by the explicit outer-update path.

The pose lanes relevant to this proof are:

```text
origin f64:
  +0x00
  +0x08
  +0x10

basis f32:
  +0xd4 +0xd8 +0xdc
  +0xe0 +0xe4 +0xe8
  +0xec +0xf0 +0xf4
```

This stage does not rename any other BODY fields and does not infer bind values
from field labels alone.

## Proof rule

A physical ABI parameter is promoted only when **all** of the following hold:

1. the parameter is register-backed in the proven #1210 ABI;
2. the existing all-path IA-32 register engine traces each relevant object-base
   register at every write back to that one exact entry parameter;
3. structured Ghidra p-code reports a `STORE` for the machine instruction;
4. the union of those stores covers every byte of all three persistent origin
   lanes and all nine persistent basis lanes;
5. no other register-backed entry parameter writes any required pose byte;
6. no non-frame write touching a required pose byte has unresolved or derived
   base provenance.

The promoted role is intentionally narrow:

```text
persistent_BODY_pose_record_target
```

It means that one physical parameter is the object base receiving the complete
persistent pose writes inside `FUN_007b7840`.

## Why byte coverage is used

Origin lanes are f64 values but x86 code can materialize them as multiple
machine stores.  The proof therefore does not require one source instruction per
logical field.  It requires complete byte coverage of the frozen field ranges.

Store width comes from the value input of structured p-code `STORE`, not from a
string guess about the assembly mnemonic.

## Frame-local writes are not object evidence

`EBP`/`ESP` relative stores can numerically use displacements such as `0xd4`, but
those are stack-frame offsets, not BODY offsets.  They are retained for audit
when they overlap the numerical pose range and explicitly excluded from target
role promotion.

## Fail-closed cases

The target role remains negative when:

- any required origin/basis byte is not covered;
- two entry parameters touch required pose bytes;
- more than one parameter independently has complete pose coverage;
- a relevant non-frame base has ambiguous, unknown or derived all-path
  provenance;
- the instruction row is not exact `FUN_007b7840`;
- the #1210 ABI is not storage-ready;
- the upstream ABI already preclaims BODY0/bind semantic results.

In particular:

```text
LEA EAX,[ECX + 4]
```

is not silently converted into an ECX-relative BODY proof.  Pointer arithmetic
needs an explicit offset-aware provenance layer before such a path can be
promoted.

## What this does not prove

Even a positive target-parameter role leaves all of these false:

```text
pose_writer_ABI_semantic_roles_ready = false
BODY0_pointer_at_bind_callsite_ready = false
BODY0_bind_origin_basis_values_ready = false
BODY0_bind_frame_proof_ready = false
```

This stage does **not** prove:

- that `FUN_007b7840` is the retail bind initializer;
- that the target parameter points to BMW chassis BODY0 at either direct caller;
- which stack/register source values form origin or basis;
- x87 value flow into those stores;
- the bind-time matrix;
- Phase 706 commit cadence;
- camera follow or renderer scheduling.

## Next static join

If the target parameter is positive, the remaining bind path becomes finite:

```text
proven FUN_007b7840 BODY-record target parameter
  + #1205/#1210/#1212 callsite physical value provenance
  -> exact selected initialization-call target pointer
  -> BMW chassis BODY0 identity

and separately

origin/basis STORE value inputs
  -> register/stack/x87 source provenance
  -> bind-time origin/basis values
```

Only after both joins agree may Process 1 construct and validate a positive
`SHIFT.BMWBody0BindFrameProof/1` for Process 2 Phase 704–706.

## Vertical-slice position

The renderer-side mechanical path is already present through Process 3 Phase
649, and Phase 707 consumes retail BODY-owner/chassis selection without a
caller-injected identity.  Therefore proving the BODY0 bind transform remains
one of the shortest direct blockers between persistent physics state and a real
moving BMW in the Vulkan scene.
