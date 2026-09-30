# Phase 542 — production FLAT normalization and leaf consumers

Phase 542 fixes a production-only FLAT decoding gap exposed by the real
Silverstone Era 3 Grand Prix SGB and extends the direct-record runtime consumer
map without assigning unproven class names.

## Serialized versus runtime span word

The previous parser treated FLAT node `+0x1c` as if every file already carried
the runtime-normalized high-byte marker.

The retail loader proves a two-stage contract instead:

1. `FUN_006a5270` derives a boolean from SGB header bit 2.
2. `FUN_006a48d0 -> FUN_0068a8b0` forwards the FLAT body.
3. When header bit 2 is clear, `FUN_006afd30 -> FUN_006af6c0` rewrites a
   negative signed `+0x1c` value as a positive low-24-bit byte span and then
   writes the runtime depth/termination marker into the high byte.

For the retail Silverstone Grand Prix root:

```text
serialized:  0xFFF7E3E0  == -531488
runtime:     0x01081C20
span bytes:  0x081C20     == 531488
```

The corrected parser preserves both serialized and normalized values.

## Production corpus closure

The observation in
`evidence/silverstone_era3_grandprix_flat_runtime_observation.json` identifies
the source BFF and SGB by SHA-256 without committing raw game data.

After source-equivalent normalization the production FLAT body decodes as:

- 1,913 tree nodes;
- 7,348 direct records;
- maximum structural depth 10;
- 629 serialized negative terminal spans;
- runtime index coverage exactly `0..7347` with no duplicates or gaps.

This replaces a previous full decode failure on that same retail FLAT body.

## Direct-record consumer contract

The already-proven direct record remains `0x40` bytes.

### `+0x3c` — runtime index

`FUN_006af780` uses this value to join the record to:

- primary runtime entry `index * 0x28`, source-record pointer at entry
  `+0x20`;
- secondary runtime entry `index * 0x40`, with parent node at `+0x30`,
  source record at `+0x34`, and primary-entry pointer at `+0x38`.

`FUN_006af5a0` later resolves the same secondary slot and dispatches through
its vtable `+0x08`.

### `+0x38` — nullable direct object pointer slot

This field is still not assigned a concrete class identity.

Its operational use is nevertheless source-backed:

- `FUN_006af640` traverses child FLAT nodes first, then passes populated
  direct-record `+0x38` pointers to `FUN_006b0440` for recursive scene-object
  lookup;
- `FUN_006af830` owns fallback teardown when no normalized secondary slot is
  present;
- the fallback path releases a nested pointer at object `+0x08`, clears the
  leaf pointer, decrements a refcount at object `+0x20`, and calls vtable
  `+0x10` when the refcount reaches zero;
- when a secondary slot exists, its vtable `+0x0c` handles the release path.

The Silverstone serialized corpus contains zero persisted non-null `+0x38`
pointer words, which is consistent with these being runtime object links rather
than portable resource identifiers.

## Boundary

Phase 542 does not name the concrete class behind direct-record `+0x38`, and
does not assign semantics to the other raw FLAT record words.

The next scene task is to correlate the remaining direct-record float payload
and OBJECT/HIERARCHY consumers against real SGB records before exposing them to
RenderBinding.
