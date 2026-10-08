# Process 1 — `FUN_0074f560` static provider probe

## BLOCKER

P1.2a is now narrowed to the collision/world lookup implementation at or below `FUN_0074f560` / the scene-query boundary. The repository contains caller-visible `FUN_007b0710` ABI evidence, but not an indexed full source body for `FUN_0074f560` from which the actual provider object/call can be promoted.

The next useful step therefore requires a reproducible navigation artifact from the authoritative PC-retail `SHIFT.exe.c`, not a guessed collision-engine implementation.

## OUTPUT

Adds:

```text
tools/ghidra/inventory_fun_0074f560_provider_surface.py
```

The probe is SHA-256 locked to the authoritative PC-retail decompiler export and emits a **raw navigation inventory** for exactly the `FUN_0074f560` function body:

- source start/end lines;
- direct `FUN_xxxxxxxx` call sites and unique callees;
- referenced `DAT_` / `PTR_` / `LAB_` / `UNK_` globals;
- potential indirect-call lines;
- hexadecimal pointer/field-offset frequency.

Its JSON format is:

```text
SHIFT.Fun0074f560ProviderSurfaceInventory/1
```

## Safety boundary

This output is **not a positive provider-ownership contract**.

In particular, the probe deliberately reports:

```text
provider_object_identified = false
scene_query_call_identified = false
physx_class_name_proven = false
safe_to_replace_with_guessed_track_query = false
requires_manual_pointer_provenance_review = true
```

A vtable-shaped or indirect-call expression is only a navigation candidate. It cannot be promoted to a PhysX class, scene object, or collision-provider owner without pointer provenance from PC retail evidence.

## Usage

Run against the exact authoritative full Ghidra C export:

```bash
python3 tools/ghidra/inventory_fun_0074f560_provider_surface.py \
  /path/to/SHIFT.exe.c \
  --output /tmp/fun_0074f560_provider_surface.json
```

The script fails closed if the `SHIFT.exe.c` SHA-256 differs from:

```text
512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9
```

## Review order

After generating the report:

1. inspect `potential_indirect_call_sites` and direct callees;
2. trace the receiver/object expression for each plausible scene-query dispatch;
3. use globals/offsets only as navigation evidence;
4. bind any promoted lower call to the already-recovered `FUN_007b0710` 0x58-byte returned surface-record contract;
5. do not infer PhysX names from calling shape alone.

## TESTS

`tests/test_process1_fun_0074f560_static_probe.py` verifies target-definition extraction, direct/global/offset inventory, indirect-call candidate capture, source-hash pinning, and the fail-closed documentation boundary.

## GATES_CHANGED

None. The external provider count remains 7 and P1.2a remains incomplete until the probe output is reviewed and a positive pointer/call provenance contract is published.

## NEXT_OWNER

Process 1.

## NEXT_STEP

Generate this inventory from the pinned PC-retail `SHIFT.exe.c`, then promote only the smallest source-backed object/call relation needed to identify the actual scene-query provider boundary.
