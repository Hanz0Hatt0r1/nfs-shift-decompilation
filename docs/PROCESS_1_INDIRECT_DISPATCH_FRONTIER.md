# Process 1 — indirect dispatch/static-reference frontier

The persistent BODY integration chain is closed below `FUN_00770e80`.  The
remaining high-priority ownership gap is above that update, especially the
second direct caller:

```text
UNKNOWN OWNER
  -?-> FUN_0079b2d0
        -> FUN_00770e80
```

The current Ghidra direct callgraph contains no incoming edge for
`FUN_0079b2d0`.  That absence is **not** proof that the function is a root.  A
vtable, callback, function-pointer table or other indirect dispatcher remains a
valid static possibility.

This block adds:

```text
tools/ghidra/build_indirect_dispatch_frontier.py
```

Output format:

```text
SHIFT.GhidraIndirectDispatchFrontier/1
```

No original-game execution or runtime capture is involved.

## Evidence layers

The analyzer intentionally keeps direct observations and heuristics separate.

### Direct Ghidra observations

The following inputs are treated only according to what they literally contain:

- `functions.jsonl` — target function identity/bounds;
- `callgraph.jsonl` — direct edges and unresolved computed-call sites;
- `switches.jsonl` — computed jump instructions and recovered destinations;
- `static_tables.jsonl` — defined static-data bytes;
- `strings_xrefs.jsonl` — exact code/string relationships.

For static data the tool searches for the target address encoded with the
exported pointer size and records every byte occurrence as:

```text
table address
byte offset
cell address
pointer alignment
raw-truncated state
```

A byte occurrence proves only that those bytes occur in the exported static data.
It does not prove that the cell is a callback, vtable slot, owner reference or
active runtime pointer.

### Heuristic candidate layers

`vtables.json` is exported as `SHIFT.GhidraVtableCandidates/1` with status
`heuristic-candidates`.  `constructors.jsonl` likewise contains
`vtable-xref-candidate` rows.

For a requested target, the analyzer reverse-indexes:

```text
target function
  -> heuristic vtable candidate slot(s)
      -> exact Ghidra function xrefs to candidate table start
      -> constructor-candidate rows referencing that candidate table
```

The resulting evidence state is still `ambiguous`.  Neither candidate layer is
promoted to a retail class, constructor or virtual-dispatch owner.

## `FUN_0079b2d0` workflow

Run against the existing full static export:

```bash
python3 tools/ghidra/build_indirect_dispatch_frontier.py \
  out/shift_ghidra_database \
  0x0079b2d0 \
  --json-out out/vehicle_indirect_dispatch_frontier.json \
  --targets-out out/vehicle_indirect_dispatch_targets.txt
```

The report records:

- whether the direct incoming-call set is still empty;
- the function's direct outgoing calls;
- unresolved outgoing indirect calls;
- its internal computed-jump candidates;
- every heuristic vtable candidate containing the function and the exact slot;
- functions with Ghidra references to each matching candidate table;
- constructor-candidate rows attached to those tables;
- raw static-data occurrences of the function pointer;
- a deduplicated instruction-export target list consisting of the original
  function plus functions that reference matching vtable candidates.

The next proof step is to export p-code/instructions for those candidate owner
functions and prove the pointer flow at the exact reference/callsite.  Only then
may an indirect ownership or virtual-dispatch edge be promoted.

## Upper direct frontier

The already saved caller-frontier evidence also contains the next exact direct
edge above the first update path:

```text
0x00715602  FUN_007155e9 -> FUN_00715380
```

That edge is direct-call evidence only.  It should be included in the next
ownership/lifecycle slice, but it is not by itself a class identity, scheduler
identity or input/control owner.

The two branches of Process 1 therefore remain deliberately independent until
static pointer provenance closes them:

```text
FUN_007155e9 -> FUN_00715380 -> FUN_00713050 -> FUN_00794a30 -> FUN_00770e80

UNKNOWN/INDIRECT OWNER -?-> FUN_0079b2d0 -----------------------> FUN_00770e80
```

## Fail-closed behavior

The analyzer rejects:

- missing required Ghidra datasets;
- target addresses absent from `functions.jsonl`;
- unsupported pointer sizes;
- `vtables.json` format/status drift;
- malformed raw static-data hex.

Its output explicitly fixes the following policies to `false`:

```text
raw pointer occurrence is dispatch proof
vtable membership is class identity proof
vtable xref is constructor proof
missing direct call is root proof
ownership or virtual dispatch promoted
```

Evidence states remain within the Process 1 vocabulary:

```text
proven
verified
inferred
ambiguous
unknown
```

For this discovery layer, vtable/static-pointer hits remain `ambiguous`; absence
of those hits remains `unknown`.  Promotion belongs in a later exact
instruction/reference dataflow contract, not in this inventory pass.
