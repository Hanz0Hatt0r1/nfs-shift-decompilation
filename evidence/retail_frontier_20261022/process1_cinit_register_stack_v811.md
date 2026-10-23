# Original-PE `0x0050F010` register and stack replay: v811

Date: 2026-10-22. This is a one-frame replay of original SHIFT PC retail 1.02
PE32 x86 in the Linux P-code runtime. It directly traced the initializer
function; it does not prove a visible frontend, retail rendering, or race entry.

## Identity and input coverage

- Original PE SHA-256: `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.
- Runtime SHA-256: `135c2452d882da91a249fb01acd9e5a3deedab42bde826097e43d9eb6aaff54e`.
- v659 module manifest SHA-256:
  `6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`.
- The manifest loads `rvi_0050f010` from
  `function-0050f010-full-pcode-20261020/lowered-v1/libnfs_shift_pcode_supplement.so`.
  Manifest and file SHA-256 both equal
  `966823f0caf2f115195e72633c7324fef300ec96450ee002f1915891418e1c8d`; it
  exports 249 instructions and 744 P-code operations.
- The matching complete Ghidra function export has 249 instructions. The
  verified-byte audit passed all five required epilogue instruction addresses
  against the pinned PE. Its report is
  [process1_cinit_register_stack_v811-pcode-audit.json](process1_cinit_register_stack_v811-pcode-audit.json).
  The audit explicitly does not claim behavioral parity.

## Observed call and return

v811 selected `0x0050F010` in the live guest-call trace. The event was:

| Field | Entry | Return |
|---|---:|---:|
| Caller | `0x0041D7B0` | `0x0041D7B0` |
| Return address | `0x00A75C58` | — |
| EAX | `0x0041D7B0` | `1` |
| ESI | `0x00AA6828` | `0x00AA6828` |
| EDI | `0x00AA9968` | `0x00AA9968` |
| EBP | `0x7FFDEFFC` | `0x7FFDEFFC` |
| ESP | `0x7FFDEF64` | `0x7FFDEF68` |

The entry stack word at `ESP` was the recorded return address `0x00A75C58`;
the trace sampled the next three words as `0x009075E5`, `0x00000A28`, and
`0x00000002`. The completed call therefore returned EAX=1, preserved the
observed nonvolatile ESI/EDI/EBP values, and consumed exactly the caller return
address from the stack. This confirms that the v659 supplemental body executes
through the original PE return block in this startup context.

## Result and limits

- v811 completed one host frame with status `host-frame-loop`, exit 0, and no
  runtime blocker. It reported zero Vulkan validation errors, while
  `guest_draw_translation=false` and `retail_rendering_proven=false`.
- The earlier v303-v310 mismatch was tied to the incomplete frozen base-corpus
  row. It is not a reproduced runtime blocker when the v659 full-function
  override is loaded. Do not add a synthetic RET or loader-side workaround.
- The frozen 2026-10-17 monolithic export still lacks the verified epilogue.
  Keep the completeness gate enabled for that export; validate the effective
  export or loaded override when testing a newer runtime module set.
- The one-frame replay establishes this function's observed return behavior
  only. It does not establish full P-code parity, ARM64 behavior, frontend
  readiness, retail drawing, or gameplay.

Run log SHA-256: `0c0476e498b004a59feb6d3273c5fb7e8b1d71f6e5a84e56fb7307e443c42d97`.
