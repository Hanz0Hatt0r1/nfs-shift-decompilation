# Phase 608 — draw-range-aware runtime pipeline candidate join

## Production motivation

Phase 607 raises runtime/static candidate coverage to 9 of 10 target pipeline
signatures and 1,442 of 1,581 target draws, but every surviving pipeline is
still ambiguous.

The runtime D3D9 catalogue already observes exact DrawIndexedPrimitive ranges,
while every Silverstone static binding carries a source-backed primitive draw
range. Phase 608 uses that existing evidence as another candidate-only gate.

## Complete runtime draw ranges

The target draw signature catalogue now preserves every distinct observed tuple:

- primitive type;
- base vertex index;
- start index;
- primitive count;
- draw count.

The existing top-eight diagnostic list remains for compact inspection.

## Candidate gate

After the Phase 606/607 shader/layout gate, a static candidate survives the
draw-range gate only when its source:

- first_index equals an observed D3D9 start_index; and
- primitive_count equals the same observed D3D9 primitive_count.

This gate does not use resource pointer identity and does not claim the runtime
draw belongs to that static IMB instance.

## Backward compatibility

Older target-draw catalogues do not contain the complete observed range list.

For those reports, Phase 608 only derives a complete set from top_draw_ranges
when:

`len(top_draw_ranges) == distinct_draw_range_count`.

If the legacy list is truncated, the draw-range gate is not applied. This
prevents false-negative candidate elimination.

## Reporting

The join now records:

- pre-draw-range candidate binding count;
- runtime draw-range source;
- runtime draw-range tuples used;
- draw-range gate status;
- final candidate binding count;
- aggregate counts for applied, reduced and rejected gates.

## Boundary

Draw-range agreement is candidate narrowing only.

Even a single surviving binding still does not prove:

- exact runtime IMB resource identity;
- same-instance identity;
- render admission.

Promotion remains behind the existing Phase 572 exact runtime resource +
primitive + strong shader evidence gates.
