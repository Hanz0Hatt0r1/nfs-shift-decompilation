# PM4_INTERRUPT predicate and source-IB crosswalk review — v58

Date: 2026-10-29
Scope: compare the supplied Xenos v58 / Native v55 producer-rank crosswalk
against the exact ReXGlue Xenos decoder and this branch's Native packet path.
The initial review was evidence-only; the v72 follow-up below adds Native
Type-3 predicate execution and captured regressions.

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

### Native packet framing and the missing execution gate

Native's `scan_captured_packet_stream` computes Type-3 packet size from bits
16–29 and extracts the opcode from bits 8–15; bit 0 affects neither field
(`native_vulkan/src/xbox_draw_input.cpp`, lines 169–207). For both
`0xC0005400` and `0xC0005401`, the count field is zero, so the packet is one
payload dword plus its header: 8 bytes total. `decode_captured_gpu_interrupt`
requires exactly that size and reads payload `0x4` as CPU mask `0x4` (lines
891–909).

Before the v72 follow-up, the execution path had a semantic gap:
`RingWorkerLoop` branched on Type-3
opcode `0x54`, decodes the mask, then dispatches each set bit without checking
header bit 0 or maintaining `bin_select`/`bin_mask`
(`native_vulkan/rexglue_plugin/shift_native_gpu_plugin.cpp`, lines 4087–4135;
there are no bin-select/mask references in this plugin). Native therefore
framed and payload-decoded both packet forms correctly, but did not match the
Xenos conditional-execution rule when a predicated packet's bin test failed.

## v72 rank-3/rank-4 cause analysis

P1's updated evidence file
`evidence/xbox360_linux_native_xenos_first_producer_divergence_v72_20261029.json`
has SHA-256
`b6f5413fd0d71f00ea2428bd853441543cab8c46e63c928c76ed2b5c9b9b538c`.
The Native capture itself has SHA-256
`676cb87812b0dd697ccf7aa87a90b1942013c7d72f2c598e38c1853a450e89fc`.
P1 also updated the v72 callback-interval join: producer ranks 3 and 4 occur
on the same LWP inside source-1 dispatch intervals `0xEB2` and `0xEB4`.

The ring batch at generation 1, `RPTR=5992`, `WPTR=6025` is 33 dwords long
and explicitly references child IB `0x096D8F80`, 671 dwords, twice: parent
dword offsets 2 and 7. The Native expander visits each reference in order;
its active-buffer list is a recursion-cycle check, not a global dedup set, and
the stack entry is popped after each child. This behavior is correct for two
sequential PM4_INDIRECT_BUFFER commands. The v72 ring log confirms both
interrupt occurrences were dispatched from that batch:

| Queue producer rank | Expanded packet ordinal | Child occurrence | Dispatch | Queue value |
| ---: | ---: | --- | --- | ---: |
| 3 | 181 | First reference (parent dword 2) | `0xEB2` | 2 → 3 |
| 4 | 367 | Second reference (parent dword 7) | `0xEB4` | 3 → 4 |

Each target is child dword 657 (`0xA44`, byte offset 2628), header
`0xC0005401`, payload `0x4`. The child contains 184 framed packets; its target
is zero-based packet 179. Including the root's leading SET_BIN_SELECT_LO and
IB packets gives ordinal 181 in the first expansion; the second occurrence
adds the first child's 184 packets and two more root packets, yielding 367.
The exact logger lines make the source packet certain, and callback intervals
link both producer writes to their respective dispatches. Parent occurrence
assignment is further supported by that expanded order. P1's v69 repeat
shows the same repeated child pattern at ordinals 181 and 367.

The packet's expected Xenos predicate result is derivable from the captured
commands even though no live Native BIN register was sampled. SDK semantics
map parent `0xC0006200` to SET_BIN_SELECT_LO, so the first and second child
executions inherit low select values `0xC` and `0x30`. Before dword 657, the
child writes BIN_MASK_HI=0 at dword 547, then BIN_MASK_LO=`0xFFFFFFFF` and
`0x80000000` at dwords 628 and 630. No BIN_SELECT writes occur in the child
before the interrupt. Thus the mask at the target is
`0x0000000080000000`; select-and-mask is zero for both occurrences:

| Child execution | BIN_SELECT low | BIN_MASK | Intersection | `C0005401` action |
| --- | ---: | ---: | ---: | --- |
| First | `0x0000000C` | `0x0000000080000000` | `0` | Skip |
| Second | `0x00000030` | `0x0000000080000000` | `0` | Skip |

The predicate state is command-stream-derived, not a direct hardware sample.
The missing Native gate explains why both packets nevertheless reached the
source-1 callback and produced queue values 3 and 4. This is a confirmed Native
PM4 execution defect for the captured batch. It does not prove that this
renderer defect alone caused the different Xenos rank-3 stream: the separate
Xenos run uses a 35-dword IB at `0x096E0B20+92` with unpredicated
`0xC0005400`, and separate runs are not lockstep comparisons.

The v72 repeat's parent occurrence and callback interval evidence also settle
the duplicated-IB question: Native should process both explicit references;
only the two predicated packets inside them should be skipped for this BIN
state. No ring replay or stale-IB traversal is indicated by this batch.

### Implemented response

The Native PM4 path now maintains the Xenos BIN_SELECT/BIN_MASK state, applies
Type-3 header bit 0 before packet execution, and updates the state from full
and low/high BIN setter packets. A predicate-failed indirect-buffer command
marks its nested packets non-executable while preserving the flattened stream
and parent order. Trace mode records skipped packet source, caller packet,
BIN_SELECT, and BIN_MASK. Duplicate unpredicated IB references continue to
expand and execute in sequence.

One traversal edge case remains: `expand_guest_indirect_buffers()` resolves
and parses nested IB contents before `RingWorkerLoop` evaluates the flattened
Type-3 predicate. A predicate-failed IB is therefore prevented from executing,
but its child address is still read and parsed; an invalid or inaccessible
child can still make expansion fail. Xenos checks the IB packet predicate
before dispatching the IB. The captured v72 parent IB packets are unpredicated,
so this does not affect the current rank-3/rank-4 correction. Defer changing
the expander until a captured predicated-IB case or a broader need justifies
moving predicate evaluation into recursive expansion.

The focused regression reproduces the captured selectors (`0xC`, `0x30`),
mask writes, duplicate IB references, and the two skipped interrupts. It also
checks an unpredicated interrupt and the positive Xenos v60 predicate state.

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
- Built and ran `shift_xbox_guest_ring_check` with `-Wall -Wextra -Werror`,
  then ran its CTest target: 1/1 passed.
- Built the Native plugin (`rexgpu-shift-native`) and live-ring smoke target;
  plugin CTest passed 7/7. The built Linux plugin SHA-256 is
  `fd615adad5febc2adcf9a46fa0b74a67c9cf28f013bc74ca8715ac9abad9c490`
  (ELF Build ID `14bc1880e1786605356deda62829d4c18a47d125`) at
  `/home/pes/work/rexglue-sdk-rexui-vulkan-20261023/out/linux-amd64/librexgpu-shift-native.so`.
- P1's paired no-input retail runs (Native v75 / Xenos v76) both exited GDB
  successfully and reached Bink `281/281`. They used the same XEX
  (`8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58`), host,
  runtime, runner/trace, and game-data root path; only the GPU plugin differed.
  The game-data root was not hashed at launch, so byte-for-byte resource
  equality is unverified.
- Native retail trace logged both duplicate child packets at
  `0x096B4E00+0xA44` as skipped: packet 181 under select `0xC`, and packet 367
  under select `0x30`; both used mask `0x80000000`, giving an empty
  intersection. This confirms the predicate gate in the retail runtime.
  A separate `PM4_INTERRUPT_BEGIN` at the same guest source and offset belongs
  to ring batch `2549/2554`, dispatch `0xDDC`; address equality alone does not
  link it to either skipped duplicate.
- Both captures ended with an empty service queue, `manager+11012=1`, and
  drained worker rings. Native drained at `2048/2048`; Xenos at `2116/2116`.
  The 68-entry difference remains unexplained because the bounded capture has
  no complete PM4-to-worker-ring crosswalk. This does not establish a game
  progress difference or prove a visible menu, input response, or race.
- P1's machine-readable evidence is
  `/home/pes/work/nfs-shift-xbox360-runtime-p1-20261023/evidence/xbox360_linux_pr2161_predicate_retail_pair_v75_native_v76_xenos_20261029.json`
  (SHA-256 `b2cc273a97fc6136bfef619dc564e2326ca6ecd2c5a6b4f045be8bf559da3909`);
  the read-only P1 report is
  `/home/pes/work/nfs-shift-xbox360-runtime-p1-20261023/docs/XBOX360_PR2161_PREDICATE_RETAIL_VERIFICATION_V75_V76_20261029.md`.
