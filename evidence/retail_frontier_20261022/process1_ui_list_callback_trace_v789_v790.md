# UI list callback trace: v789 and v790

**Date:** 2026-10-22. **Binary:** Need for Speed SHIFT PC retail 1.02, original PE32 x86, ImageBase `0x00400000`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

These are bounded replays of the original PE in the Linux P-code guest runtime. They are not native Windows/Wine launches. Both used the full v659 startup module manifest and ran 120 host frames. Dispatch totals are context only, not evidence of gameplay or a rendered menu.

## Run summaries

| Run | P-code dispatches | Unique functions | Vulkan validation errors | Clear / present submissions | Guest draw translation | Retail rendering proven |
|---|---:|---:|---:|---:|---|---|
| v789 | 814,243 | 3,934 | 0 | 120 / 120 | false | false |
| v790 | 815,088 | 3,934 | 0 | 120 / 120 | false | false |

Both reached the host-frame loop. The probe summaries report 591 clear requests and 590 present requests in v789, and 593 clear requests and 592 present requests in v790. They do not report a retail guest draw. The v789 trace contained 18 selected events and was not truncated; v790 contained 2 selected events and was not truncated.

## v789: nine registered item callbacks

The selected trace recorded nine calls from `0x005092F0` to `0x00508860`, each with owner `O=0x27DFA5FC` in EDX. The helper entries used these item pointers as ECX:

`0x27DFAD78`, `0x27DFBE38`, `0x27DFC178`, `0x27DFB778`, `0x27DFA6B8`, `0x27DFAA18`, `0x27DFB0D8`, `0x27DFBAD8`, `0x27DFB438`.

For each observed item at helper entry, the selected slots were `+0xE4=2`, `+0xE8=0`, and `+0xEC=0x27DF0000`. The helper then set `+0xE8` to owner `O`, called an indirect target, and returned with EAX `0`. The nine observed callback targets were `0x005AA830` six times and `0x0054B510`, `0x0054AEA0`, and `0x0054AA10` once each. The helper's recorded last writes set each item's `+0xE4` DWORD to `0` and `+0xEC` byte to `1`.

This establishes the observed bounded call sequence and writes from the selected trace. It does not establish the C++ types or lifetimes of the items, or that the callbacks completed the frontend transition.

## v790: one post-traversal item query

The selected trace recorded `0x005088A0` at dispatch 461313, called from `0x005092F0` with ECX `0x27DFAD78` and return address `0x00509370`. The nested target `0x00508C70` was entered at dispatch 461314 and returned EAX `5`; the enclosing `0x005088A0` event also reported EAX `5` on completion.

The original PE block for `0x005088A0` calls the item vtable entry at `+0x0C` and stores the returned EAX into `DWORD[item+0xE4]`. The trace therefore provides a concrete candidate for the next state transition to inspect, but this selected call alone does not prove why the outer worker's byte at `O+0x2D` remains zero or that a menu/race was reached.

## Reproducibility hashes and limits

- v789 log SHA-256: `20427d0c0ebdbd4f29daa2c747ce9fe438e50aa8326f1b7c19e8f26e800edd77`
- v789 summary JSON SHA-256: `4dc0e689d38567f4b0057f5fb9224f4686464de5c01b8451075243d375ed1e73`
- v790 log SHA-256: `e56eeb453bb13601afcf0ca159c59c334093dcf80bc6ecb99acd54834e524c67`
- v790 summary JSON SHA-256: `7830c1e91eada47ab51fe1713a3286f665a66b197bd615ffc36a7f7d97ad5890`

The traces are finite observations from the selected replay windows. They do not prove that every registered callback ran in other frames, that the readiness field was ever set to one, that the original retail executable was launched natively on Linux, or that Vulkan translated any retail draw.
