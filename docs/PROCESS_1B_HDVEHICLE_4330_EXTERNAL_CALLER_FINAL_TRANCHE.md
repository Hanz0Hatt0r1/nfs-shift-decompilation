# Process 1B — HDVehicle+0x4330 external caller final tranche

This P1.3B slice closes the last three direct external callers from the exact incoming-call frontier. Retail machine transfer remains the semantic authority; Ghidra names and callgraph records are navigation/cross-check evidence only.

## `FUN_00aa2850`

The function is a two-instruction root wrapper:

```text
0x00aa2850  mov ecx,0x00c13700
0x00aa2855  jmp FUN_00769520
```

It therefore supplies the exact HDVehicle root to an already-proven root-derived `+0x4330` materializer. It does not forward a pre-existing `HDVehicle+0x4330` alias.

## `Unwind@00a7063f`

This path is deliberately **not** rejected because Ghidra labels it `Unwind@`.

Retail MSVC EH metadata proves that `0x00a7063f` is state-8 cleanup action in `FuncInfo 0x00b71bbc`. The corresponding handler stub `0x00a7064d` is installed by exactly two parent functions:

- `FUN_00769520` at `0x00769526`;
- `FUN_0076b130` at `0x0076b136`.

Both parent functions are already machine-proven exact-HDVehicle-root materializers, and both execute `ESI=ECX` followed by `[EBP-0x10]=ESI`. The cleanup action executes:

```text
mov ecx,[ebp-0x10]
add ecx,0x4330
jmp FUN_00756050
```

So this is a **positive exceptional root-derived `HDVehicle+0x4330` materializer**. It is bounded to the same exact root and the same already-bounded consumer `FUN_00756050`; it is not an unknown/pre-existing alias entry.

## `Unwind@00a72322`

Retail EH metadata maps this action through `FuncInfo 0x00b73e7c` and handler stub `0x00a7234b` back to `FUN_00798df0`. The cleanup receiver is syntactically the parent stack local:

```text
lea ecx,[ebp-0x238c]
jmp FUN_00756050
```

Therefore this path is stack-local and is not `HDVehicle+0x4330`.

## Result

Across the three P1B tranches, all **7/7 external caller functions and 11/11 external direct callsites** into the 15 exact `HDVehicle+0x4330` carrier functions now have receiver provenance.

The direct external incoming surface can close with no pre-existing `HDVehicle+0x4330` alias found. One additional exceptional root-derived materializer is positively admitted and bounded.

This does **not** close indirect entry, runtime-generated/copied function pointers, or other non-root-derived runtime aliases. Consequently `global_runtime_derived_4330_alias_surface_complete`, `manager_374_join_to_hdvehicle_4330_complete`, final `0x004b86cf`, aggregate P1.3, and provider removal remain fail-closed. Provider count remains 7.
