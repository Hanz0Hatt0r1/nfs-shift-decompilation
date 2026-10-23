# Process 1 — original-PE UI vtable setup trace

## Run identity and limits

The probe ran Need for Speed SHIFT PC retail 1.02 `SHIFT.exe`, PE32 x86,
ImageBase `0x00400000`, SHA-256
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1` in the
Linux P-code guest runtime. The runtime SHA-256 was
`135c2452d882da91a249fb01acd9e5a3deedab42bde826097e43d9eb6aaff54e`. It used
`pcode-game-data-v661` and the verified v659 supplement manifest
`function-call-stack-v659-missing-005a0ef0/module-manifest-v659-005a0ef0.json`
(SHA-256
`6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`).

This bounded run completed 120 host frames with exit code 0 and zero Vulkan
validation errors. It recorded 814,129 P-code dispatches across 3,934
functions; those counts are diagnostic only. The P-code trace was limited to
calls made by `0x0054B8B0`: it recorded 42 events and was not truncated. The
bridge submitted 120 clears and presents, but `guest_draw_translation=false`;
`retail_rendering_proven=false`. No native Windows/Wine game launch, visible
menu, retail draw or race is established.

External log:
`/home/pes/nfs-shift-recompilation-artifacts/retail-run-20261021/p1-ui-initial-vtable-trace-20261022/shift-p1-ui-init-v1.log`
(SHA-256
`e960f5418695aa3330efd7d02390ec7813854dfdf3e81f50b4a674f557ce2b29`).
Frontier summary JSON:
`/home/pes/nfs-shift-recompilation-artifacts/retail-run-20261021/p1-ui-initial-vtable-trace-20261022/shift-p1-ui-init-v1.json`
(SHA-256
`d7e0f96b5dcf5248607812db427057a7df592f2d331edc27cfc5489ce5087edf`).

## Observed original indirect-call targets

At dispatch `459570`, the original `CALL EAX` at `0x0054B8DC` resolved to
`0x00509290`. Its exact call/return record was:

~~~text
caller=0x0054B8B0 target=0x00509290 return=0x0054B8DE
entry ECX=0x27DFA5FC EDX=0x00AC500C
caller ECX/S=0x27DFA5F8; O=S+4=0x27DFA5FC
return EAX=0x00000000
~~~

There were no pushed method arguments at the callsite. The sampled original
vptr slot at `S+4` held `0x00AC52C4`; `S+0x18` (the caller-relative location
`O+0x14`) was zero at this early call.

The same run later recorded the existing post-registration indirect call at
`0x0054BAC6`: it resolved to `0x005092F0` and returned to `0x0054BAC8`. Its
entry ECX was the same `O=0x27DFA5FC`; the sampled vptr was still
`0x00AC52C4`, and `DWORD[O+0x14]` was then 9. The caller body contains nine
intervening direct calls to insertion thunk `0x005092E0` before this slot
`+0x0C` call. This establishes both dynamic targets and an unchanged sampled
vptr for this one bounded invocation; it does not prove those values are
universal across objects or runs.

The complete target record for the later call was:

~~~text
caller=0x0054B8B0 target=0x005092F0 return=0x0054BAC8
entry ECX=0x27DFA5FC EDX=0x00AC52C4
caller ECX/S=0x27DFA5F8; sampled DWORD[O+0x14]=9
return EAX=0x00000000
~~~

## Bounded conclusion

The previously unknown early virtual method at `0x0054B8DC` is `0x00509290`
in this original-PE guest run. It returns zero, then the enclosing method
performs nine list insertions and later dispatches `0x005092F0` through a
different slot on the same sampled vptr. The trace does not show that the
early method changes the original vptr or sets readiness `BYTE[O+0x2D]`; the
recorded owner-relative slots are sampled values at calls, not write
provenance. Static analysis of the full `0x00509290` body is still needed to
classify its direct write-set and nested-call boundaries. The later
`0x005092F0` observation is consistent with the separate v791 count-9
readiness reset evidence, but this run alone does not prove why readiness
remains zero or that the frontend stall is caused by it.
