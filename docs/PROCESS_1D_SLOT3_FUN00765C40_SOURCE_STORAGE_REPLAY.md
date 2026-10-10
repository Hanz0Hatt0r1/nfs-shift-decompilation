# Process 1D — `FUN_00765c40` source-storage replay

Merged #1791 expanded the canonical P1D exact-carrier set from 15 to 16 by adding `FUN_00765c40`, while deliberately leaving the previous source-storage replay at 15 carriers.

This tranche extends exactly the existing `SHIFT.P1D.Slot3DirectExactRootStorageSource/1` grammar to the new carrier. Object identity remains owned by `SHIFT.P1D.Slot3Fun00765c40CarrierHandoff/1`; the pinned `SHIFT.exe.c` export is navigation/cross-check evidence only.

The new function signature is:

```text
void __thiscall FUN_00765c40(void *this,char param_1)
```

The full function body contains **zero** direct assignments of the exact entry root matching the original replay grammar:

```text
lhs = this;
```

including casted equivalents accepted by the original analyzer. Therefore the combined 16-carrier direct exact-root assignment surface remains unchanged:

```text
FUN_00758b50: local_2c = param_1;  -> stack-local
FUN_00763570: local_4c = this;     -> stack-local
FUN_00765c40: no direct exact-root assignment
```

Persistent/unknown direct exact-root stores remain zero.

## Gate impact

The previously open #1791 source replay is now complete for this exact source-level subset:

```text
source_direct_exact_entry_root_assignment_16_carrier_subset_complete = true
source_storage_replay_for_16_carriers_complete = true
fun00765c40_direct_exact_entry_root_assignment_found = false
fun00765c40_direct_exact_entry_root_persistent_store_found = false
```

The name `source_storage_replay_for_16_carriers_complete` refers only to the same direct exact-entry-root assignment syntax as the original 15-carrier contract. It does **not** promote derived-alias storage, machine register aliases, runtime-generated/copied pointers, callbacks, indirect entry, or callee-created aliases. Those global gates remain false, as do slot3 writer provenance, P1.3D and aggregate P1.3. Provider count remains 7.

`FUN_00765c40` does contain derived addresses such as `this+offset` assigned to locals; those are intentionally outside this exact-root source grammar and remain governed by the merged machine side-effect contracts and subsequent alias work.

Reproduce:

```bash
python3 tools/ghidra/build_p1d_slot3_fun00765c40_source_storage_replay.py \
  /path/to/SHIFT.exe.c \
  evidence/p1d_slot3_direct_root_storage_source.json \
  evidence/p1d_slot3_fun00765c40_carrier_handoff.json \
  --output out/p1d_slot3_fun00765c40_source_storage_replay.json
```

Next, consume the parallel 16-carrier CALLIND/static-pointer refresh, then continue callee-created/runtime aliases and indirect-entry joins before changing the global stored/escaped-alias gate.
