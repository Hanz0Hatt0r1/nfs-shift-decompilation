# Process 1 — player vehicle render-manager global xref ranking

## Playable-slice blocker

The remaining direct transform blocker is still:

```text
outer Vehicle/car-body runtime owner
  -> canonical BMW graphical/VHF vehicle-root owner or fixed affine relation
```

Two independent render-side frontiers are now available on `main`:

1. `render-manager receiver + 0xca4 = allocation labelled mPlayerVehicleRenderables`;
2. `HDVehicle -> car-body/CHASSIS -> +0x534 -> FUN_007a3d60` vehicle visual/LOD lane.

The missing step is not another broad renderer search. It is selecting the exact
runtime users of the candidate render-manager global and testing whether one of
them physically joins those two frontiers.

## Input from the targeted global-reference exporter

Phase #1282 added `SHIFT.GhidraGlobalReferences/1` and selected
`DAT_00bc185c` as the immediate candidate global. The raw database records 116
references but not their containing functions. The new exporter supplies exact
xref instruction addresses and function ownership.

Run the existing export first:

```bash
cd /home/pes/nfs-shift-decompilation

GHIDRA_HOME=/opt/ghidra \
./tools/ghidra/run_shift_global_references.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/player_vehicle_render_manager_global_refs.jsonl \
  0x00bc185c
```

## Bounded ranker

`tools/ghidra/rank_player_vehicle_render_manager_global_refs.py` consumes that
single exact global-reference row and the normal saved Ghidra evidence database.
It validates the retail executable identity and exact mnemonic fingerprints for:

```text
FUN_0045ef50  render-manager constructor / +0xca4 anchor
FUN_0076df50  HDVehicle::Init anchor
FUN_007633b0  HDVehicle control bridge
FUN_007ac4d0  car-body/CHASSIS initializer
FUN_007a3d60  vehicle visual/LOD setup
```

For every function that references the candidate global, it computes bounded
**direct-call-only** distances in both directions to those anchors. Indirect calls
are deliberately excluded.

The ranking is discovery evidence only. A short callgraph distance does not prove
pointer identity, ownership, collection membership, or coordinate-frame
identity.

Run:

```bash
python tools/ghidra/rank_player_vehicle_render_manager_global_refs.py \
  out/shift_ghidra_database \
  out/player_vehicle_render_manager_global_refs.jsonl \
  --json-out out/player_vehicle_render_manager_global_xref_rank.json
```

The output format is:

```text
SHIFT.PlayerVehicleRenderManagerGlobalXrefRank/1
```

and contains a bounded `selected_instruction_export_functions` worklist. The
default cap is 24 functions and can be changed with `--limit`.

## Why this reduces the blocker graph

Without the ranker, the global candidate can produce a large function set and
would force another broad manual pass. With it, the next instruction export is
restricted to functions that are actually closest to the already proven
vehicle/car-body/visual lane.

The next proof is therefore finite:

```text
selected candidate-global user
  + concrete runtime access to render-manager +0xca4
  + concrete vehicle/car-body/visual pointer/value flow
    -> exact player vehicle renderable owner
```

Only after that owner is proven should the work continue to VHF hierarchy/root
identity or a fixed affine relation.

## Deliberate non-claims

The ranker keeps all transform gates closed:

```text
player_vehicle_renderables_owner_join_ready = false
outer_vehicle_root_to_VHF_vehicle_root_ready = false
BODY0_bind_frame_proof_ready = false
vehicle_world_transform_ready = false
```

It also does not promote:

- `DAT_00bc185c` to a render-manager singleton merely because it is the current
  candidate;
- callgraph proximity to pointer identity;
- `mPlayerVehicleRenderables` collection membership to VHF root identity;
- an indirect call edge to a deterministic ownership path;
- equal transforms or positions to object identity.
