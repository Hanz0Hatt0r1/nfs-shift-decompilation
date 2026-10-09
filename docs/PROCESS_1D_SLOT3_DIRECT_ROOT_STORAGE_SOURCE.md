# Process 1D — slot3 direct exact-root storage source surface

This pass narrows the remaining stored/escaped alias frontier without claiming a machine-level escape theorem.

It scans the exact PC retail `SHIFT.exe.c` export (SHA-256 `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`) only inside the 15 carrier functions whose HDVehicle/wheel identity was already established by merged P1D retail machine contracts.

The bounded syntax is deliberately strict: assignments whose right-hand side is exactly the entry root variable (`this` or `param_1`), optionally through a cast, with no pointer arithmetic or dereference.

Result:

```text
exact entry-root assignments:        2
persistent/nonlocal assignments:     0

FUN_00758b50: local_2c = param_1;   # stack local
FUN_00763570: local_4c = this;      # stack local
```

No direct source-level assignment of the exact entry root to persistent or unknown storage exists in the bounded carrier set.

Reproduce:

```bash
python3 tools/ghidra/analyze_p1d_slot3_direct_root_storage_source.py \
  /path/to/SHIFT.exe.c \
  --output out/p1d_slot3_direct_root_storage_source.json
```

## Boundary

This does **not** follow either stack-local alias after assignment and does not cover:

- derived wheel/base pointers;
- register-only machine aliases;
- stores through another local alias;
- bulk/aggregate stores;
- callee-created escapes;
- callbacks registered elsewhere.

Therefore `stored_or_escaped_aliases_ruled_out` remains false. This result only removes the simplest direct exact-entry-root persistent-store syntax from the frontier. Slot3 writer provenance and P1.3D remain false; provider count remains 7.
