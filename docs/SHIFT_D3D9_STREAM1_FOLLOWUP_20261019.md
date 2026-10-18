# SHIFT D3D9 stream-1 follow-up — 2026-10-19

## Capture

A second manual trigger was requested during the same PortProton retail race
session. The trigger fired at frame **3968** and captured frames **3966–3970**;
the proxy marked it complete at frame **3971**. This used the merged bounded
capture producer from [PR #2093](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/pull/2093).

The user reported that the visible car group had already left before this
capture could be used to examine the variety. No screenshot or car-specific
resource identity was recorded, so this window cannot establish which vehicle
models were visible.
The matched shader signature is inventoried as `crowdgeninstanced`; its draws
must not be treated as vehicle-model evidence.

## Findings

- The signature `ps:b83e3c4ec719e80f` matched **119 draws** using stream 1 from
  capture-local vertex-buffer generation `0xd4dfd70` (131,072 bytes, stride
  64). The draws used **93 distinct stream offsets**, from 6,528 to 43,712.
- The trigger flushed **1,806 captured lock-range payload events** for that
  generation: 719,488 captured bytes across 725 offsets. Every referenced
  payload file exists in the external bundle.
- The spatial union of captured byte ranges covers the computed stream-1 input
  interval for **109/119** target draws. Ten intervals remain incomplete; this
  union does not prove the exact byte values present at each draw time.
- Compared with the earlier manual window in this capture (frames 3851–3855,
  90 target draws), this sample adds **92 target draw offsets** and **282
  payload offsets** not present in that window. This establishes additional
  stream-1 data, but not additional vehicle models.
- The buffer pointer is local to this proxy capture. This generation does not
  fill the separate `0xd39e4b8` generation from the 2026-10-18 capture, and no
  original `resource_path`/`resource_sha256` identity was captured.

The machine-readable summary is
[`stream1_race_followup_f3968.json`](../evidence/retail_frontier_20261019/stream1_race_followup_f3968.json).

## Game-owned replay cache

The game's `replaycache.rep` is a separate, useful source: it starts with
`GameSetupReplaySnapshot` and contains **16** `ParticipantReplaySnapshot`
records. The model IDs are RX-7 ×5, VW Scirocco ×4, Mitsubishi Evo X ×3,
Renault Megane ×2, and Infiniti G35 ×2. It was modified at 01:14:47 local,
about 22 seconds after the capture log's last write. This supports a diverse
race participant roster, but the cache has no shared frame/draw ID that ties a
model to the target shader calls above. It is replay/setup data, not compiled
shader bytecode.

The cache was inspected read-only and copied outside the repository so its
hash can be reproduced. The compact roster and both hashes are recorded in
[`game_owned_replaycache_roster_20261019.json`](../evidence/retail_frontier_20261019/game_owned_replaycache_roster_20261019.json).
No separate game-owned compiled shader cache was found in the searched game
installation and `Documents/NFS SHIFT` profile paths.

## Artifact location

The raw capture and payloads remain outside Git under
`/home/pes/nfs-shift-recompilation-artifacts/portproton-retail-capture-20261019/stream1-partial-followup-2093/`.
The filtered stream-1 bundle is
`stream1_vb_d4dfd70_frame3968_payloads.tar.gz` (434,050 bytes, SHA-256
`c7cfc8257a31f8e8589128aa64b702c8bc9dae2b297b63333e8cc9d5e0fee8ec`). Its
manifest is
`stream1_vb_d4dfd70_frame3968_payloads.manifest.json` (815,437 bytes,
SHA-256 `9a6d422d34bb28d67ee9cb139a8b96efe542aedf64e1d962358fc5ded5eaed6c`).
The raw JSONL is 91,304,285 bytes with SHA-256
`ec8f7a3cee0447ee46dedc2d52e15c90d4e16f8cb1fd75c5f22d74099f07d8d6`.

## Remaining gap

The extra lock ranges are useful for stream-1 analysis, but the scene inventory
does not identify cars and ten target draw intervals are not fully covered.
The older capture-local generation also remains separate. Do not count this
sample as vehicle-model coverage or as a retail draw admitted to the Vulkan
backend.
