# Phase 243 — DDS fixture count correction

The synthetic DDS fixtures now encode the 31 DWORDs of the standard 124-byte DDS_HEADER exactly. The previous fixtures had one extra zero before `caps`, producing 32 DWORDs and failing `struct.pack`.

No production DDS decoder or Vulkan behavior changes.
