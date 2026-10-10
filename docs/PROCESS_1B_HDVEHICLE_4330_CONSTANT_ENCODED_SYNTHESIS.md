# Process 1B — HDVehicle+0x4330 constant-only encoded synthesis

`SHIFT.P1B.HDVehicle4330ConstantEncodedSynthesis/1` bounds one remaining exact-carrier pointer source on PC retail 1.02: straight-line register synthesis from constants and common arithmetic/bitwise transforms.

## Authority

The analyzer is locked to retail `SHIFT.exe` SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`, size 8,801,792. GNU `objdump -d -Mintel` machine disassembly adjudicates this subset.

The target set is the canonical Process 1B 15-function `HDVehicle+0x4330` carrier set.

## Bounded model

Seven GPRs (`EAX/EBX/ECX/EDX/ESI/EDI/EBP`) are propagated inside straight-line regions. The model recognizes:

- immediate/register `mov`;
- `xor/add/sub/or/and` with immediate operands;
- `inc/dec/neg/not`;
- immediate `shl/sal/shr/sar/rol/ror`;
- `lea reg,[reg+/-imm]`.

State is reset at every call, jump/conditional branch, loop, return, interrupt or other recognized control transfer. Unknown writes kill the destination register.

## Retail result

The scan covers **2,847,850 decoded instructions** and observes:

- **67,970** constant seeds: 38,128 `mov reg,imm` plus 29,842 `xor reg,reg` zero seeds;
- **2,168** recognized arithmetic/bitwise/LEA transitions while a constant value is live;
- **0** synthesized values equal to any canonical Process 1B carrier VA.

The largest transition classes are `neg` (610), `inc` (493), `lea` (294), `sub` (247), `add` (245), and `shl` (136). None reaches an exact carrier entrypoint.

## Adjudication

This promotes only:

`constant_only_encoded_carrier_synthesis_subset_complete=true`

and records:

`constant_only_encoded_exact_carrier_synthesis_found=false`.

It does **not** promote the global computed/encoded, runtime-generated/copied, generic store/copy, incoming-indirect or P1.3 gates.

## Remaining frontier

Still open by construction:

- memory/table-derived values;
- delayed runtime module-base consumers owned by P1A;
- split arithmetic across control-flow boundaries/path joins;
- opaque helper returns;
- runtime patching;
- pointers copied from runtime-created storage.

The next useful P1B step is to bound memory/table-derived or cross-block exact-carrier reconstruction and classify any positive store/copy sink.
