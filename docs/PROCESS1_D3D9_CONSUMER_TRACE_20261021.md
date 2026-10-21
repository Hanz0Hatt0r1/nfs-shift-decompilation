# Process 1 — retail display consumer trace (2026-10-21)

## Run

The bounded v692 run used the original retail PC `SHIFT.exe` PE32 image
(SHA-256
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`)
inside the recompiled guest P-code runtime. The runtime binary SHA-256 was
`d46ea64435ed73d9e799d37e7ce219238d780bde7b251d6f2e9666962bd88cb8`.
This was not a native Windows launch of `SHIFT.exe`.

The run completed 360 requested host frames, 1,738,845 P-code dispatches and
4,729 unique functions, with three workers waiting, no validation errors and
no current blocker. It recorded 1,112 D3D9 clear requests and 1,111 present
requests, but only host-side bridge submissions. `guest_draw_translation` and
`retail_rendering_proven` remained false.

The bounded live trace watched `0x00831380`, `0x005e1d50`, `0x00835590` and
four D3D9 Draw* imports. Its raw log is local-only; SHA-256
`a2bdcdd676ed083ee76697ba34e4bb287b282d73201ec705b44503937f7ee51d`,
4,069,724 bytes. The compact call counts and run summary are in
[`ui-event-path-v692.json`](../evidence/retail_frontier_20261021/ui-event-path-v692.json).
No selected Draw* import call was present.

## Observed consumer path

The exact retail PE bytes at `0x00835590` show this sequence:

```text
008355b5 call 00831380
008355ba mov esi,[ebp-8]
008355bd lea ecx,[esi+4]
008355c0 call 005e1d50
008355c5 cmp eax,1
008355c8 jne 008355e7
008355d0 call 008352f0
```

The getter at `0x005e1d50` is `mov eax,[ecx]; ret`. In the v692 trace,
`0x00831380` returned 660 times to `0x00835590`; the output dword read after
return was `0x3f800000` each time. The following getter ran 660 times with
`ECX=0x3f800004` and returned `EAX=0` each time. Given the exact `cmp` and
`jne` bytes, the zero result takes the branch to `0x008355e7`, skipping the
later `0x008352f0` call in each recorded iteration. This is a local control-flow
result, not a complete explanation of why the path has no observed Draw* call.

The runtime reserves a flat four-gigabyte PE32 guest address range, and the
trace's `target+0` read is diagnostic. It does not model Win32 page commitment
for that address. Thus the zero result does not establish whether the original
Windows process would read a valid zero or fault at `0x3f800004`. The payload
`0x3f800000` is also not enough to assign a pointer or float type. The next
step is producer/type provenance and, if available, a page-validity-aware
comparison against the original process; do not rewrite the branch or substitute
a value from this evidence alone.

## v703–v707 indirect field and function-count checks

The earlier trace could not resolve a field computed as
`data_base + table[index]`, so Process 1 added an opt-in, read-only call trace
for that formula and its last writer. A focused fixture covers caller-entry and
target-entry registers, the computed address/value, and writer provenance.
The trace does not alter guest memory, return values, or scheduling policy.

The retail PE's `FUN_007e3e20` reaches setter methods at vtable slots `+0x70`,
`+0x98`, and `+0x60`, implemented at `0x0082b840`, `0x0082b150`, and
`0x0082be30` respectively. Ghidra shows `0x0082b840` copies four dwords for
type 7 and converts four inputs into two dwords for type `0xb`; `0x0082b150`
writes one byte; and `0x0082be30` stores an object-like dword. These are
retail setter semantics, not inferred P-code behavior.

In v704, 1,278 calls to `0x0082b150` and 639 calls to `0x0082be30` sampled the
same computed field address, `0x27f86a00`, because the sampled table entries
for indices 0, 13, and 14 were zero. The trace records `0x0082b840` as the
last full-width writer of `0x3f800000`; subsequent one-byte writes from
`0x0082b150` expose values `0x3f800001` and `0x3f800000`. This is a real
low-byte mutation. The apparent overlap between a four-byte value, one-byte
flags, and the object setter at the same address could be an intentional
storage overlay or a type/offset problem; current evidence does not establish
a P-code defect.

Follow-up v708 captured the missing context: both `0x0082b840` calls come from
`FUN_007e3e20`, at return sites `0x007e3e9f` (index 11) and `0x007e4527`
(index 10). For all 1,374 traced calls, the nested container helpers returned
length 15 and type 7, and the setter returned `0x27f86a01` (success). This
confirms the four-dword-copy branch from retail code is used at both callsites.

The v709 trace sampled the indirect field for those calls. Both table entries
were zero: `0x27f869cc` for index 11 and `0x27f869c8` for index 10. Thus both
four-dword writes compute the same destination, `0x27f86a00`; values at that
address vary across calls. This establishes the alias at runtime, but not
whether the zero entries are intended object-layout overlays or were produced
by an earlier P-code/object-initialization defect. Do not change setter
semantics on this evidence alone; table initialization and producer provenance
remain the next checks.

The function-count decrease from v703 to v704 is run-to-run variation, not a
lost function implementation. v703 and v704 both completed 360 host frames
with zero validation errors. A repeated run, v707, used the same integrated
runtime binary and trace settings as v704 and returned to 4,729 unique
functions (v704 had 4,728). Dispatch totals, D3D9 clear/present requests, and
the active function at the final scheduler snapshot also varied. The count is
the number of unique functions touched in that run; the runs do not provide
the address sets needed to identify which one was absent from v704. The
frontier comparator now marks lower counters for review instead of treating
them alone as a regression.

These bounded recompiled-P-code runs used the existing DXT3 packet-capture
adapter capability from Process 2 PR #2143 so they could pass the managed DXT3
check. They are not native Windows executions. All three report
`guest_draw_translation=false` and `retail_rendering_proven=false`; they do
not demonstrate a retail draw, frontend, race, or rendered frame. Compact run
metrics and hashes are in
[`process1_pcode_frontier_v703_v709_indirect_field_summary.json`](../evidence/retail_frontier_20261021/process1_pcode_frontier_v703_v709_indirect_field_summary.json).

## D3DX parameter descriptor ABI correction (v719)

The v715–v718 traces narrowed the zero values at record offset `+0x10` to the
`GetParameterDesc` output assembled by the P1 D3DX proxy. The retail constructor
at `0x0083d850` copies `D3DXPARAMETER_DESC.Bytes` into each `0x50`-byte record.
The [documented PE32 structure](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dxparameter-desc)
places `Flags` at byte offset `0x24` and `Bytes` at byte offset `0x28`. The
proxy had written these final two fields in reverse order, so retail code read
the parameter flags as the size. This explained the
zero values seen in v718; it was an ABI mismatch in the guest compatibility
layer, not a defect in `0x0083a640` or the effect binary parser.

The proxy now writes `Flags` before `Bytes`. Its focused fixture uses a
four-byte parameter with a nonzero `0x40` flags sentinel and checks that the
guest descriptor returns `0x40` at `+0x24` and `4` at `+0x28`; annotation
descriptors check `Flags=0` and `Bytes=4` as well.

The rebuilt P1 runtime passed the focused module check and the 23 retail-frontier
tool tests. A bounded v719 replay with the retail PE (SHA-256
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`) returned
`0x10` from `0x0083a640` for both indices 10 and 11. The corresponding fields
were `0x241d8d24` and `0x241d8d74`, both written by retail `0x0083d850`.
This confirms that the corrected descriptor size reaches the retail record
builder. The replay then stopped at `unsupported D3D9 managed texture
description` after 1,305,017 dispatches; it did not complete the requested host
frames, and `retail_rendering_proven` remained false. At that point the replay
report did not record whether the optional D3D9 packet-capture adapter was
installed, so the exact cause of the texture stop was not yet established.

### Managed DXT3 capture boundary (v722-v723)

A v722 replay enabled `SHIFT_D3D9_PACKET_CAPTURE_DIR` and used the cumulative
v659 P-code manifest. The diagnostic record for the failing retail request was
`1024x512`, one level, usage 0, FOURCC `0x33545844` (DXT3), managed pool 1.
The active P1 branch reported adapter capabilities `DXT3=0, DXT5=1`; it then
stopped at the same managed-texture validation after 1,303,399 dispatches.
This identifies the missing DXT3 capability at the P1/P2 capture boundary; it
does not require changing the retail request or its semantics.

For v723, a temporary integration build added only Process 2 commit
`1fef18a8` from PR #2143 to the P1 v719 source, then rebuilt the runtime. The
same retail request reported `DXT3=1, DXT5=1`; the probe completed 360 host
frames with 1,735,292 P-code dispatches, 4,726 unique functions, five waiting
workers, and zero Vulkan validation errors. The scheduler snapshot was at
`0x00633a50`; the bridge submitted 360 clears and 360 presents. The probe still
reported `guest_draw_translation=false` and `retail_rendering_proven=false`,
and produced no D3D9 packet capture because no guest draw was reached. This is
evidence that the DXT3 stop is crossed when the adapter capability is present,
not evidence of a retail menu, race, or rendered frame. The temporary
integration was not pushed into either PR.

PR #2143 remains the owner of the adapter capability change; the current P1
branch does not contain commit `1fef18a8`. The compact logs, exact descriptor,
source revisions, and limitations are recorded in
[`process1_d3dx_dxt3_capture_integration_v723.json`](../evidence/retail_frontier_20261021/process1_d3dx_dxt3_capture_integration_v723.json).

Full compact evidence, focused test commands, and artifact hashes are in
[`process1_d3dx_parameter_desc_abi_v719.json`](../evidence/retail_frontier_20261021/process1_d3dx_parameter_desc_abi_v719.json).

## Audio hypothesis

This v692 trace specifically targeted D3D9 Draw* imports; it is not an audio
trace. The separate bounded v667 probe watched selected WinMM/MSACM and module
lookup APIs and did not observe them through 360 host frames. That makes a
missing selected audio import an unlikely explanation for the v667 horizon,
but does not rule out audio APIs or callbacks on later frontend/gameplay paths.
See [`PROCESS1_AUDIO_IMPORT_PROBE_20261021.md`](PROCESS1_AUDIO_IMPORT_PROBE_20261021.md)
for that probe's limits and the unresolved v520 causality question.

## Limits

- This is recompiled P-code execution over the retail PE, not evidence that the
  original retail executable reached the frontend or race.
- Host-frame, dispatch and function counts are diagnostics, not game-launch or
  gameplay proof.
- The local getter result narrows the consumer frontier but does not demonstrate
  that the selected branch should have continued, nor a causal edge to D3D9
  drawing.
- No guest value, API result, branch or ordering was changed.
