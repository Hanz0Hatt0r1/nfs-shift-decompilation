# Phase 240 — BMW DDS/Vulkan adapter hardening

Phase 240 fixes two concrete integration issues found by the full CI suite.

First, DDS extraction blockers are now propagated into the final adapter result even when no temporary DDS packet can be created. This preserves fail-closed behavior for source SHA mismatches and missing/ambiguous BFF provenance.

Second, the adapter rewrites DDS bridge provenance after temporary extraction so persistent `dds_sources.json` and the returned report never retain the ephemeral extraction directory. Material sampler identity is represented by the stable RenderCommand reference; the exact BFF archive/path/SHA remains in `material_slice_source.json`.

The existing Linux Vulkan runtime path is unchanged.
