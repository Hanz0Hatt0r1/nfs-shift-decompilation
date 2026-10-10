# Process 1B — HDVehicle+0x4330 PE loader-entry surface

This P1.3B slice bounds image-published and loader-managed ways for one of the 15 exact `HDVehicle+0x4330` carrier functions to be entered without an ordinary direct caller.

The proof parses the authoritative PC retail 1.02 PE headers/tables directly.

## Entrypoint

`AddressOfEntryPoint = 0x0050488a`, so the runtime entry VA is `0x0090488a`. It is not one of the 15 exact carrier entrypoints.

## Export table

The export directory is at RVA `0x00779d60`, size `0x6e57`, and names image `GeckoFnl.exe`.

It contains:

```text
509 function RVAs
509 named exports
0 zero function RVAs
0 forwarders
0 exact HDVehicle+0x4330 carrier exports
```

Thus none of the exact carrier functions is published through the PE export address table.

## TLS callbacks

The TLS directory is present at RVA `0x007672ac` (size `0x18`). `AddressOfCallbacks = 0x00aa9990`, and the first callback-array entry is zero. The TLS callback count is therefore zero.

## Load Config / SafeSEH / Guard tables

The PE Load Config data-directory entry is `(0,0)`. No SafeSEH or Guard function table can be published through that directory.

The PE exception data directory is also `(0,0)`. This is recorded only as a PE-table fact; it is **not** treated as absence of x86 MSVC inline EH metadata. The previously recovered `Unwind@` actions remain valid and are handled by their separate machine proofs.

## Result

The bounded PE-published/loader-managed entry subset closes negative for the exact carriers:

- process entrypoint: no carrier;
- export table: 509/509 entries checked, 0 carrier hits;
- TLS callback table: empty;
- Load Config published handler/guard tables: absent.

Runtime callback registration, function pointers computed at runtime, copied pointers, encoded pointers, and unresolved indirect dispatch remain open. Therefore the global indirect-entry, `HDVehicle+0x4330` runtime-alias, manager identity, final `0x004b86cf`, aggregate P1.3 and provider-removal gates remain fail-closed. Provider count remains 7.
