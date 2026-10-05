# Process 1 — player vehicle render-manager receiver-transfer frontier v2

## Blocker

The first playable Linux slice still waits on `SHIFT.BMWBody0BindFrameProof/1`.
The active owner/frame path needs a physical first-hop transfer from the now
proven `DAT_00bc185c` render-manager instance into one or more concrete
method/dispatch receivers that can be checked for `receiver + 0xca4` access.

The v1 frontier consumed the exhaustive 80-function retail instruction export,
found 95 exact READ xrefs of `DAT_00bc185c`, but rejected all 95 at seed
admission because it additionally required one particular raw Ghidra p-code
`LOAD` lowering. The exported machine instructions themselves are direct IA-32
loads such as `MOV ECX,dword ptr [0x00bc185c]`. Therefore the v1 `0/95` result
is an acquisition-shape failure, not a negative proof that no physical manager
pointer is read.

## Input

- positive `SHIFT.PlayerVehicleRenderManagerGlobalConstructorIdentity/1`;
- exhaustive ready `SHIFT.PlayerVehicleRenderManagerRootPoseXrefRank/1`;
- exact 80-function `SHIFT.GhidraFunctionInstructions/2` export;
- the v1 retail result showing 95 exact global READ xrefs and zero seeds;
- the existing finite IA-32 all-path register-provenance engine;
- structured p-code register-write safety checks from the v1 frontier.

## Output

`tools/ghidra/build_player_vehicle_render_manager_receiver_transfer_frontier_v2.py`
emits:

```text
SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/2
```

A seed is admitted only when all of the following hold:

1. the current rank identifies the instruction as an exact READ xref of
   `DAT_00bc185c`;
2. the instruction is exactly `MOV tracked_reg,[absolute global address]`;
3. the absolute source address numerically equals `0x00bc185c`;
4. the finite register engine changes that destination register to exactly one
   post-instruction memory origin;
5. that one origin numerically names the same candidate global.

A raw p-code `LOAD -> register` or `LOAD -> unique -> COPY -> register` shape is
recorded only as diagnostic evidence. It is not required for the seed because
the exact xref plus exact machine `MOV` plus exact register origin already prove
the physical load. Structured p-code remains active as a fail-closed safety net
for register writes during the downstream local-CFG trace.

The v2 report still promotes only first-hop CALL receiver transfers. Direct
callee targets become a bounded targeted-instruction worklist; indirect calls
remain unresolved dispatch evidence.

## Consumer

A positive direct worklist feeds targeted callee instruction export and the
next proof:

```text
entry manager receiver
  -> exact receiver + 0xca4 runtime access
  -> mPlayerVehicleRenderables value
  -> SMS / RenderHierarchy owner join
  -> BMW VHF/root-frame identity
  -> SHIFT.BMWBody0BindFrameProof/1
```

If v2 produces seeds but no CALL receiver transfers, the exact-global first-hop
CALL branch is correctly negative and Process 1 can move to the next bounded
owner/frame frontier without reopening broad callgraph exploration.

## Explicit limits

This artifact does **not** prove:

- `receiver + 0xca4` is accessed by any resulting callee;
- the `+0xca4` value is a render-owner or VHF object;
- outer vehicle root equals the BMW VHF root/frame;
- BODY0 bind-frame equality;
- vehicle world-transform readiness.

No original-game execution or runtime capture is required for this step.
