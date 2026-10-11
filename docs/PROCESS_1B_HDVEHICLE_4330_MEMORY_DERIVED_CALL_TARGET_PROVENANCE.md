# Process 1B: HDVehicle+0x4330 memory-derived call target provenance

## Result

The two positive memory-derived indirect calls recovered by v14 are narrowed against PC retail 1.02 image data and exact visible initializer/reset writers.

### `0x00553247`

The call loop reads the object table pointer from `0x00b83dc0`, then loads the callable entry from `[table+0x4]`.

Bounded visible table-pointer values are:

- image initial value `0x00acdd68`;
- initializer `0x00a79af0 -> 0x00a79b0d` writes `0x00acdd70`;
- reset loop `0x00a9d6d0` includes `0x00b83dc0` and writes `0x00acdd68`.

Therefore the bounded callable targets are:

- `[0x00acdd68+4] = 0x00553a90`;
- `[0x00acdd70+4] = 0x00553260`.

### `0x005539ac`

The target path reads the table pointer from `0x00b83ec0`, then `[table+0x4]`.

Bounded visible table-pointer values are:

- image initial value `0x00acdd68`;
- the 41-object reset loop at `0x00a9d730` reaches `0x00b83ec0` on its final iteration and writes `0x00acdd68`.

The bounded callable target is therefore `0x00553a90`.

## Carrier comparison

The union of bounded callable targets is `{0x00553260, 0x00553a90}`. Neither address is one of the 15 canonical P1B HDVehicle+0x4330 carriers, so this bounded static/initializer subset contributes **0 exact carrier hits**.

## Aggregate effect

`SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/15` increases bounded coverage classes from **18 to 19** and keeps the bounded exact-carrier hit count at **0**.

## Boundary

This is not full runtime target identity. Computed aliases, arbitrary runtime mutation, heap/object replacement and other writer paths for `0x00b83dc0` / `0x00b83ec0` remain open. Consequently global `indirect_entry_into_carriers`, the manager+0x374 identity join, slot2 `0x004b86cf`, and aggregate P1.3 remain fail-closed. Provider count remains **7**.

## Next

Bound computed/alias/runtime writers for the two source slots, then return to the remaining direct/indirect live-taint call boundaries.
