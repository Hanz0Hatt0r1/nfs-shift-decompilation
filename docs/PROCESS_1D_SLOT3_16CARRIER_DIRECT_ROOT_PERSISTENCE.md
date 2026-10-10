# Process 1D — 16-carrier direct exact-root persistence

This slice extends the earlier six-window persistence work to the complete merged 16-carrier set, but keeps the claim deliberately narrow: only **direct machine value uses of stable exact-root carrier registers** are classified.

The semantic identity of each root/register interval comes from already-merged machine contracts. GNU `objdump` is used only to replay the pinned PC retail 1.02 bytes and enumerate direct stores, pushes, and immediate GPR copies sourced from those stable exact-root registers.

## Result

Across all 16 carriers:

```text
direct exact-root memory stores = 2
non-stack/unknown stores        = 0
direct exact-root pushes        = 0
direct exact-root GPR copies    = 23
copy destinations               = ECX only
```

The two stores are stack-local preservation only:

| Function | Site | Store |
| --- | --- | --- |
| `FUN_00758b50` | `0x00758b9b` | `[ebp-0x1c] = EDI` |
| `FUN_00763570` | `0x00763590` | `[ebp-0x3c] = EDI` |

For `FUN_00758b50`, the first stack slot is also machine-recovered explicitly at `0x00758d70` (`EDI = [ebp-0x1c]`), allowing the exact-root interval to resume after EDI is temporarily reused for another object.

No direct store of a stable exact-root carrier register to non-stack memory is present. No exact-root value is pushed. All 23 direct register copies sourced from stable root registers target `ECX`; no new persistent GPR alias is created by this direct-copy surface.

## Reproduce

```bash
python3 tools/ghidra/analyze_p1d_slot3_16carrier_direct_root_persistence_pe.py \
  /path/to/SHIFT.exe \
  --output out/p1d_slot3_16carrier_direct_root_persistence.json
```

The analyzer verifies the retail executable SHA-256 and pins every function body by decoded instruction count and machine-byte SHA-256. Two Ghidra extents (`FUN_00763570`, `FUN_00765c40`) end on a partial decoded byte; the evidence therefore records both the Ghidra extent size and the exact decoded-byte count instead of silently treating the final partial byte as an instruction.

## Boundary

This is not a universal alias-escape proof. It does **not** close:

- derived/interior addresses produced from exact roots;
- aggregate or bulk copies;
- aliases reconstructed from memory;
- callbacks and indirect entry;
- encoded/copied/runtime-generated pointer values;
- callee-created aliases beyond their separately merged closures.

Therefore `machine_register_alias_storage_ruled_out`, `stored_or_escaped_aliases_ruled_out`, slot3 writer provenance, P1.3D, and aggregate P1.3 remain false. External provider count remains 7.
