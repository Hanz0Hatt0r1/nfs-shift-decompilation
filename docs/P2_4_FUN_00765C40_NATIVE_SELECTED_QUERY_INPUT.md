# Process 2 P2.4 — native selected `FUN_00765c40` query input

The selected BMW path already owns all three pre-query inputs outside the residual callback: current-BODY world position, persistent cache handle, and the exact BMW M3 E36 `+0x38e8` miss fallback.

This slice makes that ownership explicit with `Fun00765c40ExternalPassInput::selected_bmw_query_input()`. For a selected BMW request, the complete `Fun00765c40QueryInputBoundary` is materialized before the residual provider result is accepted. Validation rejects any provider result that changes the world position, cached handle, or miss fallback.

Generic historical fixtures without a selected world position retain their existing compatibility behavior; only the cached-handle provenance remains mandatory there.

This does not internalize the lower collision query implementation or the remaining `FUN_00765c40` producer arithmetic. The top-level provider remains present and the external provider count remains 7.
