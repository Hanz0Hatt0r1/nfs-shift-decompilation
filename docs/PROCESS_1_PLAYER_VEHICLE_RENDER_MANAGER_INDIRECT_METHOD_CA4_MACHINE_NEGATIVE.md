# Process 1 — retail machine closure of indirect manager `+0xca4`

## BLOCKER

The shortest playable-slice blocker remains `SHIFT.BMWBody0BindFrameProof/1`.
The direct render-manager method branch had already closed negative for
`mPlayerVehicleRenderables` at `+0xca4`, while
`SHIFT.PlayerVehicleRenderManagerIndirectDispatch/1` left exactly two resolved
retail entries to inspect:

```text
0x0045f620
0x0045f630
```

Until those entries were closed, the manager `+0xca4` hypothesis remained a live
P1.1 candidate branch.

## INPUT

- negative `SHIFT.PlayerVehicleRenderManagerMethodCa4Access/1` over the frozen 17
  direct callees;
- positive `SHIFT.PlayerVehicleRenderManagerIndirectDispatch/1` with exactly the
  two targets above;
- retail `SHIFT.exe`:
  - MD5 `705af8b420e5eb1e3834ac43d5533c6b`;
  - SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`;
  - image base `0x00400000`;
  - i386 PE machine `0x014c`.

## OUTPUT

`tools/ghidra/analyze_player_vehicle_render_manager_indirect_method_ca4_machine_negative.py`
emits:

```text
SHIFT.PlayerVehicleRenderManagerIndirectMethodCa4MachineNegative/1
```

The proof reuses the repository PE mapper and fails closed on executable identity,
PE machine/image-base drift, target relocation outside `.text`, non-file-backed
bytes, opcode-shape drift, or resolved-target-set drift.

It decodes only the two finite branch-free bodies proven by the preceding dispatch
contract.  It is not a general x86 disassembler.

### `0x0045f620`

Exact retail bytes:

```text
8b81ac0d0000c3
```

Decoded body:

```text
MOV EAX, dword ptr [ECX + 0xdac]
RET
```

The only ECX-relative access is a read at `+0xdac`.

### `0x0045f630`

Exact retail bytes:

```text
558bec8b45088981ac0d00005dc20400
```

Decoded body:

```text
PUSH EBP
MOV  EBP, ESP
MOV  EAX, dword ptr [EBP + 0x8]
MOV  dword ptr [ECX + 0xdac], EAX
POP  EBP
RET  0x4
```

The only ECX-relative access is a write at `+0xdac`.

Both bodies are terminal and contain no branch or call.  Therefore there is no
hidden reachable continuation in either resolved entry that could contain the
hypothesized `+0xca4` access.

The committed retail report is:

```text
evidence/player_vehicle_render_manager_indirect_method_ca4_machine_negative.json
```

It records:

```text
indirect_manager_method_ca4_branch_negative = true
manager_method_ca4_hypothesis_closed = true
player_vehicle_renderables_field_runtime_access_ready = false
bmw_body0_bind_frame_proof_ready = false
```

## CONSUMER

This is a negative Process 1 decision proof.  It removes the render-manager
`+0xca4` branch from the live P1.1 blocker graph; it does **not** make a Process 2
or Process 3 semantic gate positive.

The next P1.1 frontier returns to the canonical BODY0 construction/bind provenance
lane required by the v2 instructions:

```text
FUN_007b3670
  -> FUN_007bba90
  -> FUN_007bbb10
  -> FUN_007bbb60
```

No neighboring manager methods are added merely because they are close in the
binary.

## Reproduction

With the two upstream JSON reports and the exact retail executable:

```bash
python3 tools/ghidra/analyze_player_vehicle_render_manager_indirect_method_ca4_machine_negative.py \
  out/player_vehicle_render_manager_method_ca4_access.json \
  out/player_vehicle_render_manager_indirect_dispatch.json \
  /path/to/SHIFT.exe \
  --json-out out/player_vehicle_render_manager_indirect_method_ca4_machine_negative.json
```

The retail executable is not committed to the repository.

## Limits

This proof does not identify the object stored at `+0xdac`, prove
`mPlayerVehicleRenderables` ownership, establish an outer Vehicle/VHF frame
relation, materialize `M_BODY0_bind`, prove retail scheduler/cadence, or publish a
vehicle world transform.  Those claims remain gated independently.
