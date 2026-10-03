# Ghidra BODY / vehicle update schedule frontier

`tools/ghidra/build_body_update_schedule_frontier.py` recovers a narrow direct-call
schedule around the already proven BODY/vehicle writer anchors. Its output format
is `SHIFT.GhidraBodyUpdateScheduleFrontier/1`.

This evidence was checked against the existing Ghidra export for:

- program: `SHIFT.exe`;
- PE MD5: `705af8b420e5eb1e3834ac43d5533c6b`;
- language: `x86:LE:32:default`;
- image base: `0x00400000`;
- pointer size: 4 bytes.

No game execution or runtime capture is required.

## Main result

The existing direct callgraph closes substantially more of the outer physics
ordering than the earlier subsystem-wide frontier showed.

`FUN_00770e80` contains exactly two direct calls to `FUN_0076d100`:

```text
0x00770f8f -> FUN_0076d100
...
0x00770fbf -> FUN_0076d100
```

The same anonymous helper, `FUN_00765470`, appears after both passes. It is the
unique repeated helper in those windows that directly calls both the recovered
SDF solve boundary and the post-solve writer.

Inside `FUN_00765470` the direct-call order is:

```text
0x007657b2 -> FUN_00763570
0x007657bd -> FUN_007b3f40
0x007657c8 -> FUN_007b4110
```

Therefore the following ordering is direct-callgraph-backed:

```text
FUN_0076d100
  -> FUN_00765470
       -> FUN_00763570
       -> FUN_007b3f40
       -> FUN_007b4110
```

The recovered source already establishes that `FUN_00763570` reaches the
wheel-local `FUN_00755f80` triplet writer, while `FUN_007b3f40` is the recovered
SDF solve orchestration and `FUN_007b4110` applies post-solve BODY accumulator
feedback. This report proves their call order in this anonymous helper; it does
not claim that all three operate on the same BODY instance.

## Inside `FUN_0076d100`

The same export proves this direct-call subsequence:

```text
0x0076d12b -> FUN_00765c40
0x0076d132 -> FUN_00758b50
0x0076d139 -> FUN_00766510
0x0076d2c1 -> FUN_00769ef0
```

`FUN_00769ef0` is recovered structurally rather than named semantically. It is the
unique direct callee of `FUN_0076d100` which calls both the known contact-outer
path and the known BODY motion read gate. Its local order is:

```text
0x0076a1c7 -> FUN_007675f0
0x0076a1e8 -> FUN_007682c0
```

So the current static schedule is at least:

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
  -> ...
  -> FUN_0076d100
       -> same recovered pass ordering
  -> FUN_00765470
       -> same recovered solver/post-solve ordering
```

This is stronger than the earlier statement that `FUN_00770e80` merely executes
two `FUN_0076d100` passes. It places known wheel/contact accumulator work,
motion-side readers, the wheel shared-triplet pass, SDF solve and post-solve
feedback into a repeatable direct-call schedule.

## Still unresolved

The schedule does **not** reveal the missing persistent-state writer by itself.
In particular it does not prove:

- a write from BODY `+0x48..+0x70` into `+0x18..+0x28`;
- a write into the motion triplet `+0x78/+0x80/+0x88`;
- origin `+0x00/+0x08/+0x10` integration;
- basis `+0xd4..+0xf4` integration;
- that a register in one of the anonymous helpers is a BODY pointer;
- that wheel-local `FUN_00755f80` state aliases chassis BODY state;
- the semantic identity of `FUN_00765470` or `FUN_00769ef0`.

Those remain explicit blockers until instruction/p-code and pointer-provenance
evidence establish concrete loads/stores.

## Indirect-call blockers

The schedule analyzer keeps computed calls visible for all proven anchors and the
newly recovered anonymous helpers. In the current export the relevant unresolved
indirect sites are both inside `FUN_007b3f40`:

```text
0x007b3f8c
0x007b4102
```

No virtual target is assigned to either site from callgraph evidence alone.
Vtable/object provenance must resolve them separately.

## Narrow next instruction targets

Running the schedule builder on the current export produces this priority list:

```text
0x00765470
0x00769ef0
0x007b8810
0x007b3e90
0x00758810
0x00754880
0x007b2270
0x007653f0
```

The first two are the uniquely recovered orchestration candidates. The remaining
entries are repeated or low-fan-in helpers directly adjacent to the recovered
schedule. Generic high-fan-in support functions remain visible in the full
ordered call lists but are deliberately not auto-selected.

`FUN_007b8810` is especially useful as a next static target: it is called after
`FUN_00765470` in both outer-pass windows and directly calls `FUN_007b3ed0`, but
that adjacency is not enough to assign it a lifecycle or refresh name.

## Run

```bash
python3 tools/ghidra/build_body_update_schedule_frontier.py \
  out/shift_ghidra_database \
  --json-out out/body_update_schedule_frontier.json \
  --targets-out out/body_update_schedule_targets.txt
```

The existing export is sufficient for that step. A new Ghidra run is needed only
for the next instruction/p-code layer:

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

That output can then be passed through the existing register-relative access
analyzer:

```bash
python3 tools/ghidra/analyze_register_relative_accesses.py \
  out/body_update_schedule_instructions.jsonl \
  --json-out out/body_update_schedule_register_accesses.json
```

A candidate persistent-state bridge should only be promoted after the exact
instruction stream proves both object-pointer provenance and the relevant
`LOAD`/`STORE` offset relationship.

## Evidence boundary

`FUN_00765470` and `FUN_00769ef0` remain anonymous, `promoted=false` candidates.
The only newly proven property is their direct-callgraph position and ordering
relative to already established anchors. No function rename, BODY field semantic
promotion, virtual-call target, pose integrator or Linux runtime behavior is
introduced by this layer.
