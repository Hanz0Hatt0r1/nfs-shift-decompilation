# Phase 537 — compiled shader permutation identity deduplication

Phase 537 makes material-linker ambiguity operate on compiled shader identity
rather than cache-file location when byte evidence is available.

## Problem

The retail shader cache can store the same compiled VS/PS pair in more than one
FXO file. Those rows can tie on every material-ranking field while differing
only in file name/program offset.

Treating each cache location as a different shader permutation overstates
ambiguity.

## Identity rule

For top-ranked tied candidates, the linker now compares in this order:

1. `SHIFT.ShaderPermutationIdentity/1.identity_sha256`;
2. pair byte SHA-256;
3. file/program location only when byte identity is unavailable.

Candidates with the same proven compiled identity collapse to one logical
representative.

A tie between distinct permutation identities remains ambiguous.

Synthetic candidates without byte/pair identity also remain ambiguous; stable
file/program location is deliberately retained as the fail-closed fallback.

## Retail impact

This does not select any BMW retail permutation by itself. The real BMW corpus
still contains multiple distinct top-ranked compiled identities. It only makes
the reported ambiguity count equal to the number of distinct compiled
permutations rather than the number of redundant cache locations.

The next evidence layer can therefore compare runtime material witnesses
against a clean set of distinct permutation identities.
