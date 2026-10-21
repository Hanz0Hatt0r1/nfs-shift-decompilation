# Process 1 — bounded audio import probe (2026-10-21)

This probe checks whether the sound API surface is reached in the current
recompiled guest-runtime startup path. It uses the original PC retail 1.02
`SHIFT.exe` PE32 image (SHA-256
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`) with
the recompiled P-code runtime. It is not a native Windows `SHIFT.exe` launch.

The run used the P1 runtime change from `e6f674a6`, P2 DXT3 capture adapter
from `1fef18a8`, game data `pcode-game-data-v661`, and the reconstructed v659
module manifest. A 32-import trace watched the main `waveOut` / `waveIn`,
`timeSetEvent`, MCI, MSACM stream, and dynamic module/procedure lookup calls.
The selected APIs and report fields are recorded in
`evidence/retail_frontier_20261021/process1_audio_runtime_probe_v667.json`.

## Result

- Status: `host-frame-loop`, no blocker, exit code 0.
- Requested/rendered host frames: 360 / 360.
- P-code dispatches / unique functions: 1,736,499 / 4,728.
- Worker waiting count: 5; validation errors: 0.
- No selected `WINMM.dll!` or `MSACM32.dll!` call was recorded. The trace
  recorded `LoadLibraryA("kernel32.dll")` and `LoadLibraryA("nvapi.dll")`;
  it did not record an audio-module load or audio-related procedure query.
- The log contains no `unimplemented PE import` message.
- `guest_draw_translation=false` and `retail_rendering_proven=false`.

For this bounded replay, the missing WinMM/MSACM handlers are not a blocker
before the 360-frame host loop. This does not rule them out on a later path and
does not explain or disprove the separate v520 worker/predicate bit-2
observation: this run did not trace that predicate's exact reader/writer chain
or establish a causal edge from an audio result to the bit. The audio
hypothesis remains unproven for v520.

This is guest P-code execution from the retail PE, not proof that the original
Windows game reached its frontend, race, or rendered a retail frame.
