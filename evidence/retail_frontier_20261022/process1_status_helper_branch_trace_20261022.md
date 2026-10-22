# Process 1 — original-PE status helper branch trace

## Run identity and limits

This bounded replay ran Need for Speed SHIFT PC retail 1.02 `SHIFT.exe`,
PE32 x86, ImageBase `0x00400000`, SHA-256
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1` in the
Linux P-code guest runtime. Runtime SHA-256:
`135c2452d882da91a249fb01acd9e5a3deedab42bde826097e43d9eb6aaff54e`.
Guest data was `pcode-game-data-v661`; verified supplement manifest
`function-call-stack-v659-missing-005a0ef0/module-manifest-v659-005a0ef0.json`,
SHA-256 `6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`.

The run completed 120 host frames, exit code 0, with zero Vulkan validation
errors. The selected caller trace for `0x00653480` recorded three events and
was not truncated. The run had 813,786 P-code dispatches across 3,934
functions; those counts are diagnostic only. It recorded
`guest_draw_translation=false` and `retail_rendering_proven=false`, so this
does not prove a visible menu, retail draw, native Windows/Wine game launch or
race.

External log:
`/home/pes/nfs-shift-recompilation-artifacts/retail-run-20261021/p1-status-helper-branch-trace-20261022/shift-p1-status-branch-v1.log`
(SHA-256 `aeadc76dc8a350571693eb3f117a0ff478feb5c02dc42f7c23d8794109779659`).
Frontier summary JSON:
`/home/pes/nfs-shift-recompilation-artifacts/retail-run-20261021/p1-status-helper-branch-trace-20261022/shift-p1-status-branch-v1.json`
(SHA-256 `6217bf18fe1828cecc00686025626f8be3d64d925c37fbe400618bdc1a1e71a7`).

## Observed call boundary and branch

At dispatch `462101`, `0x00653480` called `0x00635E40`, returning to
`0x006534A7`. The saved caller ECX was `V=0x27EA0444`; the helper received
`ECX=V+8=0x27EA044C`, `EDX=0`, and returned EAX `0`. The sampled
`DWORD[V+0xCC]` at this call was zero. Therefore, for this invocation, the
first `BYTE[V+0xCC]&2` guard was clear and the helper returned `AL=0`.

The same caller then executed both tail calls that occur only after the
helper's zero return:

| Dispatch | Target | Return EIP | ECX | EDX | EAX returned | Sampled `DWORD[V+0xCC]` |
|---:|---:|---:|---:|---:|---:|---:|
| 462102 | `0x0065F490` | `0x00653539` | 0 | 0 | `0x27F7C1A0` | `0x00010000` |
| 462104 | `0x0066BAB0` | `0x00653545` | `0x27F7C1A0` | 3 | 1 | `0x00010000` |

The value at `V+0xCC` changed from zero at the helper call to `0x00010000` by
the tail calls, matching the direct flag write in `0x00653480`'s main path.
Together, the observed `0x00635E40` AL=0 and subsequent main-only calls
localize this invocation to the main initialization branch. Its final EAX=0
is forced by the original function after `0x0066BAB0`, regardless of that
callee's observed EAX=1. This aligns with, and explains the branch for, the
separate bounded status-chain observation that `0x00653480` returned zero.

The sampled base V is only the receiver used by `0x00653480`; no supplied
evidence equates it with owner O or callback item I. The trace proves nothing
about a write to owner readiness `BYTE[O+0x2D]`, why the readiness gate stays
closed, or whether this helper path is its cause.
