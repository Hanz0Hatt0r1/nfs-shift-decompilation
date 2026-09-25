# Phase 230 — CI reconciliation and strict COLOR pair gate

Phase 230 fixes the remaining concrete CI failures on the current mainline.

The native Vulkan texture checkpoint had a literal two-character backslash-n prefix before `struct Image`, which broke GNU C++ compilation. The source now contains a normal C++ declaration.

The D3D9 COLOR bridge requires both exact MEB descriptors:
- 460 -> [4, 6, 0]
- 461 -> [4, 6, 1]

Only when the complete pair matches the source-backed binary loader semantics and the observed Type-4 packed-color path is present can either property be promoted to D3DCOLOR. A lone 460 or 461 descriptor remains `not-proven`.

Resource provenance remains independent from ABI selection.
