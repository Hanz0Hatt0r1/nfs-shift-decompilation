# Phase 748 scope

In scope:

- freeze PC retail `FUN_00712940`, `FUN_00713630` and `FUN_007144a0` machine spans;
- reproduce the exact three-record source geometry at participant `+0x2b10`, count 3, stride `0x0c`;
- reproduce `FUN_00712940` source-visible f32 arithmetic and two accumulators;
- prove the CRT wrappers used by `FUN_00713630` execute x87 `FSIN` and `FCOS`;
- reproduce the participant `+0x16b4/+0x16b8/+0x16bc` writer and `+0x2128/+0x212c` aggregate stores;
- expose `%3` manager cadence from `FUN_007144a0`;
- reuse Phase747's typed `Fun00766510ParticipantReferenceSource3f` consumer boundary.

Out of scope:

- assigning runtime values or physical meaning to `DAT_00c12ee0..DAT_00c12f04`;
- replacing the dynamic `+0x2b10` history with selected-session constants;
- fully scheduling `FUN_00727870` sample-history updates;
- proving the owner/value of participant `+0x4b0`;
- scheduling `FUN_00713630` in `NativeVehicleProviderSession`;
- claiming complete `FUN_00766510` internalization or reducing the provider count below seven.
