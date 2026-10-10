# Process 1A / P1.3A — exact imagebase + carrier-RVA immediate construction closure

## Scope

The merged static-carrier handoff closes raw absolute carrier VAs, raw carrier-RVA byte sequences, exported static tables and standard PE base relocations. One remaining static-to-runtime mechanism is manual arithmetic from the preferred PE base `0x00400000`.

This pass deliberately closes only the **exact-immediate** form: a recovered function must contain an exact scalar use of the preferred image base and an exact scalar use of one of the 16 canonical carrier RVAs. Split additions, table-derived values, encoded values and runtime reconstruction remain outside this proof.

## Retail result

The hash-locked PC retail 1.02 executable disassembles to **2,847,850** instructions. Exact scalar `0x00400000` occurs **52** times:

- `test`: 25
- `or`: 8
- `mov`: 7
- `push`: 5
- `cmp`: 4
- `and`: 2
- `sub`: 1

Thirteen of those uses are value-materializing `mov`/`push`/`sub` instructions. They are retained as observations; numeric use of `0x00400000` alone is not treated as image-pointer identity because several uses are flags, sizes or CRT/startup state.

Across the same authoritative disassembly there are **zero exact scalar occurrences of every canonical carrier RVA**:

`0x00358b50`, `0x00355950`, `0x00370e80`, `0x00355a60`, `0x00352fc0`, `0x00360b50`, `0x00363570`, `0x00355f80`, `0x0036d100`, `0x00358810`, `0x00369ef0`, `0x003675f0`, `0x003682c0`, `0x00366510`, `0x00358fc0`, `0x00365c40`.

Therefore no recovered function can contain the bounded `exact imagebase scalar + exact carrier RVA scalar` construction shape. The same-function candidate count is exactly zero.

## Gate

```text
exact imagebase + exact carrier-RVA immediate subset complete = true
same-function candidates                                      = 0
manual imagebase + exact RVA immediate construction ruled out = true
all manual/split imagebase arithmetic ruled out               = false
encoded/reconstructed carrier pointers ruled out              = false
runtime-generated/copied carrier pointers ruled out           = false
runtime callback registration ruled out                       = false
incoming indirect entry ruled out                              = false
slot0 complete                                                 = false
slot1 complete                                                 = false
P1.3 complete                                                  = false
provider count                                                 = 7
```

## Next step

Remove exact-RVA immediate reconstruction from the carrier frontier. Continue with split/table-derived/encoded carrier reconstruction and runtime callback registration/incoming dispatch. Selected-wheel data-pointer persistence remains an independent open frontier.
