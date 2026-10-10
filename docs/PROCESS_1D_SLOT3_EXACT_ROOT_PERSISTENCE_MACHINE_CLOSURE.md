# Process 1D — exact wheel-root persistence machine closure

Merged #1793 defined six exact wheel-root register windows but intentionally left the authoritative retail capture open. This slice executes that finite frontier directly against the pinned PC retail 1.02 `SHIFT.exe` with GNU objdump while preserving the semantic root windows from merged machine contracts.

## Exact machine result

The six windows are byte-hash locked independently. Across all six windows:

```text
memory-store-root = 0
push-root         = 0
ranked register/LEA candidates = 8
```

The eight exporter-style candidates are finite and already machine-adjudicated by merged P1D work:

| Site | Raw class | Machine adjudication |
| --- | --- | --- |
| `0x00755964` | derived-address-root | `wheel+0x80`; forwarded to `FUN_007555b0`, not exact root |
| `0x00755b8f` | register-copy-root | child load `[wheel+0x420]` |
| `0x00755c04` | derived-address-root | `wheel+0x7c8`; bounded `FUN_00753620` write remains at `wheel+0x7c8` |
| `0x00755db3` | register-copy-root | known exact-root forward to already-closed `FUN_00752fc0` leaf |
| `0x00760d02` | register-copy-root | child load `[wheel+0x420]` -> `FUN_007ba860` |
| `0x00755f9c` | register-copy-root | child load `[wheel+0x420]` |
| `0x00755fb8` | register-copy-root | child load `[wheel+0x420]` |
| `0x00755fd6` | register-copy-root | child load `[wheel+0x420]` |

The raw #1793 classifier deliberately over-approximates `MOV reg,[root+offset]` as `register-copy-root`; this closure keeps that raw class for reproducibility but explicitly distinguishes the dereferenced child pointers from true root copies.

## Reproduce

```bash
python3 tools/ghidra/analyze_p1d_slot3_exact_root_persistence_pe.py \
  /path/to/SHIFT.exe \
  --output out/p1d_slot3_exact_root_persistence_machine_closure.json
```

The tool verifies the retail executable SHA-256 and the instruction-byte SHA-256 of every bounded window before producing a result.

## Boundary

This closes the six-window #1793 persistence frontier only. It does not rule out:

- aliases created in other exact carriers or callees;
- aggregate/bulk pointer stores outside these windows;
- callbacks registered elsewhere;
- runtime-generated/copied/encoded pointer paths;
- the still-separate 16-carrier `SHIFT.exe.c` source-storage replay.

Therefore the global `machine_register_alias_storage_ruled_out`, `callee_created_aliases_ruled_out`, `stored_or_escaped_aliases_ruled_out`, slot3 writer provenance, P1.3D and aggregate P1.3 gates remain false. External provider count remains 7.
