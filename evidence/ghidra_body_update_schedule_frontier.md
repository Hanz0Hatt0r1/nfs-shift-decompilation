# Ghidra BODY / vehicle update schedule frontier

`tools/ghidra/build_body_update_schedule_frontier.py` recovers a narrow direct-call
schedule around the already proven BODY/vehicle writer anchors. Its output format
is now `SHIFT.GhidraBodyUpdateScheduleFrontier/2`.

This evidence is based on the existing Ghidra export for:

- program: `SHIFT.exe`;
- PE MD5: `705af8b420e5eb1e3834ac43d5533c6b`;
- language: `x86:LE:32:default`;
- image base: `0x00400000`;
- pointer size: 4 bytes.

No game execution or runtime capture is required.

## What changed in v2

The earlier schedule report stopped at `FUN_007b4110` and therefore treated the
persistent motion/pose writer as unresolved. That became stale after static source
and retail-PE corroboration established the persistent BODY integration contract
`SHIFT.BodyFrameIntegrationStatic/1`.

The schedule analyzer now imports two already proven anchors from that contract:

```text
FUN_007b2270  BODY-array integration loop
FUN_007bab70  persistent BODY integration primitive
```

The tool does not derive their field semantics from the Ghidra callgraph. It only
requires the direct-call edges needed to place those proven primitives in the
existing half-step schedule.

## Direct-call schedule

`FUN_00770e80` contains exactly two direct calls to `FUN_0076d100`:

```text
0x00770f8f -> FUN_0076d100
...
0x00770fbf -> FUN_0076d100
```

The same anonymous helper, `FUN_00765470`, appears after both passes. In v2 it is
selected only if its direct callees contain all three of:

```text
FUN_007b3f40  SDF solve
FUN_007b4110  post-solve BODY accumulator feedback
FUN_007b2270  BODY-array integration loop
```

Inside `FUN_00765470` the required direct-call order is:

```text
0x007657b2 -> FUN_00763570
0x007657bd -> FUN_007b3f40
0x007657c8 -> FUN_007b4110
0x0076582a -> FUN_007b2270
```

`FUN_007b2270` must then contain exactly one direct call to `FUN_007bab70`.
The separately corroborated BODY integration contract establishes that
`FUN_007b2270` iterates the BODY array and that `FUN_007bab70` performs the
persistent motion/origin/basis update.

Therefore the static schedule is now linked across the former persistent-state
writer gap:

```text
FUN_00770e80
  -> FUN_0076d100
       -> FUN_00765c40
       -> FUN_00758b50
       -> FUN_00766510
       -> FUN_00769ef0
            -> FUN_007675f0
            -> FUN_007682c0
  -> FUN_00765470
       -> FUN_00763570
       -> FUN_007b3f40
       -> FUN_007b4110
       -> FUN_007b2270
            -> FUN_007bab70
  -> FUN_007b8810
  -> FUN_0076d100
       -> same recovered pass ordering
  -> FUN_00765470
       -> same solver/post-solve/BODY-integration ordering
  -> FUN_007b8810
```

This is direct-call ordering evidence plus imported source/machine-code semantics
for the two BODY integration anchors. It is not a claim that callgraph structure
alone proves field writes.

## `FUN_0076d100` tail

The same direct-call evidence still recovers the anonymous `FUN_00769ef0` helper.
It is the unique direct callee of `FUN_0076d100` that calls both the known
contact-outer path and the BODY motion read gate, in this order:

```text
0x0076a1c7 -> FUN_007675f0
0x0076a1e8 -> FUN_007682c0
```

No semantic rename is assigned to `FUN_00769ef0`.

## Fail-closed conditions

Version 2 aborts instead of weakening the conclusion when any of the following
changes in the export:

- `FUN_00770e80` no longer has exactly two direct `FUN_0076d100` calls;
- the repeated between-pass helper is absent or ambiguous;
- its required `FUN_00763570 -> FUN_007b3f40 -> FUN_007b4110 -> FUN_007b2270`
  ordering is not preserved;
- `FUN_007b2270` does not have exactly one direct call to `FUN_007bab70`;
- the `FUN_0076d100` or `FUN_00769ef0` required ordering changes;
- any required anchor is absent from `functions.jsonl`.

Indirect calls remain explicit blockers rather than guessed virtual targets.

## What remains unresolved

The persistent BODY writer bridge itself is no longer the main static blocker.
The remaining higher-level boundaries include:

- caller ownership above `FUN_00770e80`;
- exact vehicle/update-loop scheduling relative to rendered frames;
- higher-level input/control ownership feeding that vehicle update path;
- semantic identity of `FUN_00765470`, `FUN_00769ef0` and adjacent helpers;
- the two unresolved indirect calls in `FUN_007b3f40`;
- constructor/destructor/vptr/object-lifetime proof for PhysicsParticipant/vehicle
  objects beyond heuristic vtable candidates.

These should remain separate frontiers rather than being inferred from the now
closed BODY integration path.

## Run

The existing full Ghidra export is sufficient for the schedule report:

```bash
python3 tools/ghidra/build_body_update_schedule_frontier.py \
  out/shift_ghidra_database \
  --json-out out/body_update_schedule_frontier.json \
  --targets-out out/body_update_schedule_targets.txt
```

The generated target list deliberately excludes the already proven
`FUN_007b2270`/`FUN_007bab70` anchors and keeps unproven adjacent helpers as the
next targeted instruction-export worklist.

If instruction-level evidence is needed for those remaining helpers:

```bash
mapfile -t TARGETS < out/body_update_schedule_targets.txt

GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/body_update_schedule_instructions.jsonl \
  "${TARGETS[@]}"
```

Then audit register-relative loads/stores without promoting object identity by
syntax alone:

```bash
python3 tools/ghidra/analyze_register_relative_accesses.py \
  out/body_update_schedule_instructions.jsonl \
  --json-out out/body_update_schedule_register_accesses.json
```

## Evidence boundary

`FUN_00765470` and `FUN_00769ef0` remain anonymous, `promoted=false` candidates.
The BODY integration semantics belong to the separately source/machine-code-backed
`SHIFT.BodyFrameIntegrationStatic/1` contract. Version 2 adds only the strict
callgraph schedule link from post-solve feedback through `FUN_007b2270` to
`FUN_007bab70`. No function rename, virtual-call target, or Linux runtime behavior
is introduced by this layer.
