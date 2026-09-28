# Phase 443 — specialized-provider operator signatures

## Goal

Phase 443 classifies the visible arithmetic shape of specialized-provider solver assignments. It is the first layer above the Phase 442 address dependency graph that describes *what kind of update* an assignment performs, while still avoiding reconstruction of proprietary RHS expressions.

## Operator classes

The classifier emits only structural signatures:

- `subtract-product` — subtraction containing a multiplication term;
- `subtract-product-then-scale` — subtraction/multiplication followed by the pivot-local scale variable;
- `scale-or-product-by-pivot` — multiplication ending in the pivot-local scale variable;
- `product` — multiplication without the pivot-local scale pattern;
- `subtraction` — subtraction without multiplication;
- `division` / `other` — remaining visible forms.

The reciprocal pivot itself remains represented by the Phase 436/437 pivot fingerprint rather than as an assignment operator.

## Retail audit

A local audit of the supplied retail decompilation source produces 620 assignment sites for provider 0 and 465 for provider 1 under this lexical classifier.

Provider 0 counts: 316 `subtract-product-then-scale`, 236 `subtract-product`, 66 `scale-or-product-by-pivot`, and 2 `product`.

Provider 1 counts: 145 `subtract-product-then-scale`, 218 `subtract-product`, 100 `scale-or-product-by-pivot`, and 2 `product`.

These are classifier counts, not a claim that every site represents the same mathematical operation.

## Cross-phase role

The operator signatures can be joined to Phase 442 destinations and RHS dependency references. That gives a reconstruction pipeline of:

`pivot -> destination cell -> RHS dependency cells -> operator shape`

This is enough to begin generating a neutral fixed-layout solver model without embedding the proprietary retail expression text.

## Scope boundary

The classifier does not parse a complete AST, recover compiler temporaries, attach semantic matrix names, or infer physical units. It records only decompiler-visible operator structure and assignment order.

Run locally with:

    python specialized_provider_operator_signature_runtime.py SHIFT.exe.c

The repository does not contain the proprietary `SHIFT.exe.c` file.
