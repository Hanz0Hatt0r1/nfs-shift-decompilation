# Process 1A / P1.3A — trivial constant-return producers for `FUN_005ffc50`

## Scope

The direct/raw/PIC/FNSTENV and exact-GPR CFG contracts do not model a callee return value flowing back into `EAX`. This pass closes one bounded return-value class without external Ghidra state.

Every direct call target is inspected from its entry address. A producer qualifies only when its **entry basic block** reaches `ret` within 64 decoded instructions before any call or branch, and the local constant tracker proves an exact `EAX` value. Each direct call to such a producer then seeds the caller's `EAX` with that exact value and scans only the immediate straight-line suffix up to the next control transfer.

## Retail result

Across **2,847,850** decoded instructions:

- direct call targets: **25,666**;
- trivial exact-constant return producers: **280**;
- direct callsites to those producers: **859**;
- distinct exact return constants observed at those callsites: **41**;
- post-call instructions simulated: **3,045**.

Within this bounded return-value class:

- exact `0x005ffc50` materializations after the call: **0**;
- indirect `call reg` / `jmp reg` transfers to `0x005ffc50`: **0**.

Synthetic tests prove that `callee: mov eax,base; ret` followed by `caller: add eax,delta; call eax` is detected. A branched callee is intentionally excluded from this contract.

## Gate effect

Promoted only `p13a_fun005ffc50_trivial_constant_return_producer_subset_complete=true`.

General return-value provenance remains fail-closed: branched producers, memory-derived returns, post-call CFG carry, writable/runtime-memory entry, unbounded phi reasoning, global encoded/reconstructed entry, dynamic registry registration, callback/incoming-indirect closure, runtime-generated selected-wheel stores, stored aliases, slot0, slot1, and aggregate P1.3 remain open. Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_trivial_constant_return_producers.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_four_edge_constant_carry.json \
  --output evidence/p1a_p13a_fun005ffc50_trivial_constant_return_producers.json
pytest -q tests/test_process1a_p13a_fun005ffc50_trivial_constant_return_producers.py
```

## Next step

Extend return-value provenance to branched or memory-derived producers, or move to writable/runtime-memory sources. Trivial direct constant-return producers no longer need to be rescanned.
