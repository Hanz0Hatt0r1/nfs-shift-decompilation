# SHIFT paired class lifetime evidence

`tools/shift_live_dump/build_class_lifetime_pair_evidence.py` joins the strong
create-side and release-side source shapes already recovered for the same class
descriptor.

The output format is `SHIFT-CLASS-LIFETIME-PAIR-EVIDENCE/1`.

## Pairing rule

A class is marked `paired_lifetime_shape=true` only when both exist:

- at least one `create_wrapper_shape=true` row from
  `SHIFT-CLASS-CREATE-WRAPPER-EVIDENCE/1`; and
- at least one `deleting_wrapper_shape=true` row from
  `SHIFT-CLASS-DELETING-WRAPPER-EVIDENCE/1`.

The join key is the recovered RTTI class descriptor, not a class-name string.
Class names remain descriptive metadata.

`ghidra_paired_lifetime_shape=true` additionally requires at least one create
shape with both factory edges independently confirmed by Ghidra and at least one
delete shape with both teardown/release edges independently confirmed.

## Preserved context

Each class row keeps:

- factory functions and initializer candidates;
- immediate preinitializer helpers;
- raw integer-literal argument sets from those helpers;
- an unambiguous preinitializer helper only when every strong create row agrees;
- deleting-wrapper functions;
- teardown-transition functions;
- release helpers and an unambiguous release helper when unique;
- nearest recovered ancestor with a unique vtable;
- concrete and ancestor vtable addresses;
- underlying strong create/delete evidence rows;
- explicit blockers for classes which currently have evidence on only one side.

This makes asymmetric recovery visible instead of dropping classes merely
because only their create or release side has been reconstructed so far.

## Source identity

The builder rejects mismatched source paths and conflicting source SHA-256
values. When the referenced source file still exists locally it recomputes its
SHA-256 and checks it against the available lifecycle artifacts before joining.

Older create-side reports may not carry their own SHA-256; in that case the
current source path and the hashed lifecycle/delete artifacts provide the
cross-check. No missing hash is fabricated.

## Evidence boundary

A paired lifetime shape does **not** establish:

- allocator semantics of the preinitializer helper;
- that a helper literal argument is object size;
- C++ constructor identity of the initializer;
- C++ destructor or deleting-destructor identity;
- ownership or reference-count policy;
- allocation arena, placement-new semantics, or scalar/array delete ABI.

It says something narrower: the same recovered class has a strong source path
feeding a helper result into its initializer and a strong source path from its
teardown transition into a guarded release wrapper. This is a high-value target
for the next ABI/lifetime analysis, not a semantic rename.

## Run

```bash
python3 tools/shift_live_dump/build_class_lifetime_pair_evidence.py \
  --create out/class_evidence/create_wrapper_evidence.json \
  --deleting out/class_evidence/deleting_wrapper_evidence.json \
  --lifecycle out/class_evidence/class_lifecycle_source_evidence.json \
  --json-out out/class_evidence/class_lifetime_pair_evidence.json
```
