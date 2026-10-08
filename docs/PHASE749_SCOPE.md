# Phase 749 scope

In scope:

- consume `SHIFT.Fun00766510LaterResponseBranchOwnership/1` in Process 2;
- model `FUN_00756b10` persistent refresh for `+0x3a00/+0x3ac8`;
- keep `+0x3770/+0x3788` mutable instead of freezing setup values;
- model proven baseline restoration from `+0x3cb8/+0x3cc0`;
- preserve six-entry `+0x3a40` table geometry;
- rewrite runtime `+0x3ac0` from `FUN_00755340(+0x3a08) * +0x3a00` on each materialization;
- inject persistent `+0x3ac8` into the sixth table entry;
- keep the setup table snapshot unchanged.

Out of scope:

- inventing `FUN_00758000` coefficient mutation semantics;
- full later-branch relative-vector/table evaluation and BODY application;
- final `+0x40a0/+0x40a8/+0x40b0` accumulator ownership;
- optional diagnostic-tail ownership;
- remaining `FUN_00713630` upstream input provenance;
- removing `NativeVehicleExternalProviderBundle.contact_response`;
- reducing the active external-provider count below seven.
