# BMW BODY0 targeted runtime probe — operator usage

This capture is intentionally bounded. It records raw observations for Process 1 and does not infer retail semantics from matching values.

## Basic run

Start the retail game first, enter a Silverstone session with the target BMW, then from the repository run:

```bash
bash tools/shift_live_dump/capture_bmw_body0.sh
```

The default capture window is 20 seconds with 50 ms host-side sampling. The output is written to:

```text
out/bmw_body0_runtime_probe/
  capture_metadata.json
  maps.txt
  samples.jsonl
```

During the capture use this short sequence:

```text
0–5 s   leave the car idle
5–10 s  hold throttle
10–15 s steer left/right while applying light throttle
15–20 s release controls
```

If more than one process matches `SHIFT.exe`, pass its PID after the output argument:

```bash
bash tools/shift_live_dump/capture_bmw_body0.sh out/bmw_body0_runtime_probe --pid 12345
```

## Optional known memory regions

The collector can sample explicitly named virtual-memory regions when Process 1 has produced exact addresses for a specific run:

```bash
bash tools/shift_live_dump/capture_bmw_body0.sh \
  out/bmw_body0_runtime_probe \
  --pid 12345 \
  --region 0x12345678:0x170:body_candidate
```

Repeat `--region` for more than one bounded region. Each sample stores raw bytes plus SHA-256. The collector does not label those bytes as BODY0 pose or bind-frame state; that join remains a separate proof step.

On Linux systems where `/proc/<pid>/mem` access is restricted, region reads may fail while process/module/map observations still succeed. Do not weaken ptrace/Yama security settings merely to satisfy this collector; use the existing project capture mechanisms or a narrower approved runtime instrumentation route instead.

## Configuration

Environment variables:

```text
SHIFT_BMW_BODY0_CAPTURE_SECONDS   capture length, default 20
SHIFT_BMW_BODY0_SAMPLE_MS         host sample interval, default 50
```

The collector caps captures at 300 seconds and region reads at 1 MiB per requested region to prevent accidental broad memory dumping.

## Evidence boundary

The artifact can establish session identity, executable/module identity, memory-map stability and bounded changes in exact explicitly requested regions. It does not by itself prove:

- BMW BODY0 identity;
- construction/bind ownership;
- retail scheduler cadence;
- control-producer semantics;
- that a matching numeric transform is the authoritative vehicle pose.

Those claims require a later static/runtime provenance join before `SHIFT.BMWBody0BindFrameProof/1` can become positive.
