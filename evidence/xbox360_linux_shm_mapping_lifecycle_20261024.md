# Xbox 360 Linux guest-memory mapping lifecycle

Date: 2026-10-24

## Change under review

ReXGlue PR [#530](https://github.com/rexglue/rexglue-sdk/pull/530) adds an explicit POSIX unlink-after-open mode for process-local guest memory. The original four-argument `CreateFileMappingHandle` symbol and its named-mapping behavior remain available. `Memory::Initialize` opts into the private mode; an already-open descriptor remains usable for mapping views after its name is removed.

## Verification

- Built the Linux AMD64 Debug `unit_tests` and `rexglue` targets against ReXGlue `main` at v0.10.0.
- `unit_tests "[memory][posix]"`: 2 test cases, 10 assertions passed. One case verifies that the unnamed mapping remains usable; the other verifies that the default named mapping remains discoverable until close.
- `nm -D` confirmed both the original four-argument symbol and the new five-argument overload in the rebuilt runtime.
- A bounded Linux host run with the rebuilt runtime reached title shader-storage initialization and was stopped by an external timeout. One pre-existing orphan under `/dev/shm` remained unchanged; the run created no additional `xenia_memory_*` name.

## Limits

This smoke run does not demonstrate the retail main menu or an offline race. It used an older copied GPU plugin, so its renderer output is not evidence about the current Process 2 build. The change was built and tested on Linux AMD64; Android/ARM64 and Windows builds have not been verified here. No game files or private storage links are part of this evidence or the ReXGlue PR.
