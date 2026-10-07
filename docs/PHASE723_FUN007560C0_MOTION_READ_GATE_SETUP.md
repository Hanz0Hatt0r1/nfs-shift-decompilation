# Phase 723 — FUN_007560c0 motion-read gate setup ownership

PC retail writes `HDVehicle+0xe0` in `FUN_007560c0`, called from the vehicle setup path `FUN_0076df50`, while `FUN_00769ef0` later reads the stored byte before deciding whether to call `FUN_007682c0`.

This phase moves ownership of that byte out of the per-pass `Fun007682c0ExternalMachineInput` boundary and into immutable `NativeVehicleProviderSession` setup state. The selected setup value remains explicit; this phase does not assume the default global settings values are the selected runtime values.

After this handoff, `DAT_00c128cc` is the only remaining late `FUN_007682c0` raw input field. The external provider inventory remains eight because the gate is setup state, not an additional callback/provider boundary.
