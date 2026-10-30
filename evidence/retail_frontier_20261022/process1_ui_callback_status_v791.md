# UI callback status trace: v791

**Date:** 2026-10-22. **Binary:** Need for Speed SHIFT PC retail 1.02, original PE32 x86, ImageBase `0x00400000`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

v791 ran the original PE in the Linux P-code guest runtime with the full v659 startup module manifest for 360 host frames. It reached the host-frame loop with exit code 0, 1,751,486 P-code dispatches across 4,733 unique functions, and zero Vulkan validation errors. The bridge submitted 360 clears and 360 presents, but reported `guest_draw_translation=false`; `retail_rendering_proven=false`.

The targeted guest-call trace selected caller `0x005092F0`, target `0x005088A0`, owner slots `+0x14/+0x2D/+0x28/+0xAC`, item slots `+0xE4/+0xE8/+0xEC`, and exact-address provenance for the nine v789 list items. It contained 27 selected events and was not truncated.

## Bounded observations

- At the readiness guard call (dispatch 461057), `DWORD[O+0x14]` was `9`; the latest exact-address provenance entry was the four-byte value `9` store by `0x004F5E60` at dispatch 461055. The guard returned EAX `0x00509200` (AL zero), after which `0x005092F0` wrote zero to `BYTE[O+0x2D]`.
- The same nine list-item callback calls seen in v789 are present in the v791 trace; each returns EAX zero through `0x00508860`. No list-count decrement was observed in the selected fields.
- `0x005088A0` returned EAX `5` for one item at dispatch 461313 from caller `0x005092F0`, then for four selected items from caller `0x00509689`: item `0x27DFBE38` at dispatch 994206, `0x27DFC178` at 1309416, `0x27DFB778` at 1319733, and `0x27DFA6B8` at 1612672.
- In the original PE, `0x005088A0` calls the item vtable slot at `+0x0C` and stores the returned EAX at item `+0xE4`. The trace records the return value; it does not itself sample a post-return read of that field.

These are observations from one selected replay. They do not prove that every list item was queried, that the returned value `5` means ready, that any other function cannot change the list, or that the zero readiness byte caused a frontend stall. No guest state was changed and no claim of a rendered menu, race, native Windows/Wine launch, or translated retail draw is made.

## Reproducibility hashes

- v791 log SHA-256: `10b0d4f5831f35aff824f4cd9a2873c9d48361d225bd0bb42eeaae4c7bdb8029`
- v791 summary JSON SHA-256: `b82c9a791d11f1e8e2d8e9e2a8fd300f98561b4e06ca32351b090c4d1e0d8639`
