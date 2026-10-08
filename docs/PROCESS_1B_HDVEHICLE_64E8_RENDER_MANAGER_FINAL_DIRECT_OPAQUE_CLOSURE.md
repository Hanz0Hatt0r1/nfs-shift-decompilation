# Process 1B — final bounded direct opaque render-manager closure

## Scope

This slice exhausts the four remaining targets in the frozen 17-target direct receiver-transfer worklist rooted at exact render-manager outer pointer `0x00bc185c`.

PC retail 1.02 machine transfer is authoritative. Ghidra SQLite is used only for boundaries, names and fingerprints. Completion here is intentionally limited to this finite direct-target worklist; it is not a global unknown-origin pointer proof.

## `0x0045bfc0 -> FUN_00d51560`

The exact root enters in `ECX` at `0x004d19e6` and is copied to `EDI`. The immediate helper `FUN_00624930` does not read incoming `ECX`: it initializes/returns singleton `0x00befbe0`. Within `FUN_00d51560`, the saved root has only two semantic uses, both through `root+0x0c` (`0x00d5157f`, `0x00d515ec`). The exact root is never stored, returned or re-forwarded.

## `0x0045cc50 -> FUN_00d517b0`

The exact root is copied to `EBX`. Across the full body, its only register uses are:

```text
root + 0x520
root + 0x780
root + 0x9e0
```

The three derived pointers are written to stack locals at `[ebp-0xac]`, `[ebp-0xa8]`, `[ebp-0xa4]`. After those stores, those local slots have zero reads in the bounded body. The exact root itself is neither stored nor returned nor explicitly forwarded as an argument.

## `0x0045db50 -> FUN_00d51bd0`

Entry `ECX` is initially placed in stack local `[ebp-0x4]`. A pointer to that local is routed through `FUN_004651a0` to `FUN_00d77800`. The helper's first dereference of that pointer is:

```text
0x00d77868  mov dword [esi],0
```

There is no earlier read through the pointer. Thus the original exact root is destroyed before `FUN_00d51bd0` later reloads `[ebp-0x4]`; the reload can only observe zero or a replacement object written by the helper.

## `0x00462400`

Thirteen exact-root callsites enter with the root in `ECX`. The function saves it in `ESI`; direct root uses are only fields `+0xd20/+0xd21` and calls to `FUN_0045e6e0`.

`FUN_0045e6e0` saves the same receiver but its nested paths are bounded:

- `FUN_00633980` ignores entry `ECX` and replaces it with singleton storage;
- `FUN_0045abe0` and `thunk_FUN_004300ae` are already closed by `SHIFT.HDVehicle64e8RenderManagerEntryAliasNonConsumptionSurface/1`;
- `FUN_0045abf0` does not read entry `ECX`; its first nested `FUN_00886980` also ignores `ECX`, and the function replaces `ECX` before later use.

No path stores or returns the exact outer root.

## Worklist transition

The frozen direct worklist started with 17 targets. Prior Process 1B contracts closed 13. This slice closes the final four, so:

```text
bounded direct targets: 17 / 17 complete
remaining direct targets: 0
```

This does **not** close external/unknown-origin exact-root aliases or two-unknown-origin/cross-control-flow `HDVehicle+0x4330` reconstruction. The manager `+0x374 -> HDVehicle+0x4330` identity join, literal `0x004b86cf`, P1.3 completion and provider removal therefore remain fail-closed. External provider count remains 7.
