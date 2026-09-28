# Phase 493 — selector reset storage footprints

## Goal

Phase 493 maps each provider scalar selector to the exact storage touched by its reset case.

For every selector `N`, the contract exposes:

- direct zero addresses;
- addresses covered by reset bulk clears;
- combined reset-zero addresses;
- the unit-diagonal seed address;
- the complete touched-address set.

## Runtime expansion

Phase 492 reconstructs active runtime scalar groups. Phase 493 expands those selectors through the provider-specific reset-case map and produces a per-frame list of the storage addresses that the provider reset logic is expected to touch for the observed selectors.

Provider filtering is exact: events with another `provider_id` are excluded rather than mixed into the selected provider's footprint.

## Why this matters

This is the first bridge from runtime scalar indexing to provider storage topology:

`runtime selector → reset case → exact packed-storage addresses`

It can later be compared with a per-scalar post-reset capture without assigning matrix semantics to the touched cells.

## Scope boundary

The footprint is storage-level evidence. It does not claim that a touched address is a matrix coefficient, RHS element, constraint parameter, or physical quantity.