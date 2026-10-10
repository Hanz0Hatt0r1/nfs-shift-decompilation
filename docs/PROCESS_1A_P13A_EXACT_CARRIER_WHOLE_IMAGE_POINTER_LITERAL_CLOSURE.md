# Process 1A / P1.3A — whole-image exact-carrier pointer literal closure

## Scope

Merged #1848 closes finite exported static callback/target inventories. This pass adds an independent PC-retail whole-file scan for the simplest static registration seed: a raw little-endian 32-bit **absolute VA** equal to one of the 16 exact carrier entrypoints.

The scan covers every byte of the authoritative 8,801,792-byte `SHIFT.exe`, not only Ghidra candidate tables.

## Retail result

Authority:

```text
SHA-256   eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
PE32 base  0x00400000
file size  8,801,792
carriers   16
```

Whole-file absolute-VA result:

```text
encoding                         little-endian 32-bit absolute VA
searched bytes                   8,801,792
exact carrier literal hits       0
```

Therefore none of the 16 exact carrier entrypoints appears anywhere in the on-disk retail image as a raw absolute 32-bit code-pointer literal.

## RVA diagnostic

The analyzer also searches the byte encoding of `carrier_va - image_base`, but this surface is **diagnostic only** and does not drive a semantic gate.

Exactly two raw RVA byte-sequence matches occur, both for `FUN_0076d100` RVA `0x0036d100`:

```text
file 0x006d2e3f -> image 0x00ad443f (.rdata), offset mod 4 = 3
file 0x00764ea7 -> image 0x00b664a7 (.rdata), offset mod 4 = 3
```

Both are unaligned byte-sequence collisions. Numeric equality to an RVA is not treated as function-pointer identity.

## Gate

```text
whole-image exact-carrier absolute-VA literal subset complete = true
absolute-VA carrier literal hit found                          = false
absolute-VA carrier literal hit count                          = 0
runtime callback registration ruled out                        = false
incoming indirect entry ruled out                              = false
relocated/RVA-encoded carrier pointers ruled out               = false
runtime-generated/copied carrier pointers ruled out            = false
runtime-generated selected-wheel stores ruled out              = false
stored-or-escaped aliases ruled out                            = false
slot0 complete                                                 = false
slot1 complete                                                 = false
P1.3 complete                                                  = false
provider count                                                 = 7
```

## Limits

This closure is intentionally narrower than “no callback registration.” It rejects only raw absolute-VA literals in the on-disk image. It does not reject:

- direct `rel32` calls, which belong to the already-composed call-target surface;
- RVA/relocation-based code pointers;
- encoded or reconstructed pointers;
- copied pointers whose original seed is produced dynamically;
- runtime callback registration;
- incoming indirect entry whose target is resolved only at runtime;
- selected-wheel **data-pointer** persistence.

## Reproduce

```bash
python3 tools/ghidra/analyze_p1a_exact_carrier_whole_image_pointer_literals.py \
  /path/to/SHIFT.exe \
  --output evidence/p1a_p13a_exact_carrier_whole_image_pointer_literal_closure.json
```

## Next step

Bound RVA/relocation-based or runtime-generated carrier code pointers and callback-registration paths, then join any positive registration to its eventual indirect consumer. In parallel, continue runtime-generated/copied selected-wheel data-pointer provenance before changing global stored-or-escaped-alias gates.
