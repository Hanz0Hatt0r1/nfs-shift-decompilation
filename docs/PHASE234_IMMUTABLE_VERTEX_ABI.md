# Phase 234 — immutable vertex ABI status

Phase 234 makes the VertexLayout ABI-status lookup table immutable. The mapping is process-wide contract data, not mutable runtime state; it now uses MappingProxyType.

This prevents test or application-side mutation from changing established COLOR confidence values later in the same Python process.

No MEB property mapping or ABI selection is changed by this phase.
