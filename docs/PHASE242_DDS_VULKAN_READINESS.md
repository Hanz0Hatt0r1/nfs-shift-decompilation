# Phase 242 — DDS/Vulkan readiness reconciliation

Phase 242 closes the last CI contract mismatch in the BMW material → DDS → Vulkan adapter.

The final adapter report now recomputes `ready` from its final blocking-reason set after merging the DDS bridge. A successful resource bridge cannot leave a stale false readiness bit, and a newly introduced blocker cannot leave a stale true bit.

The synthetic DXT1 DDS fixtures now use the DDS_HEADER caps/caps2 offsets defined by the 124-byte header: `caps` at byte 104 and `caps2` at byte 108. The production decoder/resource path is unchanged.
