# Process 1 — Controller #1 polling vs Physics Manager 30 Hz cadence

This slice closes the next Process 1 timing question left by
`SHIFT.Process1PhysicsManagerControllerOwner/1`.

The authority remains the pinned PC retail 1.02 `SHIFT.exe` plus the matching
full `SHIFT.exe.c` from Google Drive. The Xbox 360 recompilation is not required
for this promotion.

## Pinned PC inputs

```text
SHIFT.exe MD5    705af8b420e5eb1e3834ac43d5533c6b
SHIFT.exe SHA256 eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
SHIFT.exe.c SHA256
                 512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9
```

Contract:

```text
SHIFT.Process1Controller1PhysicsCadence/1
```

## 1. Controller #1 is an alertable polling worker

The already-proven Controller #1 path enters `FUN_00662880`. The PC decompile
and machine code show this loop order:

```text
message / controller work
  -> FUN_006626a0
  -> manager-list dispatch
  -> ...
  -> FUN_00649780(10, 1)
  -> loop back
```

`FUN_00649780` is the exact two-argument wrapper around imported Win32
`SleepEx`. Therefore the worker requests:

```text
SleepEx(10 ms, alertable = TRUE)
```

after its manager-dispatch work.

This is **not** a proven 100 Hz controller frequency. A 10 ms alertable sleep is
a timeout/polling boundary, not a fixed period:

- work before the sleep contributes variable elapsed time;
- the scheduler may resume later than the requested timeout;
- alertable wait can return early when an APC completes.

There is no render/presentation wait in the recovered worker loop, so this slice
does not connect Controller #1 polling to a rendered frame.

## 2. Physics Manager independently selects 30 Hz

Physics Manager vtable `0x00b04524` has `FUN_00710a70` at slot `+0x4`.
`FUN_00710a70` calls:

```text
FUN_00647860(PhysicsManager, 0, 30.0f)
```

The generic setter `FUN_00647860` stores:

```text
manager+0xdc = 1
manager+0xe0 = 30.0
manager+0xe8 = trunc(1000.0 / 30.0) = 33
manager+0xf8 = 0
```

The generic manager diagnostic path labels `manager+0xe0` as:

```text
Desired Freq = %2.2f Hz
```

So `30.0` is now source- and machine-backed as the Physics Manager desired
frequency. The integer scheduler period is independently reproduced as 33 ms.

## 3. Selected Physics Manager scheduler mode dispatches at most once per call

`FUN_00647ef0` has multiple generic modes. The Physics Manager initialization
selects the fixed-frequency branch (`+0xdc != 0`) with mode byte `+0xf8 == 0`.

For that exact selected mode, the recovered branch:

1. adds elapsed time to the residual accumulator;
2. compares it against the integer 33 ms period with the framework tolerance;
3. dispatches `FUN_00647d80` at most once;
4. retains the residual after consuming one period.

The other generic scheduler modes must not be projected onto Physics Manager.
In particular, generic multi-dispatch behavior elsewhere in `FUN_00647ef0` does
not prove multiple Physics Manager updates per one selected scheduler call.

## 4. Three cadence domains remain separate

The evidence now distinguishes:

```text
Controller #1 worker polling:
    SleepEx(10, TRUE)

Physics Manager internal scheduler:
    Desired Freq = 30 Hz
    integer period = 33 ms
    residual accumulator

render / presentation:
    not joined here
```

No equality among those domains is inferred.

The following claims remain forbidden:

- `SleepEx(10)` means exactly 100 Hz;
- Controller #1 wakes exactly every 10 ms;
- Controller #1 cadence equals Physics Manager cadence;
- Physics Manager 30 Hz equals render cadence;
- one Physics Manager update occurs per rendered frame;
- render/presentation wakes or phase-locks Controller #1.

The 30 Hz value is a **manager-internal desired frequency**. It is not a proof
of exact wall-clock 30 Hz, because the surrounding controller polling,
accumulator residual, OS scheduling and alertable-wake behavior remain distinct.

## Machine-locked spans

The contract pins these PC retail spans:

- Controller dispatch -> alertable sleep -> loop back:
  `0x006629ef..0x00662a92`,
  SHA-256 `7162bf4986b40ba0fed17689144c996ff3787896c6e357fff93802ba957f8812`;
- `SleepEx` wrapper:
  `0x00649780..0x0064978c`,
  SHA-256 `260451a7ed8644869aebf1085cde645cf66e9be0397021c69457405e77d760a5`;
- Physics Manager init vtable slot `+0x4`:
  `0x00b04528..0x00b0452c`,
  SHA-256 `af5a703bed6ab7af99e1cc148b10e9bcff1c0bd9546366b80fc8158bcf9a9547`;
- `FUN_00710a70 -> FUN_00647860(..., 30.0f)`:
  `0x00710ac5..0x00710ad8`,
  SHA-256 `42287985821d4791ba878c05c057a41dac685024c263aeb37d8664ad806068da`;
- frequency setter:
  `0x00647860..0x006478a9`,
  SHA-256 `22c1656bac743db9d3ca84ff703ea79036fee14e63f93e3095a87b2dd5422081`;
- selected mode gate:
  `0x00647fe2..0x00647fef`,
  SHA-256 `58438134add52369441bb9ded374dd3e5d66b59b57b7c5b651a69b091ba3943e`;
- selected single-dispatch accumulator branch:
  `0x006483bd..0x00648497`,
  SHA-256 `38ff27af839ae9ea9a8745aa6e12efcfa1b0c3e4240791fa639a517f6aeaedb9`.

## Next Process 1 blocker

The next bounded target is no longer the ordinary polling timeout. It is to
enumerate every producer that can wake the alertable Controller #1 worker
(APC/message/other synchronization path), then test whether any proven
render/presentation path reaches those producers.

Until such a join exists, Process 1 must keep:

```text
10 ms Controller #1 polling timeout
!= 30 Hz Physics Manager desired cadence
!= render/presentation cadence
```

No original-game execution is required for this static closure.
