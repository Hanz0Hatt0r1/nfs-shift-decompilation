# Process 1A / P1.3A — executable `.text` exact-carrier RVA literal closure

## Scope

Merged `SHIFT.P1A.P13AExactCarrierWholeImagePointerLiteralClosure/1` found zero raw absolute-VA carrier literals across the complete retail image and retained two unresolved raw RVA byte-sequence matches in `.rdata`.

This step partitions that already-authoritative whole-image result by PE section and closes only the executable `.text` byte-literal subset.

## Result

Authoritative PC retail 1.02 `.text`:

```text
section RVA                         0x00001000
raw bytes                            6,964,736
exact carrier entrypoints                   16
encoding searched                   little-endian 32-bit RVA
exact-carrier RVA literal hits               0
```

Therefore no raw exact-carrier RVA byte sequence occurs in the on-disk executable `.text` section.

The two whole-image RVA matches remain outside this closure and stay unresolved:

```text
FUN_0076d100 RVA 0x0036d100
  file 0x006d2e3f -> .rdata, offset mod 4 = 3
  file 0x00764ea7 -> .rdata, offset mod 4 = 3
```

Neither match is promoted to a function pointer nor rejected as a non-pointer here.

## Gate

```text
.text exact-carrier RVA literal subset complete        = true
.text exact-carrier RVA literal hit found              = false
.text exact-carrier RVA literal hit count              = 0
non-.text exact-carrier RVA matches unresolved         = true
global RVA/relocation carrier pointers ruled out       = false
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

This result says only that the raw 32-bit RVA byte encoding of an exact carrier entrypoint is absent from `.text`. It does not exclude:

- direct `rel32` transfers;
- relocation-backed or encoded code pointers;
- computed/reconstructed pointer values;
- runtime callback registration;
- incoming indirect entry;
- the two unresolved `.rdata` byte matches;
- selected-wheel data-pointer persistence.

## Reproduce

```bash
python3 tools/ghidra/build_p1a_exact_carrier_text_rva_literal_closure.py \
  --output evidence/p1a_p13a_exact_carrier_text_rva_literal_closure.json
```

## Next step

Classify the two unresolved `.rdata` RVA matches by exact data/xref provenance or move to runtime-generated/relocated callback registration paths. Continue selected-wheel data-pointer persistence as an independent frontier before changing any global stored-or-escaped-alias gate.
