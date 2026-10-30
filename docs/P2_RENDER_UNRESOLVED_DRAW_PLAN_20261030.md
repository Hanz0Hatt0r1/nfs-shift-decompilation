# P2 Renderer Plan: unresolved draw packets and shader control-flow opcode 7

Status: planning / analysis. Not a fix. No code changed by this document.
Branch: `work/xbox360-retail-runtime-p1-20261023`. Date: 2026-10-30.
Process: P2 (renderer lane). Related open gate: X3 (retail SHIFT splash rendered; menu
background currently black on the Native Vulkan backend).

Every claim below names a file and line, or is explicitly marked **unknown**. Nothing in
this document is presented as retail-correct behaviour: the goal is to bound exactly what
the emulator is refusing to render and to propose tests that can prove each step.

---

## 0. Evidence base

Run under analysis (read-only):

- Renderer log: `/home/pes/work/nfs-shift-p1-menu-setup-v118-repeat-native-retry-20261029/bin/logs/nfs_shift_001.log`
  (2,291,821 bytes, last write 2026-10-29 21:26).
- Plugin source: `/home/pes/work/nfs-shift-xbox-live-ring-20261023/native_vulkan/rexglue_plugin/shift_native_gpu_plugin.cpp`
  (222,863 bytes, ~4422 lines, branch `work/process2-xbox-live-ring-20261023`, PR #2161).
- SDK clone used for codegen semantics: `/home/pes/work/rexglue-sdk-xbox360-memory-lifecycle-20261025`
  (see `docs/XBOX360_BUILD_PINS_20261030.md` for the pin).

Two independent failure families appear in the same frame:

1. **Failure 1 — unresolved draw packets.** The frame refresh aborts before any of the
   captured draws are translated. This is the immediate cause of the black menu background.
2. **Opcode 7 — unsupported captured shader control-flow opcode.** Even if family 1 were
   fixed, draw #6 would still fail translation.

Quoted log lines (verbatim prefix, truncated with `…` only where noted):

```
[2026-10-29 21:24:18.605] [warning] [core] [t1177800] shift-native: Vulkan frame refresh failed for 1280x720 with 1 captured draws (failure 1): captured operation stream contains unresolved draw packet 0; ordered operations=unresolved(packet=0,draw_registers={valid_mask=0x17038,surface=0x0,color=0x0,depth=0x0,mode=0x4,depth_control=0x0,color_mask=0x0,stencil_refmask=0x0,stencil_refmask_valid=0,screen_scissor=[0x0,0x0],window_scissor=[0x0,0x100010]});unresolved(packet=1,…);…
```

```
[2026-10-29 21:25:30.760] [info] [core] [t1177800] shift-native: unresolved captured draw #6 topology=2 autoindex=true count=24 raster=true inputs=false translated=false: captured pixel shader: unsupported captured shader control-flow opcode 7 at instruction 1
```

Note the two timestamps: 21:24:18 (frame-refresh failure, packet-level) and 21:25:30
(draw #6, shader-level), 72 s apart. They are reported by different code paths and are
not necessarily from the same frame. **unknown**: whether the two lines describe the same
submission; the log carries no frame/packet correlation id (see T6).

---

## 1. Root-cause matrix (a): `valid_mask=0x17038` and the zeroed draw registers

### 1.1 What the mask is

`valid_mask` is produced per packet at
`native_vulkan/rexglue_plugin/shift_native_gpu_plugin.cpp:3403-3407` and stored on the
operation at `:3719-3720` (or `:3738` in the second emission path). The plugin receives a
filled `raster_registers` struct plus a `draw_register_valid_mask`; the mask is *not*
derived from the register values — a bit is set when the corresponding PM4 register write
was **seen**, and the value can still be zero.

Because the mask is an index into the plugin's own register table (a `RasterRegisters`
struct), the exact bit→field mapping is only authoritative if read from that struct's
declaration order. **unknown (must be closed by T1)**: the struct field order that maps
bit *n* to a named field. This document reasons only from
mask-value arithmetic and from the *values printed alongside* the mask, which is enough to
give a falsifiable hypothesis but not a verified bit table.

Working hypothesis for the bit table (arithmetic on the printed values, to be confirmed):

- `valid_mask = 0x0001_7038`.
  - `0x...38` = bits 3, 4, 5.
  - `0x...7000` = bits 14, 13, 12 (i.e. `0x17000` = bits 12,13,14).
  - bit 16 (0x10000) is set.
  - Bits **not** set: 0, 1, 2 (low three), and 6, 7, 0x1F beyond.

- The values printed for a masked register are, per the log line, exactly:
  `surface=0x0, color=0x0, depth=0x0, mode=0x4, depth_control=0x0, color_mask=0x0,
  stencil_refmask=0x0, stencil_refmask_valid=0, screen_scissor=[0x0,0x0],
  window_scissor=[0x0,0x100010]`.

So of the seven render-target-critical fields the task named, **only `window_scissor` is
non-trivially populated** (`[0x0, 0x100010]` → x/y at 0, width=0x10, height=0x10 when read
as the packed Xenia-style scissor pair: `0x100010` = width 0x0010 | height 0x0010 << 16,
**unknown** whether the plugin's convention is (tl, br) or (wh)). `mode=0x4` is a non-zero
enum, and `screen_scissor=[0x0,0x0]` is degenerate. `surface`, `color`, `depth`,
`color_mask`, `stencil_refmask` are all **0**.

### 1.2 Why a 24-packet prefix can legitimately carry zeros

Three explanations are consistent with the printed data; they are ranked by how cheaply
they can be falsified.

| # | Hypothesis | Prediction if true | Falsifying observation |
|---|---|---|---|
| R1 | The mask is **register-write-seen**, not register-valid. These 24 packets are `INDIRECT_BUFFER`/`SET_CONSTANT`/`EVENT`-style packets where only the 6 masked registers were written; the real `DRAW_INDX` at packet 24 would have written the rest. | A packet-24 record exists with a larger mask (e.g. `surface!=0`) and `translated=true`; the envelope of all masks in one IB unions to the full set. | Every packet in the IB has the same 0x17038 mask → it is not a prefix effect. |
| R2 | The guest really did submit a draw with **no bound surface** and the plugin is right to refuse it. Retail hardware would rasterize nothing. | The guest's packet stream for this IB contains `SET_SURFACE` writes that the capture layer dropped (mask never sees them). | Capture layer (below the guest) shows the `SET_SURFACE` writes; they are lost between PIX event and register snapshot. |
| R3 | The plugin's snapshot is taken **before** the register state that precedes the draw is applied — i.e. an ordering bug in the operation list builder, not a guest bug. | Reordering the snapshot to "registers at draw-packet time" yields non-zero surface/color for the same IB. | Replay of the same IB outside the plugin still shows zero surfaces. |

The log line itself asserts *"captured operation stream contains unresolved draw packet 0;
ordered operations=…"*, i.e. the plugin has an **ordered operation list** in which packets
0..23 are `unresolved(...)` records. That wording is direct evidence for R1/R3 over R2:
the packets are being *classified* as draws and then rejected for missing registers, rather
than being recognised as non-draw state packets and folded into the register state.
**unknown**: which classification routine produced `unresolved(packet=N, …)`; it is built
as a string with the `draw_registers={…}` formatter, and the formatter's producer is not
located in the 4422-line file by name alone (see T1).

### 1.3 Code paths that populate the register fields

Confirmed locations in the plugin source:

- `:3403-3407` — `draw_register_valid_mask` is produced together with `raster_registers`
  via a call that takes `&raster_registers, &draw_register_valid_mask`.
- `:3426` — `detail << error << " valid_mask=0x" << std::hex` — this is the *other*
  formatter (the `valid_mask=0x` spelling), used on an error path, not the
  `draw_registers={valid_mask=…}` spelling seen in the log. The log's spelling therefore
  comes from a third site. **unknown**: exact line of the `draw_registers={…}` formatter.
- `:3717-3721` and `:3736-3739` — the two places an operation is marked
  `draw_registers_ready = (draw_register_valid_mask != 0)` and the struct copied.
  **This is the important one**: readiness is decided purely by
  `valid_mask != 0`. `0x17038 != 0`, so a packet with a completely empty render-target
  set is declared *register-ready* and proceeds to translation, then fails later.
- `:3786-3790` — the second wait/marker path, same predicate
  (`draw_register_valid_mask != 0`).
- `:3519-3522` — `copy_clear_valid_mask & 6u == 6u` and `& 1u` — a separate clear-path
  validity idiom, showing the file already uses bit-checks against *field groups* for
  clears but not for draws. This is the natural place to introduce the same idiom for
  draws (T2).
- `:4129` — the `REXLOG_WARN("shift-native: Vulkan frame refresh failed for {}x{} …")`
  emission site.

### 1.4 Root-cause statement for (a)

**The operation stream builder classifies PM4 packets as draws and gates draw readiness on
"any register seen" (`draw_register_valid_mask != 0`) instead of "render-target complete"
(`surface && color && depth/color_mask` per the guest's surface kind).** A 24-packet
prelude that writes only 6 of the tracked registers therefore yields 24 unusable draw
operations, and the frame refresh aborts on the first one *before* reaching whatever
packet 24 actually is. Verified anchors: `:3717-3721`, `:3736-3739`, `:3786-3790`,
`:4129`. The bit→register mapping is **unknown** and must be measured (T1), not guessed.

---

## 2. Root-cause matrix (b): failure 1 semantics and frame-level abort

- The frame-level failure is emitted at `:4129`: *"Vulkan frame refresh failed for
  1280x720 with 1 captured draws (failure 1)"*. Two numbers are relevant and should be
  read together: **1 captured draw** and **24 unresolved packets**. The captured-draw
  counter and the packet counter are not the same counter. **unknown**: whether
  "1 captured draw" counts *translatable* draws (so the 24 unresolved packets are not
  counted) or something else. The log's phrase `with 1 captured draws` is grammatically
  singular-plural inconsistent, which is a hint the counter was repurposed.
- `failure 1` is an enum/`Result` value, not a count. The log shows exactly one
  `frame refresh failed` occurrence within the sampled window
  (`grep -m1` returned a single line; the full log has ≥1). **unknown**: the enum
  definition mapping `1` to a name. The literal string is the only authority available
  without the enum header.
- Decision semantics: the refresh path **does not skip** an unresolved packet; it aborts
  the whole frame and returns failure to the caller. This is a deliberate fail-closed
  design (no partial frames, no hallucinated geometry) and should be *kept* — the fix is
  to stop mis-classifying packets, not to start skipping them silently. Any proposal to
  "skip and continue" must land behind an explicit diagnostics flag and must never be
  enabled on an evidence run.

Consequence for the menu background: because the abort happens at packet 0 of the
operation stream, **nothing after packet 0 of the first captured draw is ever translated**,
so the state of opcode 7 and the state of the actual menu geometry are both downstream of
failure 1. Fix ordering matters: failure 1 first, then opcode 7.

---

## 3. Root-cause matrix (c): shader control-flow opcode 7

### 3.1 What we have

Log (21:25:30.760):

```
unresolved captured draw #6 topology=2 autoindex=true count=24 raster=true inputs=false translated=false: captured pixel shader: unsupported captured shader control-flow opcode 7 at instruction 1
```

Readings that follow from the string alone (each is a fact about the *reporter*):

- `topology=2` — primitive type index 2 (Xenos/DI primitive-topology enum; commonly
  `RECTLIST`/`LINELIST` depending on the enum base). **unknown** which base.
- `autoindex=true`, `count=24` — 24 vertices, auto-indexed.
- `raster=true` — rasterization enabled.
- `inputs=false` — vertex inputs are **not** resolved. This is a *second* independent
  defect on the same draw: even with a supported shader, a draw with
  `inputs=false` cannot be submitted.
- `translated=false` — the shader did not translate, hence the draw did not translate.
- `unsupported captured shader control-flow opcode 7 **at instruction 1**` — instruction
  index 1 (the second uCode instruction; index 0 translated fine).

### 3.2 Candidate identity of opcode 7 — what I could and could not verify

The Xenos shader ISA encodes control-flow in the high bits of a uCode dword (an `EXEC` /
`CF` field). The known family includes unconditional `EXEC`, `EXEC_END`, `JUMP`,
`JUMP_ANY`, `JUMP_EVERY`, `JUMP_ALL`, `CALL`, `CALL_C`, `RETURN`, `LOOP_START`,
`LOOP_END`, `LOOP_BREAK`, `PUSH`, `POP`, as documented in the Xenia/`xenos` shader
translation community references and in retail-reverse-engineering literature.

I attempted to decode opcode 7 **from the captured shader bytes**. Result: **I could not
retrieve the captured shader**. The capture is not serialised into the v118 run directory
that I have read access to — the run dir contains `bin/logs/nfs_shift_001.log`,
`run_metadata.json` and `gdb.log`, and the renderer log prints only the *diagnostic*, not
the uCode dword. Therefore:

- **unknown (high confidence needed)**: whether opcode 7 is `LOOP_START`, `CALL`, or an
  unmapped slot. I will not guess. The two leading candidates and their consequences
  differ materially:
  - If opcode 7 is a **loop** opcode, the fix is loop-structure reconstruction and the
    risk is silent mis-iteration (worst case: infinite loop or wrong frame count), not
    just "unsupported".
  - If opcode 7 is a **subroutine call/tail call**, the fix needs a call stack and a
    return-address expression register, which is a much larger translator change.
- The `at instruction 1` position is informative: many retail pixel shaders begin with
  `EXEC` (index 0) then a very short prologue, so index 1 being a control-flow opcode
  suggests a branchy shader (not a trivial constant-colour blit). That is evidence *against*
  the "menu background is a simple clear/quad" theory and *for* "the menu background pass
  uses a real material shader with control flow".

Repo-side decoding aids that exist and should be used in T4:
`tools/analyze_shader_opcode_gaps.py`, `tools/audit_shader_family_fxo.py`,
`tools/audit_fxo_shader_corpus.py`, `tools/audit_imb_material_shader_ranking.py`,
`tools/run_silverstone_renderer_shader_target_regeneration.py`. Note these are *corpus /
gap analysers* over extracted `.fxo`/shader blobs; none of them contains a Xenos uCode→
opcode-name table that I could confirm, so a reference decoder is a deliverable, not an
existing tool (**unknown** until T4 checks them).

### 3.3 Where the translator switch must be

The plugin contains the string `unsupported captured shader control-flow opcode`
(the log proves it), but the string is emitted from within the shader-translation helper
family rather than from the identified lines. The authoritative pattern for what a
"switch on opcode" looks like in this codebase is the **ReXGlue PPC** side, not the GPU
side: `rexglue-sdk-.../src/codegen/builders/vector.cpp:1325` shows
`case 5: // float16_4` — an opcode switch keyed on a literal case index with a comment
naming the field. The GPU translator switch should be located and documented the same way
(T4), because the two-stage translation (guest PM4 → captured op → translated) means a
misnamed GPU opcode and a misnamed PPC opcode look identical in the log.

---

## 4. Ranked task list

Each task has an owner-agnostic acceptance criterion that can be checked from a log line
or a committed artefact. Ordered by information gain per unit effort.

**T1 — Pin the bit table and the struct layout (blocker for everything else).**
Produce a generated, committed table mapping each `valid_mask` bit to the
`RasterRegisters` field name and to the originating PM4 register index. Method: compile a
tiny probe or read the struct declaration order; cross-check against
`:3403-3407` and the two formatters (`:3426`, and the unlocated `draw_registers={…}` site).
Acceptance: a committed markdown/markdown-generated table, and the `0x17038` decode
reproduces the six printed fields exactly, with no unexplained bit.

**T2 — Make draw readiness a render-target predicate, not a "saw any register" predicate.**
Change the three sites `:3717-3721`, `:3736-3739`, `:3786-3790` to require the fields per
§1.2, mirroring the clear idiom already at `:3519-3522`. Acceptance: a unit test feeding a
synthetic `raster_registers` with `surface=color=depth=0, valid_mask=0x17038` yields
*not ready* and a typed diagnostic naming the missing fields; the same input with a
surface resolves as ready.

**T3 — Classify non-draw packets as state, not as unresolved draws.**
The 24-packet prelude should fold into register state. Acceptance: replaying the captured
IB from the v118 run produces an operation list with **zero** `unresolved(...)` entries
whose mask is `0x17038`, and reports the state-only packets under a `state` count.

**T4 — Build a Xenos uCode reference decoder and decode opcode 7.**
Deliver `tools/<…>_xenos_ucode_decode.py` (repo-standard `main()` + asserts) that prints
opcode name, exec/cf field, and operand expressions for a uCode dword stream; validate it
against the existing corpus in `tools/audit_fxo_shader_corpus.py` orbit. Acceptance: opcode
7 is **named from an authoritative table with a citation**, and the specific captured
shader's instruction 0 and 1 are decoded and printed in a run artefact. Until T4 lands,
opcode 7 remains **unknown** and must not be implemented from guesswork.

**T5 — Capture the shader bytes into the run directory.**
The renderer log must emit a bounded, hashed hexdump of the first N uCode dwords when a
shader fails to translate, so a failed capture is still analytically usable. Acceptance:
`nfs_shift_001.log` for a new run contains the failing shader hash + hexdump, and the
hash is reproducible offline by T4.

**T6 — Correlation ids.**
The two failure families are 72 s apart in the log with no correlation. Add a
`(frame_id, packet_index, draw_index)` triple to both the frame-refresh failure and the
per-draw translation diagnostic. Acceptance: grep of one frame's lines can reconstruct
their ordering with no timestamp heuristics.

**T7 — Fix `inputs=false` on draw #6.**
Independent of opcode 7; a draw with unresolved vertex inputs cannot be submitted even
with a valid shader. Acceptance: a diagnostic distinguishing "no vertex declaration seen"
from "declaration seen but unsupported", plus a reproducer test.

**T8 — The real target: menu background not black.**
Definition of done (end-to-end, all required):
1. Opcode 7 draw reaches `translated=true`.
2. Frame refresh no longer aborts with `failure 1` on the menu-background capture.
3. A read-back of the menu-background region is **not** all-black, and the non-black pixel
   count and the read-back hash are committed to `evidence/`.
4. The same read-back numbers are reproduced on a **paired Xenos run** — the existing
   convention for this lane is a paired Xenos/Native run with both logs retained
   (`run_metadata.json` in each run dir).
5. No synthetic override: the pixels must come from a translated retail draw; if any draw
   is skipped, the skip must be visible and counted in the evidence file.

Explicitly **out of scope / not a fix**: raising the skip threshold, force-clearing the
unresolved frames, or substituting a clear colour for the menu background. Those would
produce a non-black frame that is not retail output and are forbidden by the fail-closed
rule.

---

## 5. Tests to add (CTest target names)

Convention: targets live in `native_vulkan/rexglue_plugin/CMakeLists.txt` alongside the
existing plugin targets; each is a small executable returning non-zero on failure.

- `shift_render_draw_register_validity_test` — T2 predicate table (synthetic
  `raster_registers` × mask matrix, including the exact `0x17038` case).
- `shift_render_valid_mask_decode_test` — T1 bit-table round-trip; fails if a bit has no
  documented name.
- `shift_render_packet_classification_test` — T3 operation-list builder on a recorded
  packet log; asserts zero spurious `unresolved` entries.
- `shift_render_shader_opcode_decode_test` — T4 decoder on a committed uCode fixture.
- `shift_render_diagnostics_correlation_test` — T6 log-line format contract.

## 6. Open unknowns (explicit)

1. Bit→field mapping of `draw_registers.valid_mask` (T1).
2. Exact source line of the `draw_registers={…}` formatter and of the
   `unresolved(packet=N, …)` producer.
3. The `failure 1` enum name.
4. Whether the 24 packets and the 72 s-later draw #6 belong to the same frame.
5. Identity of shader control-flow opcode 7 (T4).
6. Whether the scissor pair is `(top-left, bottom-right)` or `(x/y, width/height)`; the
   value `0x100010` is consistent with 16×16 either way.
7. Why `inputs=false` while `raster=true` on draw #6 (T7).
