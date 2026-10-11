# Process 1B: HDVehicle+0x4330 base/indexed implicit stack carriers

## Result

A SHA-locked scan of PC retail 1.02 (`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`) extends the existing 63 base/index-addressed writable `.data` loads with implicit stack-carrier classification inside the same 16-decoded-instruction bounded propagation window.

The scan finds:

- **5** tainted `push GPR` events;
- **0** tainted `pop GPR` reloads;
- **0** `add/sub esp, imm` normalization events while a base/index-derived value remains live;
- **0** tainted-register indirect `CALL/JMP` transfers;
- **5** direct-call argument escapes into **4 unique direct callees**.

Exact escape frontier:

| Load | Effective address | Push | Call | Direct callee |
| --- | --- | --- | --- | --- |
| `0x004b1c10` | `0x00b82034` | `0x004b1c17` | `0x004b1c1b` | `0x006329e0` |
| `0x004cd45d` | `0x00b822a4` | `0x004cd464` | `0x004cd46b` | `0x00632c70` |
| `0x005f51e0` | `0x00b869d0` | `0x005f51e2` | `0x005f51ed` | `0x00403c90` |
| `0x008d1951` | `0x00b95320` | `0x008d1958` | `0x008d1960` | `0x008b4c70` |
| `0x00d742fd` | `0x00b82030` | `0x00d74304` | `0x00d74308` | `0x006329e0` |

`0x006329e0` receives two of the five values; the other three callees receive one each.

## Aggregate effect

`SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/12` composes this surface and increases bounded coverage classes from **15 to 16**. Bounded exact carrier hits remain **0**.

This is deliberately **not** a negative closure of stack-derived provenance. The five pushed values cross direct-call boundaries, so callee-side argument provenance remains open and becomes a smaller exact work queue.

## Gates

Still fail-closed:

- callee-side propagation from the five direct argument escapes;
- inter-block/phi carry;
- aliases and runtime mutation;
- runtime-generated/copied function pointers;
- global `indirect_entry_into_carriers`;
- `manager+0x374 -> HDVehicle+0x4330` identity join;
- `0x004b86cf` / P1.3.slot2;
- aggregate P1.3.

External provider count remains **7**.

## Next

Classify the four unique direct callees (`0x006329e0`, `0x00632c70`, `0x00403c90`, `0x008b4c70`) for argument forwarding, storage, return, or indirect dispatch. Then continue with bounded inter-block carry.
