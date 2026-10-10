# Process 1A / P1.3A — `.rdata` exact-carrier RVA diagnostic closure

## Scope

The merged whole-image scan retained exactly two raw byte matches for `FUN_0076d100` RVA `0x0036d100`. Merged #1854 proved the executable `.text` subset has zero exact-carrier RVA byte literals, leaving only these two `.rdata` diagnostics.

This pass classifies those two diagnostics from authoritative retail machine transfer and exact table bytes.

## Result

The two matches occur at:

```text
0x00ad443f inside [0x00ad42c8, 0x00ad46c8)
0x00b664a7 inside [0x00b66330, 0x00b66730)
```

Both containing ranges are exactly `0x400` bytes, contain 256 four-byte elements, have identical SHA-256:

```text
85f4d25300d1437af965cebc94bf108d075b6dccff375290da83bc73aac2fb7e
```

and are nondecreasing when interpreted as unsigned 32-bit values.

Retail code establishes the element geometry independently for both copies:

- `0x0059cd29`/`0x0059cd2e` pass end `0x00ad46c8` and start `0x00ad42c8` to `FUN_00597db0`; that callee computes `(end-start)>>2` and compares `DWORD PTR [base+index*4]`.
- `0x00a485e8`/`0x00a485ed` load end `0x00b66730` and start `0x00b66330` before calling `FUN_00a485a0`; that callee likewise computes `(end-start)>>2` and compares `DWORD PTR [base+index*4]`.

Each raw RVA match begins at table offset `+0x177`, so its alignment is `+3 mod 4`. The bytes are:

```text
00 d1 36 00  -> unaligned little-endian value 0x0036d100
```

but they span the boundary between the aligned elements:

```text
+0x174 = 0x000032b7
+0x178 = 0x000036d1
```

Therefore `0x0036d100` is not stored as a 32-bit element in either machine-consumed table. It exists only as a cross-DWORD byte sequence.

No higher-level meaning is assigned to the tables; the proof needs only their exact four-byte element geometry and retail consumers.

## Gate

```text
non-.text exact-carrier RVA diagnostic subset complete = true
remaining raw diagnostics                              = 2
raw diagnostic stored as pointer element found         = false
whole-image raw exact-carrier RVA match subset complete= true
semantic pointer hit among raw RVA matches             = false
global relocated/RVA pointers ruled out                = false
runtime callback registration ruled out                = false
incoming indirect entry ruled out                      = false
runtime-generated/copied carrier pointers ruled out    = false
runtime-generated selected-wheel stores ruled out      = false
stored-or-escaped aliases ruled out                    = false
slot0 complete                                         = false
slot1 complete                                         = false
P1.3 complete                                          = false
provider count                                         = 7
```

## Limits

This closes the two raw byte matches retained by the existing whole-image RVA scan. It does **not** prove the absence of carrier pointers produced through relocations, encoding, arithmetic reconstruction, copying from another runtime source, callback registration, or other generated state.

The result also says nothing about selected-wheel **data-pointer** persistence; that remains a separate P1.3A frontier.

## Reproduce

```bash
python3 tools/ghidra/analyze_p1a_exact_carrier_rdata_rva_diagnostics.py \
  /path/to/SHIFT.exe \
  --output evidence/p1a_p13a_exact_carrier_rdata_rva_diagnostic_closure.json
```

## Next step

Remove raw absolute-VA/RVA carrier literals from the callback-seed frontier. Continue with PE relocation records and encoded/reconstructed/runtime-generated carrier pointers, and independently trace selected-wheel data-pointer persistence before any global stored-or-escaped-alias gate changes.
