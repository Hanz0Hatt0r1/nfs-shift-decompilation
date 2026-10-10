# Process 1D — machine wheel-root materialization closure

This slice closes the two already-identified PC retail 1.02 paths that derive the four wheel roots directly from an exact `HDVehicle` root. Object identity remains machine-owned; no scalar/offset coincidence is promoted to pointer identity.

## `FUN_00763570` wheel loop

The hash-locked window `0x007635f4..0x0076362a` proves:

```text
0x007635f4  EAX = HDVehicle+0x400
0x00763609  [EBP-0x4] = EAX
0x0076360c  ECX = [EBP-0x4]
0x0076360f  call FUN_00755f80
0x0076361b  [EBP-0x4] += 0xa80
0x00763622  ESI += 1
0x00763625  compare ESI with 4
0x00763628  loop while ESI < 4
```

Therefore the four receivers are exactly:

```text
HDVehicle+0x400
HDVehicle+0xe80
HDVehicle+0x1900
HDVehicle+0x2380
```

The derived wheel cursor exists only in stack-local `[EBP-0x4]`; this bounded loop contains no non-stack persistence of the wheel root.

## `FUN_00770e80` explicit wheel calls

The hash-locked window `0x007710fe..0x00771185` materializes the same four roots directly in `ECX` before calls to `FUN_00760b50`:

| LEA site | receiver | consumer call |
| --- | --- | --- |
| `0x007710fe` | `HDVehicle+0x400` | `0x00771107` |
| `0x0077111c` | `HDVehicle+0xe80` | `0x00771125` |
| `0x00771138` | `HDVehicle+0x1900` | `0x00771147` / `0x00771162` branch alternatives |
| `0x00771177` | `HDVehicle+0x2380` | `0x00771180` |

The last row is the selected slot3 wheel root. Within each live `ECX` wheel-root interval before its consumer call, the root is neither pushed nor stored to non-stack memory.

## Reproduce

```bash
python3 tools/ghidra/analyze_p1d_slot3_machine_wheel_root_materialization_pe.py \
  /path/to/SHIFT.exe \
  --output out/p1d_slot3_machine_wheel_root_materialization_closure.json
```

The analyzer verifies the pinned retail executable SHA-256 plus independent machine-byte hashes for both bounded windows.

## Boundary

This proves the known direct `HDVehicle -> wheel root` materializations and their immediate storage/forwarding behavior only. It does not close interior/child aliases, reconstructed pointers loaded from memory, aggregate copies, callbacks, indirect entry, or runtime-generated/copied/encoded pointers.

Accordingly `other_derived_alias_storage_ruled_out`, `runtime_generated_pointer_stores_ruled_out`, `stored_or_escaped_aliases_ruled_out`, slot3 writer provenance, P1.3D, and aggregate P1.3 remain false. External provider count remains 7.
