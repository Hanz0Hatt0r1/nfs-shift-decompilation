# Phase 404 — real BMW M3 physics intake evidence

The supplied `BMW_M3_E36.bff` was decoded locally with the project's source-backed native XMem/LZX backend. The archive contains the shared suspension resource `vehicles/physics/suspension/aarm_multilink.sdf` at index 1091, stored as Type-2 XMem/LZX data: 1110 compressed bytes expanding to 5056 bytes.

The decoded resource SHA-256 is `fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed`; the archive SHA-256 is `c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70`.

The resource defines 11 bodies, 4 `JOINT&HINGE` records and 20 BAR records. With the already reconstructed solver widths JOINT=3, HINGE=2 and BAR=1, this yields a real 40-scalar SDF solver domain for this suspension asset.

The four wheel/spindle joint axes are `(-1,0,0)`, `(1,0,0)`, `(-1,0,0)`, `(1,0,0)`. This is structural archive evidence only; it does not assign unsupported physical units or claim that the generic multilink resource itself is unique to the BMW M3.

No raw game resource is committed to the repository in this phase; only measured hashes and derived structural evidence are stored.
