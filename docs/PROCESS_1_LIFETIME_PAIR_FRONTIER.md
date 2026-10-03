# Process 1 — vehicle lifetime pair frontier

`SHIFT.VehicleLifecyclePointerJoin/1` closes a narrow static correlation between
the persistent vehicle pointer graph, one exact candidate-table STORE and one
unique PE/source-backed lifecycle class row.  The repository also already has a
separate class-wide create/delete pairing artifact:

```text
SHIFT-CLASS-LIFETIME-PAIR-EVIDENCE/1
```

This block joins those two evidence families without claiming runtime ownership
or C++ constructor/destructor semantics.

Tool:

```text
tools/ghidra/build_vehicle_lifetime_pair_frontier.py
```

Output:

```text
SHIFT.VehicleLifetimePairFrontier/1
```

## Identity rule

The join uses two independent recovered identifiers:

```text
class descriptor
+
exact numeric own-vtable address
```

A class-name string is metadata only.  It is never used to select a lifetime
pair.  If the descriptor and vtable identify one row but the two reports carry
different class-name text, the candidate is retained but its identity state is
reduced to `ambiguous` and the metadata disagreement is reported explicitly.

## Inputs

```bash
python3 tools/ghidra/build_vehicle_lifetime_pair_frontier.py \
  out/vehicle_lifecycle_pointer_join.json \
  out/class_evidence/class_lifetime_pair_evidence.json \
  --json-out out/vehicle_lifetime_pair_frontier.json \
  --targets-out out/vehicle_lifetime_transfer_targets.txt
```

The first input must be:

```text
SHIFT.VehicleLifecyclePointerJoin/1
```

The second must be:

```text
SHIFT-CLASS-LIFETIME-PAIR-EVIDENCE/1
```

## Lifetime-pair strength

The existing class lifetime artifact distinguishes two levels:

- `paired_lifetime_shape=true`: source-backed create and delete shapes exist for
  the same recovered descriptor;
- `ghidra_paired_lifetime_shape=true`: the create and delete sides also have the
  required direct Ghidra edge confirmations.

This frontier maps those levels conservatively:

```text
paired source shape only        → inferred
ghidra-paired lifetime shape    → verified
no complete pair                → unknown
```

The frontier cannot become `verified` unless the upstream vehicle lifecycle
pointer join is also `verified` and descriptor + own-vtable identity is unique.

## Preserved create-side evidence

For the exact lifetime-pair row the report keeps:

- factory functions;
- initializer candidates;
- immediate preinitializer helper candidates;
- an unambiguous preinitializer helper when the source evidence already has one.

These remain structural lifetime evidence.  A helper is not renamed as an
allocator, and an initializer candidate is not renamed as a constructor.

## Preserved delete-side evidence

The report also keeps:

- deleting-wrapper functions;
- teardown-transition functions;
- release helpers;
- an unambiguous release helper when already established by the pair artifact.

A deleting-wrapper shape is not by itself a C++ deleting destructor, and a
release helper is not automatically `operator delete`.

## Verified frontier meaning

`verified_vehicle_lifetime_pair_frontier=true` means:

1. the persistent vehicle pointer/lifecycle join is verified;
2. exactly one class lifetime-pair row has the same descriptor and exact
   own-vtable address;
3. that row has `ghidra_paired_lifetime_shape=true`;
4. descriptive class-name metadata does not conflict.

It therefore establishes a concrete set of create/delete-side functions that
belong to the same recovered class descriptor/table evidence as the vehicle
pointer candidate.

It does **not** establish that the runtime object passed through those create and
delete functions is the same object instance observed on the vehicle update
path.

## Next targeted instruction frontier

For every matched lifetime pair the tool emits the union of:

```text
factory functions
initializer candidates
deleting-wrapper functions
teardown-transition functions
```

These are the next exact `SHIFT.GhidraFunctionInstructions/2` targets.

The next Process 1 stage should prove callsite value transfer separately on the
create and delete sides:

```text
create helper result / factory value
→ initializer receiver/value
→ lifecycle pointer source

lifecycle pointer source
→ teardown receiver/value
→ deleting-wrapper/release path
```

A direct call edge alone is not sufficient.  The transfer stage must inspect the
actual register/stack value flow at each exact callsite and stop on clobbers,
branches, unsupported ABI assumptions or ambiguous aliases.

## Fail-closed cases

The builder does not choose a pair when:

- the vehicle lifecycle row lacks a descriptor;
- the stored table address is missing;
- the descriptor exists but no pair has the same own-vtable;
- multiple pair rows have the same descriptor + own-vtable;
- class-name metadata conflicts;
- the upstream lifecycle join is weaker than verified;
- the lifetime pair is source-only rather than Ghidra-paired.

Source-only lifetime pairs remain visible as `inferred`, not discarded.

## Evidence boundary

Even after a verified frontier, all of the following remain false:

```text
allocation_transfer_proven
initializer_receiver_transfer_proven
teardown_receiver_transfer_proven
release_transfer_proven
same_runtime_object_across_lifetime_proven
constructor_semantics_proven
destructor_semantics_proven
owner_identity_proven
```

This stage is a target-narrowing and identity-composition contract.  It makes the
next ABI/pointer-transfer analysis finite without promoting class lifetime
semantics prematurely.
