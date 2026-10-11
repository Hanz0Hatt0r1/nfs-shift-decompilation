# Process 1A / P1.3A — `+0xd94` loop source key semantics

The loop receiver is copied from DWORD 0 of a `0xd98` source record. This subset classifies how that DWORD is used while `FUN_00503390` selects the source record that becomes the derived loop record.

At `0x005033f1`, DWORD 0 of the selected source record is loaded. A null value is rejected before comparison. A second key is obtained from the caller-side object; if that key is null, `0x00aa9b60` is substituted, whose first byte is NUL and therefore represents an empty C string.

The non-null source-record DWORD 0 and the comparison key are passed to `0x00901179`. Its default path tail-jumps to `0x00901071`, which reads one byte at a time, folds ASCII `A` through `Z` by adding `0x20`, compares the folded bytes, and stops on NUL. Its locale-aware branch passes the same two character-pointer inputs to `0x009010a6`.

Therefore a non-null `source_record+0` selected by this path is used as a case-insensitive NUL-terminated string/key-compatible pointer. This usage does not prove a unique C++ object type or constructor, and it does not alone prove that the pointer cannot alias the runtime writer singleton.

Promoted only: `p13a_fun005ffc50_writable_callback_pair_d94_loop_source_key_semantics_subset_complete` and `writable_callback_pair_d94_loop_source_record_dword0_string_key_compatible`. Writer/consumer identity, runtime-writer relevance, `+0xd94` value range, and aggregate callback/slot/P1.3 gates remain fail-closed.

Next: classify producer/copy paths for `source_record+0` and combine them with the bounded `DAT_00bc185c` direct/call propagation frontiers.
