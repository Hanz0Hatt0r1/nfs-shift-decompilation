# Process 1D — `FUN_007555b0` wheel+0x80 interior alias closure

Merged P1D machine proof establishes:

```text
FUN_00755950 exact receiver = selected wheel
0x00755964 ECX = wheel + 0x80
0x00755983 -> FUN_007555b0
```

Therefore `FUN_007555b0` does **not** receive the exact wheel root. It receives the exact interior pointer `wheel+0x80`. The selected slot3 field `wheel+0x538` would appear inside this callee as receiver offset:

```text
0x538 - 0x80 = 0x4b8
```

The complete PC retail function body is hash locked:

```text
start             0x007555b0
size              364 bytes
instruction count 115
machine SHA-256   43aff676522a3b6b558980b56e29e289926893d266bf71e063b25d401d1e4881
```

Across the whole body, ECX-relative memory accesses are confined to `+0x1d0..+0x260` at the exact enumerated offsets. Persistent writes occur only at receiver `+0x248/+0x250/+0x258/+0x260`, which normalize to selected-wheel `+0x2c8/+0x2d0/+0x2d8/+0x2e0`.

The callee contains:

```text
selected target receiver+0x4b8 accesses = 0
direct calls                              = 0
ECX value reconstruction/mutation         = 0
```

Thus this interior alias neither reaches `wheel+0x538`, reconstructs the exact wheel root, nor forwards the interior/root pointer to another callee.

Reproduce against the authoritative retail executable:

```bash
python3 tools/ghidra/analyze_p1d_slot3_fun007555b0_interior_alias_pe.py \
  /path/to/SHIFT.exe \
  --output out/p1d_slot3_fun007555b0_interior_alias_closure.json
```

This closes only the `FUN_00755950 -> FUN_007555b0` wheel+0x80 callee-created alias. Other child/interior aliases, runtime pointer stores, callback paths and global stored/escaped alias coverage remain open. Slot3 writer provenance and P1.3D remain false; provider count remains 7.
