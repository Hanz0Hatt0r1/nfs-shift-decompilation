# Process 1A / P1.3A — bounded static carrier-seed handoff

## Purpose

Several merged P1A steps now close distinct **on-disk/static** ways an exact carrier entrypoint could appear before runtime. This handoff composes those bounded classes so later work does not reopen them while tracing runtime-generated callbacks and selected-wheel aliases.

## Closed bounded classes

For the canonical 16 exact carriers:

```text
exported vtable carrier targets                     0
exported static-table carrier pointers              0
whole-image raw absolute-VA carrier literals        0
whole-image raw carrier-RVA byte matches            2
semantic pointer hits among those RVA matches       0
standard PE base-relocation records present         false
exact-carrier CALLIND caller edges                   0
```

The two raw RVA matches are already machine-classified as cross-DWORD byte sequences inside 256-element `u32` tables, not aligned pointer elements.

The retail PE also has `IMAGE_FILE_RELOCS_STRIPPED`, a zero `BASERELOC` directory and no `.reloc` section, so the standard Windows loader relocation path is absent.

## Incoming indirect index caveat

The Drive Ghidra index contains 19,500 `indirect=true` call records, but **zero** resolved indirect targets. Therefore:

```text
incoming indirect index frontier captured          true
resolved target coverage                            false
index can prove exact-carrier absence               false
```

This is an explicit capability gap, not negative semantic evidence.

## Gate

```text
bounded on-disk/static exact-carrier seed surface complete = true
bounded static seed hit found                              = false
standard PE loader relocation seed path ruled out          = true
incoming indirect index capability gap explicit            = true

runtime callback registration ruled out                    = false
incoming indirect entry ruled out                          = false
manual imagebase+RVA construction ruled out                = false
encoded/reconstructed carrier pointers ruled out            = false
runtime-generated/copied carrier pointers ruled out         = false
runtime-generated selected-wheel stores ruled out           = false
stored-or-escaped aliases ruled out                        = false
slot0 complete                                             = false
slot1 complete                                             = false
P1.3 complete                                              = false
provider count                                             = 7
```

## Scope boundary

The word **complete** above applies only to the explicitly composed static classes:

- exported vtable/static-table literal targets;
- raw 32-bit absolute-VA literals;
- raw exact-carrier RVA byte matches;
- standard PE base relocation records.

It does not include runtime arithmetic, manual `imagebase + RVA`, encoded/reconstructed addresses, callback registration, incoming runtime dispatch, copied/generated code pointers, or selected-wheel data-pointer persistence.

## Reproduce

```bash
python3 tools/ghidra/build_p1a_static_carrier_seed_handoff.py \
  --output evidence/p1a_p13a_static_carrier_seed_handoff.json
```

## Next step

Stop spending effort on raw static carrier literals and PE loader relocations. Trace runtime/generated/encoded carrier pointer construction and callback registration/incoming dispatch. In parallel, continue selected-wheel data-pointer persistence; neither runtime frontier is authorized to close yet.
