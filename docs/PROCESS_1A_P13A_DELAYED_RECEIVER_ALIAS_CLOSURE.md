# Process 1A / P1.3A — delayed singleton-receiver alias closure

This contract closes the direct-`FUN_00886980` delayed/stored receiver subset left open by the immediate-dispatch contract. It is retail-PC-1.02 specific and is pinned to `SHIFT.exe` SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

## Result

Across all 203 direct calls to `FUN_00886980`, the bounded exact-receiver event scan finds exactly one stack spill and one raw return before the first intervening call/unconditional jump. It finds no direct non-stack store and no direct call-argument escape.

The stack spill is `0x00832aa2 mov [ebp-0x10],eax` after getter call `0x00832a96`. Its delayed reload at `0x00832fbc` is used only for virtual slots `+0x50` and `+0x58`; neither is the module-base getter slot `+0x84` or `+0xa4`.

The same stack cell is later passed as the second output argument to the dynamically resolved NVAPI entry at `0x00bbbd34`. The retail dynamic table pairs that slot with interface ID `0xe5ac921f`, `NvAPI_EnumPhysicalGPUs`. The call at `0x00833144` passes `&[ebp-0x224]` as the physical-GPU handle array and `&[ebp-0x10]` as the GPU-count output. The post-call reload/store at `0x00833150`/`0x00833156` is reachable only on `NVAPI_OK == 0`, so the stack cell contains the output count there, not the old singleton receiver.

The sole raw-return path is the getter call at `0x005f5182` returning the exact receiver in EAX at `0x005f51a1`. The already-bounded `FUN_005f4f50` entry surface has two direct callers and one direct tail jump, with no absolute function-pointer occurrences. Both direct callers ignore/overwrite EAX before use; the tail path reaches the only direct `FUN_005f8950` caller at `0x005a89e4`, whose next instruction calls `0x00586dd0` and therefore overwrites caller-saved EAX before use.

## Gates

Promoted only:

- `p13a_direct_getter_delayed_spill_return_subset_complete = true`
- `direct_singleton_getter_delayed_or_stored_alias_dispatch_ruled_out = true`

Still fail-closed:

- `delayed_or_stored_receiver_alias_dispatch_ruled_out`
- `module_base_getter_consumer_paths_complete`
- runtime callback registration
- incoming indirect entry
- encoded/reconstructed carrier pointers
- runtime-generated/copied carrier pointers
- runtime-generated selected-wheel pointer stores
- stored/escaped aliases
- slot0, slot1, aggregate P1.3

Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_delayed_receiver_alias.py /path/to/SHIFT.exe \
  --output evidence/p1a_p13a_delayed_receiver_alias_closure.json
pytest -q tests/test_process1a_p13a_delayed_receiver_alias.py
```

The analyzer requires GNU `objdump`. NVAPI ABI identity is pinned by interface ID and is tested offline; no network lookup is required during CI.
