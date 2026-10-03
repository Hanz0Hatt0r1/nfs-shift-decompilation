# Ghidra vehicle outer-update caller frontier

`tools/ghidra/build_vehicle_outer_update_caller_frontier.py` moves the static
frontier upward from the now-proven BODY integration schedule. Its output format
is `SHIFT.GhidraVehicleOuterUpdateCallerFrontier/1`.

The result below was checked against the existing offline Ghidra export already
present in `out.zip` (`out/shift_ghidra_database`). No game execution, runtime
capture, or new Ghidra export was required.

## Direct callers of `FUN_00770e80`

The current `callgraph.jsonl` contains exactly two direct callers of the proven
outer-update anchor:

```text
0x00794a6e  FUN_00794a30 -> FUN_00770e80
0x0079b310  FUN_0079b2d0 -> FUN_00770e80
```

Ghidra metadata records:

```text
FUN_00794a30
  size: 475
  convention: __thiscall
  signature: undefined FUN_00794a30(void * this,
              undefined4 param_1, undefined4 param_2,
              undefined4 param_3, int param_4, char param_5)

FUN_0079b2d0
  size: 411
  convention: __fastcall
  signature: undefined4 FUN_0079b2d0(void * param_1, undefined4 param_2)
```

Neither function is renamed or assigned vehicle/input/frame semantics by this
evidence.

## Shared direct-call shape

In both functions the call to `FUN_00770e80` is the first direct call, followed
by the same four direct callees in the same order:

```text
index 0  FUN_00770e80
index 1  FUN_0078ef00
index 2  FUN_00793ca0
index 3  FUN_007aa750
index 4  FUN_007851d0
```

After that prefix the two functions diverge. This is strong structural evidence
that they share an orchestration prefix, but it is **not** class identity,
function equivalence, frame-loop proof, or input ownership proof.

The analyzer records the common prefix mechanically instead of assigning a name.

## Upstream ownership split

The two direct callers have different incoming-call evidence.

`FUN_00794a30` has three direct call sites, all in `FUN_00713050`:

```text
0x00713112 -> FUN_00794a30
0x00713135 -> FUN_00794a30
0x007131b5 -> FUN_00794a30
```

The next two direct incoming levels are:

```text
0x00715434  FUN_00715380 -> FUN_00713050
0x00715602  FUN_007155e9 -> FUN_00715380   # outside default depth=2 report
```

With the default `--upstream-depth 2`, the next instruction-export targets above
that branch are therefore `FUN_00713050` and `FUN_00715380`.

By contrast, `FUN_0079b2d0` has **no direct incoming call edge** in the current
Ghidra callgraph. The analyzer emits this as
`no-direct-upstream-caller-in-export`. It does not conclude that the function is
a root. Indirect dispatch, callback tables, unrecognized references, or an
external entry remain possible.

`switches.jsonl` additionally records an internal computed-jump candidate in
`FUN_0079b2d0`:

```text
0x0079b2ec  JMP dword ptr [EAX*0x4 + 0x79b46c]
```

with six recovered local destinations. This constrains the function's internal
control flow, but does not explain who invokes it.

## Current targeted instruction worklist

At the default upstream depth the new worklist is:

```text
0x00794a30
0x0079b2d0
0x00713050
0x00715380
```

These are target-selection addresses only. The next instruction/p-code pass can
ask narrower questions such as:

- what object/register is passed from either caller into `FUN_00770e80`;
- whether both caller variants pass the same object slot/layout;
- which arguments differ between the two variants;
- whether `FUN_00713050` selects between multiple vehicle instances or repeated
  substeps;
- whether input/control values can be followed into the outer-update arguments;
- whether a concrete indirect/table reference explains the otherwise ownerless
  `FUN_0079b2d0` branch.

None of those meanings is promoted until instruction/reference evidence proves
it.

## Run

The existing export is enough to regenerate the frontier:

```bash
python3 tools/ghidra/build_vehicle_outer_update_caller_frontier.py \
  out/shift_ghidra_database \
  --upstream-depth 2 \
  --json-out out/vehicle_outer_update_caller_frontier.json \
  --targets-out out/vehicle_outer_update_caller_targets.txt
```

For the next instruction-level pass:

```bash
mapfile -t TARGETS < out/vehicle_outer_update_caller_targets.txt

GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/vehicle_outer_update_caller_instructions.jsonl \
  "${TARGETS[@]}"
```

The new Ghidra run is not needed to establish the caller graph above; it is only
needed when the instruction/p-code semantics of these four functions become the
next blocker.

## Evidence boundary

Proven by this layer:

- the exact two direct callers of `FUN_00770e80` in the saved export;
- each caller's exact ordered direct-call list;
- their five-target common direct-call prefix;
- the three direct `FUN_00713050 -> FUN_00794a30` sites;
- the bounded direct upstream path through `FUN_00715380`;
- absence of a direct incoming edge to `FUN_0079b2d0` in this export;
- the recorded computed-jump candidate inside `FUN_0079b2d0`.

Not proven:

- that either caller is the rendered-frame scheduler;
- that either caller owns a vehicle object;
- that both callers operate on the same class/object layout;
- input/controller ownership;
- meaning of the shared helper callees;
- why `FUN_0079b2d0` has no direct incoming call;
- any virtual/callback target not explicitly present in the export.
