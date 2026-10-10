# Process 1A / P1.3A — PE base-relocation carrier-pointer closure

## Scope

After raw absolute-VA/RVA carrier literals are bounded, one standard way an on-disk RVA or preferred-base pointer could become a runtime code pointer is Windows PE loader base relocation.

This pass checks the authoritative retail PE headers and closes only that standard loader mechanism.

## Retail PE result

```text
format                         PE32
image base                     0x00400000
file characteristics           0x0103
IMAGE_FILE_RELOCS_STRIPPED     true
NumberOfRvaAndSizes            16
BASERELOC directory RVA        0x00000000
BASERELOC directory size       0
.reloc section present         false
sections                       .text .rdata .data .tls .rsrc .secu
```

The retail image therefore contains no PE base-relocation records for the loader to apply.

This excludes the standard `IMAGE_DIRECTORY_ENTRY_BASERELOC` path as a source of runtime carrier code pointers.

## Gate

```text
standard PE base-relocation subset complete             = true
PE base-relocation records present                       = false
PE loader carrier-pointer relocation path ruled out      = true
manual imagebase+RVA construction ruled out              = false
encoded/reconstructed carrier pointers ruled out         = false
runtime callback registration ruled out                  = false
incoming indirect entry ruled out                        = false
runtime-generated/copied carrier pointers ruled out      = false
runtime-generated selected-wheel stores ruled out        = false
stored-or-escaped aliases ruled out                      = false
slot0 complete                                           = false
slot1 complete                                           = false
P1.3 complete                                            = false
provider count                                           = 7
```

## Limits

No `.reloc` directory does not mean “no runtime code pointers.” The program can still:

- add the preferred image base to an RVA manually;
- reconstruct or decode a pointer arithmetically;
- copy a pointer produced elsewhere at runtime;
- register callbacks dynamically;
- reach carrier functions through another runtime dispatch mechanism.

Selected-wheel **data-pointer** persistence is independent of the PE loader relocation mechanism and remains open.

## Reproduce

```bash
python3 tools/ghidra/analyze_p1a_pe_base_relocation_carrier_frontier.py \
  /path/to/SHIFT.exe \
  --output evidence/p1a_p13a_pe_base_relocation_carrier_closure.json
```

## Next step

Trace manual image-base/RVA reconstruction plus encoded/runtime-generated carrier pointers and callback registration. Continue selected-wheel data-pointer persistence independently before changing global stored-or-escaped-alias gates.
