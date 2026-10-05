# Process 1 — resolved indirect render-manager method +0xca4 access

## Blocker

The shortest playable-slice blocker remains `SHIFT.BMWBody0BindFrameProof/1`.
The complete 17-target direct manager-method branch is negative, while
`SHIFT.PlayerVehicleRenderManagerIndirectDispatch/1` resolves all three frozen
indirect manager calls to exactly two retail machine entry addresses:

```text
0x0045f620  slot 7 / +0x1c
0x0045f630  slot 8 / +0x20
```

No other manager methods are admitted by this phase.

## Acquisition boundary

`0x0045f630` is a normal Ghidra function entry, but `0x0045f620` is currently
labelled `LAB_0045f620`. That is not evidence against it: the retail primary
dispatch table physically stores `0x0045f620`, so the dispatch proof itself
establishes it as a machine entry target.

The ordinary function exporter intentionally uses `getFunctionAt()` and cannot
export such an entry. This phase therefore adds an observational exact-address
slice exporter:

```text
tools/ghidra/ShiftInstructionSliceExporter.java
tools/ghidra/run_shift_instruction_slices.sh
```

It does not create functions, rename symbols, or modify the Ghidra project.

## Contract

`tools/ghidra/analyze_player_vehicle_render_manager_indirect_method_ca4_access.py`
emits:

```text
SHIFT.PlayerVehicleRenderManagerIndirectMethodCa4Access/1
```

For each exact resolved dispatch entry it starts register provenance with the
machine ABI entry state and asks whether a p-code-backed register-relative
memory access at displacement `+0xca4` has exactly:

```text
base origin = entry:ECX
```

A read satisfying that condition joins the already source-backed constructor
layout anchor:

```text
FUN_0045ef50 receiver + 0xca4 = mPlayerVehicleRenderables
```

and promotes only:

```text
player_vehicle_renderables_field_runtime_access_ready=true
```

It still does not prove the loaded value's SMS/RenderHierarchy owner, VHF root
or frame, BODY0 bind-frame equality, or vehicle world transform.

## Negative-proof rule

A positive `+0xca4` access may be accepted as soon as all-path provenance to the
access is closed inside the exported slice.

A negative result is stronger: every resolved target slice must be CFG-complete.
If a reachable branch/fallthrough leaves the slice, the analyzer emits:

```text
indirect-manager-method-ca4-acquisition-incomplete
```

rather than claiming the indirect branch is negative.

## Retail acquisition

```bash
cd /home/pes/nfs-shift-decompilation
git pull

GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_instruction_slices.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/player_vehicle_render_manager_indirect_method_slices.jsonl \
  0x0045f620:0x400 \
  0x0045f630:0x400

python tools/ghidra/analyze_player_vehicle_render_manager_indirect_method_ca4_access.py \
  out/player_vehicle_render_manager_method_ca4_access.json \
  out/player_vehicle_render_manager_indirect_dispatch.json \
  out/player_vehicle_render_manager_indirect_method_slices.jsonl \
  --json-out out/player_vehicle_render_manager_indirect_method_ca4_access.json
```

Only the final JSON report is required for the next decision.

## Consumer

If `player_vehicle_renderables_field_runtime_access_ready=true`, Process 1 traces
only the exact proven loaded `+0xca4` value toward the SMS/RenderHierarchy owner
lane.

If `ready=false` and `negative_branch_closed=true`, both the complete direct and
resolved-indirect manager method hypotheses are closed; the next P1.1 task must
move to an independent owner/root/frame frontier rather than broaden this
manager-method search.
