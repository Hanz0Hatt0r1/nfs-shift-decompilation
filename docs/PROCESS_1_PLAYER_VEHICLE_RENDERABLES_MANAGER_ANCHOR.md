# Process 1 — player vehicle renderables manager anchor

## Playable-slice blocker reduced

The remaining vehicle-transform blocker is now narrowly:

```text
outer Vehicle root
  -> canonical BMW graphical/VHF vehicle-root owner
```

The broad `.vhf` loader search is intentionally not reopened. The current retail
Ghidra database already contains a stronger render-side anchor in
`FUN_0045ef50`: the constructor labels one allocation
`mPlayerVehicleRenderables`.

This phase records that exact receiver-relative field and adds a targeted global
reference exporter so the next pass can intersect render-manager users with the
already-proven vehicle/participant owner chain.

## Exact constructor anchor

Retail identity remains:

```text
SHIFT.exe MD5 705af8b420e5eb1e3834ac43d5533c6b
```

`FUN_0045ef50` has mnemonic fingerprint:

```text
6644a22ad5bd2c20d96f40b8f1e7d5193afdd8e9d40a60bf216814e2f43f60aa
```

and preserves its entry receiver in `ESI`:

```text
0x0045ef59  MOV ESI,ECX
```

The exact allocation label and chain are:

```text
0x00ab55a4  "mPlayerVehicleRenderables"
0x0045f191  PUSH 0xab55a4
0x0045f196  PUSH 0x400
0x0045f1a1  CALL FUN_00695e30
0x0045f1a8  CALL FUN_00695f10
0x0045f1af  CALL FUN_0068a700
0x0045f1bf  MOV [ESI+0xca4],EAX
```

Therefore the constructor proves only this physical field relation:

```text
render-manager receiver + 0xca4
  = allocation labelled "mPlayerVehicleRenderables"
```

This is a render-side owner/container anchor. It is **not** yet a proof that any
particular runtime global is an instance of this class, that an element is the
BMW VHF hierarchy root, or that its frame equals the outer Vehicle root.

## Why the previous database could not finish the join

`globals.jsonl` currently records only a global's `reference_count`. For example,
the retail database reports:

```text
DAT_00bc185c  reference_count = 116
```

but does not record the individual xref instruction addresses or the functions
containing them. That prevents a deterministic intersection between a candidate
in-game/render manager global and functions that also carry vehicle/participant
pointers.

The new targeted contract is:

```text
SHIFT.GhidraGlobalReferences/1
```

Exporter:

```text
tools/ghidra/ShiftGlobalReferenceExporter.java
```

Runner:

```text
tools/ghidra/run_shift_global_references.sh
```

Each requested global produces exact reference rows containing:

- reference instruction address;
- Ghidra reference type;
- operand index and primary-reference bit;
- containing function address/name when present;
- disassembled instruction text;
- a deduplicated containing-function list;
- executable MD5.

The validator fail-closes if the requested addresses, reference count, or
function summary disagree with the detailed rows.

## Next targeted export

The immediate candidate global is intentionally treated as a candidate until its
machine references are inspected:

```bash
cd /home/pes/nfs-shift-decompilation
git pull

GHIDRA_HOME=/opt/ghidra \
./tools/ghidra/run_shift_global_references.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/player_vehicle_render_manager_global_refs.jsonl \
  0x00bc185c
```

The resulting file is sufficient to rank the exact functions that access the
candidate manager global. Only functions that also expose a vehicle/participant
pointer or reach the `+0xca4` player-vehicle-renderables field should receive a
follow-up full instruction export.

## Deliberate non-claims

This phase keeps all transform gates closed:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready         = false
outer_vehicle_root_to_VHF_fixed_affine_delta_ready   = false
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                         = false
vehicle_world_transform_ready                        = false
```

It does not promote:

- the `mPlayerVehicleRenderables` name to VHF hierarchy identity;
- `DAT_00bc185c` to render-manager instance identity before its references are
  inspected;
- collection membership to coordinate-frame identity;
- equal spawn/world positions to pointer identity;
- a generic `.vhf` loader to the player vehicle path.

## Next proof

After the single global-reference export, the next finite question is:

```text
function referencing candidate in-game/render manager global
  + concrete access to manager+0xca4
  + concrete vehicle/participant pointer
    -> exact player vehicle renderable owner
    -> VHF hierarchy/root owner or fixed affine relation
```

That is the shortest static bridge remaining between the now-singular
BODY0->outer-Vehicle numeric bind and the already source-backed Phase 645 BMW VHF
assembly transform.
