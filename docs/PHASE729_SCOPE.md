# Phase 729 scope

Phase 729 owns only the two current-BODY motion lanes consumed by `FUN_007675f0`.

In scope:

- read BODY0 `+0x78/+0x88` from the authoritative persistent BODY buffer;
- refresh those values independently for both recovered physics passes;
- remove `speed_x/speed_z` from the session-facing `ContactOuterExternalInput`;
- retain compatibility with the complete historical `ContactOuterKernelInput` while ignoring legacy external speed fields;
- keep the active external-provider count at seven.

Out of scope:

- internalizing the remaining eight `FUN_007675f0` caller inputs;
- assigning stronger physical names/units than the PC evidence supports;
- changing canonical Phase 727/728 `FUN_00765c40` / `FUN_007618f0` proofs;
- reducing the external-provider count without another complete owner/producer proof.
