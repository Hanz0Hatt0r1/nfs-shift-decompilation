# Process 1 — exact `manager+0x378` indexed selection

`FUN_0045da80` is an exact PC-retail structural writer of `FUN_00489ad0()` singleton field `+0x378`.

```text
0x0045da84 call FUN_00489ad0
0x0045da89 mov EDX,[EBP+0x0c]
0x0045da8c mov ESI,EAX
0x0045da8e cmp EDX,[ESI+0x2c4]
0x0045da94 jb 0x0045daa3
0x0045da96 xor EAX,EAX
0x0045da98 mov [ESI+0x378],EAX
...
0x0045daa3 lea ECX,[ESI+0x2a0]
0x0045daa9 call FUN_0054ed00
0x0045daae mov [ESI+0x378],EAX
```

Therefore:

- when the supplied index is outside the manager-side bound, `manager+0x378 = 0`;
- when it is admitted, `manager+0x378 = FUN_0054ed00(manager+0x2a0,index)`.

`FUN_0054ed00` is the already bounded read-only indexed-address accessor. This establishes a concrete relationship between the real manager collection and sibling field `+0x378`, but does not establish the semantic type of the collection entry.

The Ghidra export additionally places `FUN_0045da80` at slot 0 of candidate table `0x00ab563c`, alongside `FUN_00459070`, `FUN_0066d450`, and `FUN_004692e0`. That table is navigation evidence only: there is no proven class/interface identity and none is assigned here.

## Fail-closed result

Proven:

- exact manager root from `FUN_00489ad0()`;
- exact indexed read from `manager+0x2a0`;
- exact destination `manager+0x378`;
- exact zero fallback for an out-of-range index.

Still open:

- how real `manager+0x2a0` entries are registered/produced;
- whether a selected entry is `HDVehicle+0x4330`;
- `manager+0x374 == HDVehicle+0x4330`;
- selected non-sentinel `HDVehicle+0x64e8` provenance;
- retail control/input producer closure.

Provider count remains **7**.

The next useful search is no longer the rejected `0x00469b1d` edge. It is the true manager-root registration/producer surface for `manager+0x2a0`, plus exact sibling `manager+0x374` writers/selection ownership.
