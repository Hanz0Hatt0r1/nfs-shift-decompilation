# Process 1B: GetProcAddress wrapper static-entry surface

## Scope

This closes static publication/address-taking of generic resolver wrapper `FUN_0093dd2b` after the static `GetProcAddress` name surface was bounded.

Authority:

- PC retail 1.02 `SHIFT.exe`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`;
- Ghidra C export SHA-256 `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9` as navigation/cross-check only.

## Results

Wrapper VA/RVA: `0x0093dd2b` / `0x0053dd2b`.

Retail machine surface:

- whole-image exact absolute-VA literals: 0;
- whole-image exact RVA literals: 0;
- direct CALL transfers: 12;
- direct JMP transfers: 0.

The 12 exact direct callsites are the same callers whose proc-name arguments were resolved by `SHIFT.P1B.HDVehicle4330GetProcAddressStaticResolutionSurface/1`.

The Ghidra C export contains exactly 13 exact symbol occurrences:

- 1 definition;
- 12 direct invocations;
- 0 non-invocation/value/address-taking uses.

Therefore no static exact wrapper pointer seed is present through raw VA/RVA publication or source-visible address-taking.

## Adjudication

`generic_wrapper_static_entry_surface_complete=true`.

`generic_wrapper_static_address_taken_or_literal_seed_found=false` and `generic_wrapper_static_indirect_entry_seed_found=false`.

This does not close runtime-computed/copied/encoded wrapper addresses, opaque indirect entry, runtime-created function-pointer stores, or globally dynamic API resolution. Consequently `generic_wrapper_indirect_runtime_entry_ruled_out`, runtime patching, global indirect entry, manager identity, `0x004b86cf`, and aggregate P1.3 remain fail-closed. Provider count remains 7.
