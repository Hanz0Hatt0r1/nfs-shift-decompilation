# PM4_INTERRUPT predicate and source-IB crosswalk review — v58

Date: 2026-10-29
Scope: compare the supplied Xenos v58 / Native v55 producer-rank crosswalk
against the exact ReXGlue Xenos decoder and this branch's Native packet path.
No runtime dispatch behavior was changed.

## Findings

### Header bit 0 is Xenos Type-3 packet predication

The local ReXGlue SDK source confirms that `MakePacketType3(..., predicate)`
sets header bit 0 (`include/rex/graphics/xenos.h`, lines 1640–1644,
SHA-256 `f7dcbf856feaeb0350c9c9aaf5c16a768b4147fc487819cd513e0cc68fc16fd5`).
The exact SDK `CommandProcessor::ExecutePacketType3` checks that bit before the
opcode handler. It executes a predicated Type-3 packet only when
`(bin_select_ & bin_mask_) != 0`; otherwise it advances over the declared
payload and skips the packet (`src/graphics/command_processor.cpp`, lines
744–752, SHA-256
`53a982be7550aee8aa3194eb0741d69b55af41ab2db65e611cdacec42a67a125`).
`PM4_INTERRUPT` then reads one payload dword as a CPU mask and dispatches source
1 for each set CPU bit (same file, lines 913–926).

Thus `0xC0005401` is a predicated source-1 interrupt; `0xC0005400` is
unpredicated. P1's v58 trace reaches the Xenos interrupt handler, callback,
and retail producer for every sampled `0xC0005401, 0x4`, so the Xenos
predicate gate passed for those events. The v58 captures do not record the
actual `bin_select_`/`bin_mask_` values.

P1's subsequent low-stop v60 capture supplies those Xenos values for four
producer-linked source-1 interrupts. Its verified event-log SHA-256 is
`f4a3361588833a3048617c16c6a348fb2fb983536b1b63048bdf7427649cb581`; the
trace SHA-256 is
`3df08f3df84d039230c71f1c253ef80109649c4427e3f817e972e7f0c7aaa372`, and
metadata SHA-256 is
`632bf6dc7bfaafc0c53d588d4bbbfd4b0afefd71bb9ec5bcc60039eb1b8b211d`.
The Xenos host, runtime, XEX, and plugin identities match v58. The capture
reached Bink 281/281, sent no input, changed no guest memory, used one
interrupt hardware breakpoint and four producer stops, and captured 243
interrupt entries. The linked rows are:

The table shows the low 32 bits of the captured 64-bit bin values (zero
extended in the actual state).

| Producer rank | IRQ rank | Header | Predicate | `bin_select` | `bin_mask` | AND | P/C before producer |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 1 | 239 | `C0005400` | off | `FFFFFFFF` | `FFFFFFFF` | `FFFFFFFF` | 0 / 0 |
| 2 | 240 | `C0005401` | on | `80000003` | `80000000` | `80000000` | 1 / 1 |
| 3 | 242 | `C0005400` | off | `FFFFFFFF` | `FFFFFFFF` | `FFFFFFFF` | 2 / 2 |
| 4 | 243 | `C0005401` | on | `80000003` | `80000000` | `80000000` | 3 / 3 |

Every payload is `0x4`, all four producer calls are linked to the same LWP,
and both sampled predicated packets have a nonzero bin intersection. Their
Xenos predicate gates therefore passed. The headers and queue indices agree
with the v58 and v59 producer-rank references. This confirms Xenos-side
predicate behavior for the sampled producer events; it does not expose Native
bin state or establish cross-run causality.

The same five-entry window contains IRQ241 (`C0005400`, payload `0x4`,
all-ones bin state) with no captured `sub_823B8C60` producer between ranks 2
and 3. Its callback route remains unresolved, so it must not be attributed to
a Native queue rollback.

### Native frames both forms but does not apply the predicate gate

Native's `scan_captured_packet_stream` computes Type-3 packet size from bits
16–29 and extracts the opcode from bits 8–15; bit 0 affects neither field
(`native_vulkan/src/xbox_draw_input.cpp`, lines 169–207). For both
`0xC0005400` and `0xC0005401`, the count field is zero, so the packet is one
payload dword plus its header: 8 bytes total. `decode_captured_gpu_interrupt`
requires exactly that size and reads payload `0x4` as CPU mask `0x4` (lines
891–909).

The execution path has a semantic gap: `RingWorkerLoop` branches on Type-3
opcode `0x54`, decodes the mask, then dispatches each set bit without checking
header bit 0 or maintaining `bin_select`/`bin_mask`
(`native_vulkan/rexglue_plugin/shift_native_gpu_plugin.cpp`, lines 4087–4135;
there are no bin-select/mask references in this plugin). Native therefore
frames and payload-decodes both packet forms correctly, but it does not match
the Xenos conditional-execution rule when a predicated packet's bin test would
fail. A Native callback for a predicated packet could be extra in that case.

### Packet bounds and source-buffer shape

The Xenos crosswalk records each indirect buffer's dword count and byte
offset. For all 16 rows, the interrupt occupies 8 bytes and lies within the
measured source IB:

| IB form | Source length | Interrupt offset | Packet end | Remaining bytes |
| --- | ---: | ---: | ---: | ---: |
| Short | 35 dwords = 140 bytes | 92 | 100 | 40 |
| Long | 671 dwords = 2,684 bytes | 2,628 | 2,636 | 48 |

The Native expander reads exactly the dword count from its enclosing
`PM4_INDIRECT_BUFFER`, scans that bounded byte span, and rejects a packet
whose declared length exceeds the remaining bytes
(`native_vulkan/src/xbox_guest_ring.cpp`, lines 70–83 and 124–139). Its v55
crosswalk logs each accepted source IB address, offset, header and payload, but
does not include the numeric Native IB dword count. The Native packet was
accepted from the bounded expansion; the table alone is insufficient to
recompute that particular source extent.

The 35/671-dword source shape does not change this interrupt's length, opcode,
or mask. It is not, by itself, evidence of a packet overread or different
callback payload. It can reflect different surrounding command-buffer
construction and therefore different prior state. The concrete semantic
difference is bit 0: the first two producer-rank pairs match; at rank 3 and
later odd ranks, Xenos records `0xC0005400` while Native records
`0xC0005401`. These are separate runs paired by producer rank, not lockstep
events. The different header can affect execution if the predicate state is
false, but the crosswalk does not contain the Native predicate state or prove
that this caused the queue divergence.

## Validation performed

- Added a small `shift_xbox_guest_ring_check` case for both captured headers.
  Each must frame as an 8-byte Type-3 opcode `0x54`, leave a following NOP at
  offset 8, and decode payload `0x4` as CPU mask `0x4`.
- Built and ran the focused check directly with C++17, `-Wall -Wextra -Werror`;
  it passed.
- Ran P1's v58 crosswalk regression: 5 tests passed. An independent bounds
  check confirmed all 16 Xenos packet spans fit their captured IB extents.
  The Native crosswalk contains no numeric source-IB extents.
- Ran P1's v60 comparator against the local run metadata and v58/v59 evidence:
  all four linked producer entries validated, predicated producer ranks 2 and
  4 passed the Xenos gate, the first four headers and queue indices matched the
  v58/v59 references, and IRQ241 remained the single unlinked event.

These checks validate framing and the evidence crosswalk; they do not validate
Native conditional execution. P1's v60 capture now establishes the Xenos
predicate inputs for the sampled producer events. To determine whether
Native's missing predicate gate changes execution, the remaining minimal
runtime check is a low-intrusion Native capture of `bin_select`/`bin_mask` and
the guest producer sequence immediately around corresponding predicated
source-1 interrupts, especially producer rank 3. Do not alter dispatch
behavior until that Native-side state is available.
