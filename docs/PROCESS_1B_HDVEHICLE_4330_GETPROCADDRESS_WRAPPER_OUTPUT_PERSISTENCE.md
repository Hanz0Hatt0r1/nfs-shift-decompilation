# Process 1B: GetProcAddress wrapper output persistence

## Scope

This contract follows the resolved function pointer produced by the generic resolver wrapper `FUN_0093dd2b` for all 12 exact direct machine callers already bounded by `SHIFT.P1B.HDVehicle4330GetProcAddressWrapperStaticEntrySurface/1`.

Retail authority is PC 1.02 `SHIFT.exe` SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

## Result

All 12 direct wrapper callers pass the output destination as an address of an EBP-relative stack local. There are no non-stack output destinations.

The resolved pointer is consumed by 11 unique indirect calls. Two alternative resolution sites (`0x0093d06e` and `0x0093d086`) write the same `[ebp-0x18]` local and converge on the single indirect call at `0x0093d09b`.

Across every bounded live interval, the exact resolved pointer value has:

- 0 value copies before terminal use/kill;
- 0 persistent stores to object/global/heap memory;
- 0 pushes/forwards of the function-pointer value;
- only the expected indirect call through the local slot.

The three longer-lived locals are explicitly killed/reused at `0x009976d8`, `0x00997c65`, and `0x009a8ac9` after their function-pointer call.

Therefore `generic_wrapper_direct_output_persistence_subset_complete=true` and `generic_wrapper_direct_outputs_stack_local_only=true`.

## Limits

This is deliberately not a global function-pointer-store closure. Direct `GetProcAddress` calls outside `FUN_0093dd2b`, the 86 calls through loaded `GetProcAddress` registers, runtime/indirect entry into the wrapper, externally supplied function pointers, and unrelated runtime-populated tables remain open.

Accordingly `generic_function_pointer_stores_copies_ruled_out`, `runtime_generated_or_copied_function_pointers_ruled_out`, `runtime_patching_or_generated_code_ruled_out`, `indirect_entry_into_carriers_ruled_out`, `manager_374_join_to_hdvehicle_4330_complete`, `last_literal_0x004b86cf_rejected`, and aggregate P1.3 remain fail-closed. External provider count remains 7.

## Next step

Classify result persistence for direct-IAT and register-loaded `GetProcAddress` callsites, especially the known globals written from resolution results, then compose bounded runtime-populated function-pointer storage coverage.
