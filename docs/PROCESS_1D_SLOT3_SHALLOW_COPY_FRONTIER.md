# Process 1D — slot3 shallow bulk-copy frontier

## Scope

P1.3D still needs exact writer/value provenance for selected `HDVehicle+0x28b8`. The corrected machine displacement is `+0x538` on the receiver `HDVehicle+0x400+slot*0xa80`.

The corrected Ghidra exporter is the primary next machine step. Before that run, this frontier bounds a narrower navigation question: do the already-proven wheel/physics lifecycle roots reach a named `memcpy`/`memmove` family routine within four direct-call edges?

## Roots

The Drive `SHIFT.GhidraSQLiteIndex/1` callgraph is normalized from `raw_json` and traversed from:

- `FUN_00758b50` — proven wheel update / `FUN_00755950` caller;
- `FUN_0076d100` — enclosing physics-pass anchor containing the wheel-update anchor;
- `FUN_00763570` — recovered four-wheel same-topology feedback path;
- `FUN_00770e80` — recovered outer physics/update scheduler anchor.

The depth bound is four direct-call edges.

## Result

No named `memcpy`/`memmove` family call occurs within that shallow direct frontier.

| root | unique nodes through depth 4 | nodes by minimum depth | named copy hits |
|---|---:|---|---:|
| `FUN_00758b50` | 23 | `1,10,6,5,1` | 0 |
| `FUN_0076d100` | 151 | `1,8,41,52,49` | 0 |
| `FUN_00763570` | 48 | `1,8,6,10,23` | 0 |
| `FUN_00770e80` | 325 | `1,20,61,111,132` | 0 |

The named set includes `memcpy`, `_memcpy`, `memcpy_s`, `_memcpy_s`, `memmove`, `_memmove`, `memmove_s`, `_memmove_s`, and `__VEC_memcpy`.

## What this means

This is a prioritization result only. It says the first slot3 search should focus on:

1. exact `+0x538` store-like uses;
2. exact `+0x538` address materializers passed to callees;
3. custom or inline copy code along a concrete alias-forwarding path.

It does **not** prove that bulk-copy provenance is absent.

Still open:

- compiler-inlined copies;
- custom copy helpers with nonstandard names;
- indirect/callback dispatch to copy routines;
- named copies deeper than four direct edges;
- any copy whose destination is not proven to be the selected HDVehicle wheel-runtime root.

## Gate

```text
shallow named memcpy/memmove surface empty = true
inline/custom bulk copies ruled out         = false
indirect copy dispatch ruled out             = false
deeper direct copy paths ruled out           = false
slot3 writer provenance proven               = false
P1.3 complete                                = false
provider count                               = 7
```

## Next step

Run the corrected `ShiftWheelRuntimeAliasExporter.java` against authoritative PC retail 1.02 Ghidra using machine displacement `+0x538`. Inspect store/address/callee candidates before expanding copy depth. Only extend bulk-copy tracing from a concrete alias-forwarding candidate so numeric/topological coincidence never becomes object identity.
