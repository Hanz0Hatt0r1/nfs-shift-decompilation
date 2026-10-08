# Phase 747 next blocker

The shared `FUN_00766510` reference vector now has a concrete owner and native transform:

```text
HDVehicle+0x3fe8 -> actual participant -> f32 +0x16b4/+0x16b8/+0x16bc
-> f64 widening -> FUN_007af0a0(BODY0+0xd4)
-> local_d8/local_d0/local_c8
```

The remaining source-side blocker is the dynamic writer state used by `FUN_00713630` to refresh the participant X/Z lanes. Do not replace that state with a selected-session constant.

In parallel, Process1 still owns the optional `FUN_00766510` `+0x3bc8/+0x3cxx` branch and residual state/diagnostic writes. The top-level `contact_response` provider must remain until those paths and the dynamic participant source are integrated in exact retail order.
