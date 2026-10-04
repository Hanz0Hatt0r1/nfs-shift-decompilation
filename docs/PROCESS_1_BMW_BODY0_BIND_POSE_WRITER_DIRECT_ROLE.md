# Process 1 — BMW BODY0 bind pose-writer direct-role proof

## Blocker reduced

`SHIFT.BMWBody0BindFrameProof/1` is still the shortest static semantic blocker in
front of the retail BMW world transform.  The previous Process 1 chain spent its
next provenance work on `FUN_007b7840`, a broad BODY pose/state writer, because
that function can write all persistent origin/basis lanes.

The remaining question was whether any resolved direct invocation of that writer
actually belongs to the SDF/BODY construction lane and can therefore witness
`M_BODY0_bind`.

This proof answers that narrow question with format:

```text
SHIFT.BMWBody0BindPoseWriterDirectRole/1
```

Tool:

```text
tools/ghidra/prove_bmw_body0_bind_pose_writer_direct_role.py
```

## Evidence join

The proof does **not** infer runtime semantics from callgraph adjacency.

It first consumes the existing source/machine-backed
`SHIFT.BodyFrameIntegrationStatic/1` contract, which proves that
`FUN_00770e80` performs two half-step relation refreshes:

```text
0x00770fb7 -> FUN_007b8810
0x00770fe7 -> FUN_007b8810
```

The saved retail Ghidra export is then required to match exact function mnemonic
fingerprints and exact complete direct incoming sets for the following chain:

```text
FUN_00770e80
  -> 0x00770fb7 / 0x00770fe7 -> FUN_007b8810
  -> 0x007b8816              -> FUN_007b8630
  -> 0x007b8729              -> FUN_007b8260
  -> 0x007b82f4              -> FUN_007b7840
```

For `FUN_007b7840` itself the complete resolved direct caller set must be exactly:

```text
0x007b7d75  FUN_007b7840 -> FUN_007b7840   # recursion
0x007b82f4  FUN_007b8260 -> FUN_007b7840   # only external direct call
```

Therefore every resolved direct non-recursive invocation of `FUN_007b7840` is a
descendant of the already proven `FUN_00770e80` relation-refresh path.

## Construction lane retained separately

The proof independently requires the existing SDF/BODY construction edges:

```text
FUN_007b6900 -> 0x007b6e8f -> FUN_007b3670

FUN_007b3670 -> 0x007b3792 -> FUN_007bba90
FUN_007b3670 -> 0x007b37c8 -> FUN_007bbb10
FUN_007b3670 -> 0x007b380b -> FUN_007bbb60
```

None of these exact direct construction edges reaches `FUN_007b7840`.

## Proven conclusion

The following statement is now `proven` for the saved retail direct-call graph:

```text
FUN_007b7840 direct construction-bind-initializer role = rejected
```

This closes the resolved-direct `FUN_007b7840` bind branch.  Process 1 should no
longer spend the BODY0 bind critical path on extracting origin/basis bind values
from the known direct `0x007b82f4` callsite.

The next static target is the actual BODY construction lane:

```text
FUN_007b3670
FUN_007bba90
FUN_007bbb10
FUN_007bbb60
```

The required proof is exact target-pointer/value provenance from those
construction functions into the persistent `0x170` BODY record, followed by the
BMW chassis BODY0 identity join and concrete bind origin/basis materialization.

## Deliberately not proven

This proof does not claim that `FUN_007b7840` can never participate in bind
initialization.  The current saved callgraph proves only resolved direct calls;
it does not prove absence of an unresolved indirect/address-taken invocation.
Accordingly:

```text
FUN_007b7840 any possible bind role = unknown
indirect/address-taken invocation absence = not proven
BODY0 pointer at bind = not ready
BODY0 bind origin/basis values = not ready
SHIFT.BMWBody0BindFrameProof/1 = not ready
```

No original game execution, runtime capture, native runtime implementation,
renderer work, or camera work is introduced.

## Run

```bash
python3 tools/ghidra/prove_bmw_body0_bind_pose_writer_direct_role.py \
  out/shift_ghidra_database \
  --json-out out/bmw_body0_bind_pose_writer_direct_role.json
```

The tool fails closed on binary identity drift, function fingerprint drift,
missing/extra resolved direct callers in the proven chain, missing construction
anchors, or drift in the source-backed half-step relation-refresh contract.
