# Process 1B — render-manager CFG memory-escape analyzer

## Purpose

`SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/2` already performs fail-closed all-path register provenance for exact reads of `DAT_00bc185c`. It records call receiver transfers, pointer dereferences, stack pushes, and return-value residue, but does not distinguish an exact manager pointer used as the **source** of a memory store.

`tools/ghidra/analyze_player_vehicle_render_manager_memory_escapes.py` reuses the same audited v2 seed and local-CFG machinery and adds one narrow sink:

```text
MOV [memory], exact_manager_alias
```

The analyzer classifies the destination as stack-relative, register-relative, absolute, or unparsed memory. It does not infer destination ownership and does not follow the stored value across a function boundary.

## Inputs

Use the same three retail artifacts required by the v2 receiver-transfer frontier:

```bash
python tools/ghidra/analyze_player_vehicle_render_manager_memory_escapes.py \
  out/player_vehicle_render_manager_global_constructor_identity.json \
  out/player_vehicle_render_manager_root_pose_rank.json \
  out/player_vehicle_render_manager_ranked_function_instructions.jsonl \
  --json-out out/player_vehicle_render_manager_memory_escapes.json
```

No new Ghidra acquisition is required when those files are already present.

## Output

The output format is:

```text
SHIFT.PlayerVehicleRenderManagerMemoryEscapeSurface/1
```

A zero `memory_store_count` closes the exact-manager memory-store escape surface covered by the same exhaustive v2 seed/CFG scope. A nonzero list is only a worklist: every destination owner and every later reload must still be proven before it becomes an exact persistent alias.

## Fail-closed limits

The analyzer does not:

- infer semantics from a destination offset;
- follow an alias after it has been stored;
- promote derived interfaces/subobjects back to the exact outer root;
- change the manager `+0x374` join, literal `0x004b86cf`, P1.3, or provider-count gates by itself.

The provider count remains 7 until a runtime boundary is actually removed.
