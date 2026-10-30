# Process 1 — original-PE status-chain P-code trace

## Run identity and limits

The bounded run used the original Need for Speed SHIFT PC retail 1.02
`SHIFT.exe`, PE32 x86, ImageBase `0x00400000`, SHA-256
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.
The guest-data root was `pcode-game-data-v661`; the v659 supplement manifest
SHA-256 was
`7224960e4d4606ac0cc568418d7b7928ea5e56636a34683c9d0d2c15e27153c3`.
Runtime SHA-256 was
`135c2452d882da91a249fb01acd9e5a3deedab42bde826097e43d9eb6aaff54e`.

The probe requested 360 host frames with Vulkan validation and a 180-second
wall-clock limit. It ended with status `timeout`, process exit code `124`,
after 890 guest D3D9 Present requests. It did not reach a host-frame-loop
checkpoint; the report has no final dispatch count, frame count, or validation
result. No retail draw, menu, race, or rendering success is established.

The selected trace targets were `0x0065EC50`, `0x0065FA60`, and `0x00653480`.
The external log is
`/home/pes/nfs-shift-recompilation-artifacts/retail-run-20261021/p1-status-producer-trace-20261022/shift-p1-status-chain-v1.log`
(SHA-256 `b823b78df141121bc9154effc05c03fe963654307aa268234c61a4f345b7e78a`);
the frontier JSON is its `.json` companion (SHA-256
`b85db07193a923677a528bdf8775b5c044711dcddc28e262646a0b54aa6a94f5`).

## Observed call chain

At dispatch `605092`, the trace recorded caller `0x00634F50` entering
`0x0065EC50`, with ECX `0x27EEA1E0`, EDX `0x27E32E18`, stack argument `5`,
and return EIP `0x00634F6F`.

At dispatch `605095`, `0x0065EC50` called `0x0065FA60` with ECX
`0x36214720`, EDX `0x27EEA1E0`, first stack argument
`S=0x27E32E18`, and second stack argument `5`. The sampled target field
`[ECX+0x2CC]` was `2` at entry.

At dispatch `605245`, `0x0065FA60` called `0x00653480` with ECX
`0x36214784`, EDX `0`, EAX `0x00010000`, and the first three sampled stack
arguments all `0`. The fourth argument `0x005B0D50` is established by the
original caller bytes, but was outside the three selected stack slots in this
trace.

The observed returns were EAX `0` from `0x00653480`, then EAX `0` from
`0x0065FA60`, and EAX `0` from `0x0065EC50`. This dynamically confirms one
original-PE execution of that nested callee chain and the zero return flowing
through these functions. It is consistent with the static `0x0065FA60`
analysis: on the long branch, zero from `0x00653480` makes it return zero.

## Evidence boundaries

The trace selected the call into `0x0065EC50` from `0x00634F50`; it did not
select or record the outer caller of `0x00634F50`. Therefore it does not
independently establish that this exact runtime invocation was nested under
`0x00508C70` or that the runtime recorded an outer status value of `5`.
The static reports show how a zero from this path would map to status `5` if
`0x00634F50` was called by `0x00508C70`.

This is a single bounded P-code guest observation. The later timeout and
absence of final validation/frame data prevent claims of a completed launch.
It does not establish that the zero result is the UI readiness blocker or
explain owner `O+0x14` / `O+0x2D` state.
