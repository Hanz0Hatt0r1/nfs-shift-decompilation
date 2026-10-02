# Phase 604 — normalized target resource shapes

## Motivation

The first production Phase 603 report contains 1,581 Silverstone target draws
and only 10 pipeline signatures, but 1,094 resource-shape signatures.

Inspection shows that the dynamic instance stream changes
`offset_in_bytes` frequently while its buffer descriptor and stride remain
stable. Treating that allocator position as part of the shape identity
over-fragments otherwise recurring draw paths.

## Change

`SHIFT.D3D9TargetDrawSignatureCatalog/1` now excludes stream offsets from the
stable resource-shape hash.

The offsets are not discarded. Each normalized resource-shape row records, per
stream:

- unique observed offset count;
- minimum and maximum byte offset;
- the most frequent offsets and their draw counts.

The catalogue also emits layout cohorts keyed only by:

- vertex-declaration payload SHA-256;
- stream number/stride layout;
- index-buffer format.

Each cohort retains the contributing pipeline signatures, VS hashes, target PS
hashes, families and aggregate draw count.

## Evidence boundary

Normalization is clustering only. Removing an allocator offset from a
descriptor-shape identifier does not prove that two runtime buffers are the
same resource, mesh or scene instance.

Exact resource identity still requires the existing path + SHA evidence gate.
Primitive and same-instance attribution remain unchanged.
