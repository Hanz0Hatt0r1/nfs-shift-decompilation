# Process 1B — HDVehicle+0x4330 WinMM callback surface

## Scope

This contract bounds WinMM callback registration through `waveOutOpen`, `waveInOpen`, and `timeSetEvent` for the canonical Process 1B exact `HDVehicle+0x4330` carrier set.

## Machine-call inventory

The pinned SQLite index contains exactly six physical callsites:

- `waveOutOpen`: 3
- `waveInOpen`: 2
- `timeSetEvent`: 1

The matching Ghidra source renders one FMOD `waveInOpen` path twice because of overlapping stack recovery; the SQLite call inventory is the physical-callsite authority and pins the single machine site at `0x00999714`.

## Callback arguments

- all three `waveOutOpen` callsites pass `dwCallback = 0`;
- the simple `waveInOpen` callsite passes `dwCallback = 0`;
- the FMOD `waveInOpen` callsite at `0x00999714` passes `dwCallback = 0x0099955b` with function-callback flags;
- `timeSetEvent @ 0x009a8e7d` passes `fptc_009a8d8f`, address `0x009a8d8f`.

The two non-null callback entrypoints are disjoint from the canonical 15-function P1B exact `HDVehicle+0x4330` carrier set.

Therefore:

- `winmm_callback_surface_complete = true`
- `exact_4330_carrier_reachable_via_winmm = false`

## Limits

This is not a global runtime-callback closure. Other callback APIs, application-owned wrappers, CRT callback registration, generic function-pointer stores/copies and computed entry remain open.

Global gates therefore stay fail-closed:

- `runtime_callback_registration_ruled_out = false`
- `indirect_entry_into_carriers_ruled_out = false`
- `global_runtime_derived_4330_alias_surface_complete = false`
- `manager_374_join_to_hdvehicle_4330_complete = false`
- `last_literal_0x004b86cf_rejected = false`
- `p1_3_control_producer_complete = false`
- external provider count = **7**.
