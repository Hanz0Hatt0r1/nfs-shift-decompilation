# Phase 401 — HINGE/BAR matrix coupling

`FUN_007bb250` also fills the mixed HINGE/BAR scalar block after its HINGE/HINGE pass.

The outer HINGE's angular row `+0x48/+0x50/+0x58` and linear row `+0x60/+0x68/+0x70` are transformed through `FUN_007aefb0(body +0xb0, ...)`. A BAR supplies point `+0x18/+0x20/+0x28` and direction `+0x40/+0x48/+0x50`.

Two scalar coefficients are built. Equal side flags add them; differing flags subtract them. When the BAR scalar base is below the HINGE base, the block is stored as a 2×1 column under the HINGE rows. Otherwise the same values are stored as a 1×2 row under the BAR row.

The row-pointer table is `+0x158`, HINGE stride is `0xA0`, BAR stride is `0x60`, HINGE base is `+0x94` and BAR base is `+0x30`.

This closes the mixed coupling inside `FUN_007bb250`; the remaining physics work is now downstream body-state integration and final solver verification.
