# Process 1A / P1.3A — slot0/slot1 named memory frontier

## Blocker

P1.3A still needs selected-root alias/callee/bulk-copy provenance for slot0 `HDVehicle+0x938` and slot1 `HDVehicle+0x13b8`.

The exact absolute-displacement surface and literal wheel-local `+0x538` forwarding subset are already bounded. The remaining copy/init paths may reach the target without embedding any target displacement, so broad symbol reachability is useful only as a navigation frontier.

## Drive-backed callgraph result

`shift_ghidra.sqlite` (`SHIFT.GhidraSQLiteIndex/1`, SHA-256 `ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e`) was scanned through direct call edges from the four recovered wheel/physics roots:

- `FUN_00758b50` — wheel update / proven `FUN_00755950` caller;
- `FUN_0076d100` — enclosing physics-pass anchor;
- `FUN_00763570` — recovered four-wheel same-topology feedback path;
- `FUN_00770e80` — outer physics/update scheduler anchor.

The scan finds the first reachable named `memcpy`/`memmove` and `memset` families rather than stopping at the old depth-4 empty surface.

| root | nearest copy | nearest set |
|---|---:|---:|
| `FUN_00758b50` | depth 10: `_memmove` | depth 10: `_memset` |
| `FUN_0076d100` | depth 6: `_memmove` | depth 5: `_memset` |
| `FUN_00763570` | depth 7: `_memcpy_s`, `_memmove_s` | depth 6: `_memset` |
| `FUN_00770e80` | depth 7: `_memcpy_s`, `_memmove`, `_memmove_s` | depth 6: `_memset` |

No named copy/set target occurs within four direct edges of any root.

The wheel-update root's first copy/set paths are deep CRT/error/allocation branches. The first game-side secure-copy paths worth exact alias inspection appear under the four-wheel feedback / outer scheduler branches at depth 7:

- `FUN_00763570 -> FUN_0070fe90 -> FUN_0041903c -> FUN_0070fe99 -> FUN_0070fae0 -> FUN_00632c70 -> FUN_00631740 -> _memcpy_s`;
- `FUN_00763570 -> FUN_0070fe90 -> FUN_0041903c -> FUN_0070fe99 -> FUN_0070fae0 -> FUN_006329e0 -> FUN_00631230 -> _memmove_s`;
- `FUN_00770e80 -> FUN_0076f970 -> FUN_00887720 -> FUN_00887580 -> FUN_00647820 -> FUN_006329e0 -> FUN_00631230 -> _memmove_s`.

## Evidence boundary

This is navigation evidence, not destination identity.

A named copy routine being reachable does not prove that it receives the selected wheel alias, covers `+0x538`, or writes slot0/slot1. Inline/custom copies, indirect dispatch, and deeper paths remain open.

The result narrows the next machine trace: join the topology-alias exporter to only these nearest game-side secure-copy branches. If a branch does not carry a selected-HDVehicle wheel alias, reject it without expanding its descendants.

## Gate

```text
named-memory navigation frontier captured = true
named copy/set within depth 4 any root     = false
slot0 alias/callee/bulk-copy complete      = false
slot1 alias/callee/bulk-copy complete      = false
P1.3 complete                              = false
provider count                             = 7
```
