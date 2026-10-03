# SHIFT memory source semantic summary

`tools/shift_live_dump/summarize_memory_source_semantics.py` consolidates the
source-level semantic roles that have already been proven by the memory-wrapper
evidence chain.

The output format is:

```text
SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1
```

It consumes:

- `SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1`;
- `SHIFT-MEMORY-ALLOCATION-SIZE-ROLE-JOIN/1`;
- `SHIFT-MEMORY-RELEASED-POINTER-ROLE-JOIN/1`.

## Promotion rules

A role is not inferred from argument position.

`allocation-size` appears in the summary only when the allocation diagnostic
slice has already proven the physical backend storage supplying `%d`, and the
source-to-backend join maps that storage to a parsed source argument.

`released-pointer` appears only when the pool-free `%p` path has already been
traced through the release backend/thunk to one wrapper entry storage and the
source positional join maps that storage to one source argument.

For each wrapper the summary aggregates all proven callsites and checks whether
the source argument index is consistent. If two independently proven callsites
assign the same role to different source indices, that wrapper gets an explicit
conflict blocker and the role is not listed in `proven_source_roles` for the
wrapper profile.

## Release byte boundary

The retail static summary also carries behavior-only evidence for entry `DL`.
The source semantic summary preserves these observations:

- whether the byte reaches the release backend;
- whether the backend observes it;
- whether it controls a conditional branch;
- whether it participates in a bitwise transform.

These observations do **not** prove that the byte is a release flag, delete kind,
destructor selector, or ownership marker. Consequently the summary keeps:

```text
release_flag_role_proven = false
delete_kind_role_proven = false
ownership_semantics_proven = false
```

regardless of a stable callsite position or recognizable bit-test shape.

## Full pipeline

`tools/ghidra/run_memory_wrapper_full_evidence.sh` now emits both the static and
source semantic summaries in addition to the lower-level artifacts:

```text
memory_retail_static_summary.json
memory_source_semantic_summary.json
```

This keeps the one-command workflow layered:

```text
raw instructions / callgraph / strings
  -> wrapper forwarding + diagnostic slices
  -> physical allocation/free roles
  -> source argument role joins
  -> static summary
  -> source semantic summary
```

The lower-level artifacts remain the primary evidence and are not replaced by
the summary files.
