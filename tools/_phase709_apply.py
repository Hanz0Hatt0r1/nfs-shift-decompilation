#!/usr/bin/env python3
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"{path}: expected one replacement, found {count}: {old[:80]!r}"
        )
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


Path("native_runtime/src/runtime_loop_policy.hpp").write_text(
    '''#pragma once

#include <cstddef>
#include <limits>
#include <stdexcept>

namespace shift::runtime {

struct RuntimeLoopPolicy {
    bool continuous = false;
    bool frame_limit_enabled = true;
    int frame_limit = 120;

    bool should_continue(bool quit, int rendered_frames) const {
        if (quit) {
            return false;
        }
        return !frame_limit_enabled || rendered_frames < frame_limit;
    }
};

inline RuntimeLoopPolicy make_runtime_loop_policy(
    bool continuous,
    bool frames_explicit,
    int requested_frames,
    bool input_script_mode,
    std::size_t input_script_steps) {

    if (requested_frames <= 0) {
        throw std::invalid_argument("runtime frame limit must be positive");
    }

    if (input_script_mode) {
        if (continuous) {
            throw std::invalid_argument(
                "--continuous cannot be combined with --input-script");
        }
        if (input_script_steps == 0 ||
            input_script_steps > static_cast<std::size_t>(
                std::numeric_limits<int>::max())) {
            throw std::invalid_argument(
                "native input script has invalid fixed-step cardinality");
        }
        const int script_frames = static_cast<int>(input_script_steps);
        if (frames_explicit && requested_frames != script_frames) {
            throw std::invalid_argument(
                "--frames must equal native input script step count");
        }
        return RuntimeLoopPolicy{false, true, script_frames};
    }

    if (continuous) {
        // An explicit --frames value is an optional regression/safety cap only.
        // Without it, X11 quit/destroy events are the sole normal session end.
        return RuntimeLoopPolicy{
            true,
            frames_explicit,
            requested_frames,
        };
    }

    return RuntimeLoopPolicy{false, true, requested_frames};
}

}  // namespace shift::runtime
''',
    encoding="utf-8",
)

Path("native_runtime/tests/runtime_loop_policy_check.cpp").write_text(
    '''#include "runtime_loop_policy.hpp"

#include <iostream>
#include <stdexcept>

int main() {
    using shift::runtime::make_runtime_loop_policy;

    const auto bounded =
        make_runtime_loop_policy(false, false, 120, false, 0);
    if (bounded.continuous || !bounded.frame_limit_enabled ||
        bounded.frame_limit != 120 ||
        !bounded.should_continue(false, 119) ||
        bounded.should_continue(false, 120)) {
        std::cerr << "bounded loop policy mismatch\\n";
        return 1;
    }

    const auto continuous =
        make_runtime_loop_policy(true, false, 120, false, 0);
    if (!continuous.continuous || continuous.frame_limit_enabled ||
        !continuous.should_continue(false, 0) ||
        !continuous.should_continue(false, 2000000000) ||
        continuous.should_continue(true, 0)) {
        std::cerr << "continuous loop policy mismatch\\n";
        return 1;
    }

    const auto capped =
        make_runtime_loop_policy(true, true, 3, false, 0);
    if (!capped.continuous || !capped.frame_limit_enabled ||
        capped.frame_limit != 3 ||
        !capped.should_continue(false, 2) ||
        capped.should_continue(false, 3)) {
        std::cerr << "continuous safety-cap policy mismatch\\n";
        return 1;
    }

    const auto scripted =
        make_runtime_loop_policy(false, false, 120, true, 5);
    if (scripted.continuous || !scripted.frame_limit_enabled ||
        scripted.frame_limit != 5) {
        std::cerr << "scripted loop policy mismatch\\n";
        return 1;
    }

    bool rejected_continuous_script = false;
    try {
        (void)make_runtime_loop_policy(true, false, 120, true, 5);
    } catch (const std::invalid_argument&) {
        rejected_continuous_script = true;
    }
    if (!rejected_continuous_script) {
        std::cerr << "continuous input script was not rejected\\n";
        return 1;
    }

    bool rejected_script_mismatch = false;
    try {
        (void)make_runtime_loop_policy(false, true, 4, true, 5);
    } catch (const std::invalid_argument&) {
        rejected_script_mismatch = true;
    }
    if (!rejected_script_mismatch) {
        std::cerr << "script/frame mismatch was not rejected\\n";
        return 1;
    }

    std::cout
        << "{\\\"format\\\":\\\"SHIFT.NativeRuntimeLoopPolicyRegression/1\\\","
        << "\\\"bounded\\\":true,\\\"continuous\\\":true,"
        << "\\\"continuous_safety_cap\\\":true,"
        << "\\\"script_fail_closed\\\":true}\\n";
    return 0;
}
''',
    encoding="utf-8",
)

replace_once(
    "native_runtime/src/shift_runtime.cpp",
    '#include "runtime_state.hpp"\n',
    '#include "runtime_state.hpp"\n#include "runtime_loop_policy.hpp"\n',
)
replace_once(
    "native_runtime/src/shift_runtime.cpp",
    "    bool frames_explicit = false;\n    bool persist_post_solve_body_state = false;",
    "    bool frames_explicit = false;\n    bool continuous = false;\n    bool persist_post_solve_body_state = false;",
)
replace_once(
    "native_runtime/src/shift_runtime.cpp",
    '        } else if (option == "--persist-post-solve-body-state") {\n            args.persist_post_solve_body_state = true;',
    '        } else if (option == "--continuous") {\n            args.continuous = true;\n        } else if (option == "--persist-post-solve-body-state") {\n            args.persist_post_solve_body_state = true;',
)
replace_once(
    "native_runtime/src/shift_runtime.cpp",
    '                << "[--input-script FILE] [--frames N] "\n                << "[--validation]\\n";',
    '                << "[--input-script FILE] [--frames N] "\n                << "[--continuous] [--validation]\\n";',
)

old = '''        const bool input_script_mode =
            !args.input_script.empty();
        InputScript input_script{};
        if (input_script_mode) {
            input_script = load_input_script(
                args.input_script);
            if (input_script.steps.size() >
                static_cast<size_t>(
                    std::numeric_limits<int>::max())) {
                throw std::runtime_error(
                    "native input script has too many fixed-step rows");
            }
            if (args.frames_explicit &&
                static_cast<size_t>(args.frames) !=
                    input_script.steps.size()) {
                throw std::runtime_error(
                    "--frames must equal native input script step count");
            }
        }
        const int frame_limit =
            input_script_mode
                ? static_cast<int>(input_script.steps.size())
                : args.frames;
'''
new = '''        const bool input_script_mode =
            !args.input_script.empty();
        InputScript input_script{};
        if (input_script_mode) {
            input_script = load_input_script(
                args.input_script);
        }
        const shift::runtime::RuntimeLoopPolicy loop_policy =
            shift::runtime::make_runtime_loop_policy(
                args.continuous,
                args.frames_explicit,
                args.frames,
                input_script_mode,
                input_script.steps.size());
        const int frame_limit = loop_policy.frame_limit;
'''
replace_once("native_runtime/src/shift_runtime.cpp", old, new)

replace_once(
    "native_runtime/src/shift_runtime.cpp",
    '            << "  \\\"input_script_steps\\\": "\n            << input_script.steps.size() << ",\\n"\n            << "  \\\"solver_frame_mode\\\": "',
    '            << "  \\\"input_script_steps\\\": "\n            << input_script.steps.size() << ",\\n"\n            << "  \\\"continuous_mode\\\": "\n            << (loop_policy.continuous ? "true" : "false") << ",\\n"\n            << "  \\\"frame_limit_enabled\\\": "\n            << (loop_policy.frame_limit_enabled ? "true" : "false") << ",\\n"\n            << "  \\\"runtime_loop_schedule\\\": "\n            << "\\\"one-native-fixed-step-per-render-frame-non-retail\\\",\\n"\n            << "  \\\"solver_frame_mode\\\": "',
)
replace_once(
    "native_runtime/src/shift_runtime.cpp",
    '            << "  \\\"frames_requested\\\": "\n            << frame_limit << "\\n"',
    '            << "  \\\"frames_requested\\\": "\n            << (loop_policy.frame_limit_enabled ? frame_limit : 0) << "\\n"',
)
replace_once(
    "native_runtime/src/shift_runtime.cpp",
    "        while (!quit && rendered < frame_limit) {",
    "        while (loop_policy.should_continue(quit, rendered)) {",
)
replace_once(
    "native_runtime/src/shift_runtime.cpp",
    '            << "  \\\"fixed_dt\\\": "\n            << kFixedDt << ",\\n"\n            << "  \\\"input_layer\\\": "',
    '            << "  \\\"fixed_dt\\\": "\n            << kFixedDt << ",\\n"\n            << "  \\\"continuous_mode\\\": "\n            << (loop_policy.continuous ? "true" : "false") << ",\\n"\n            << "  \\\"frame_limit_enabled\\\": "\n            << (loop_policy.frame_limit_enabled ? "true" : "false") << ",\\n"\n            << "  \\\"runtime_loop_schedule\\\": "\n            << "\\\"one-native-fixed-step-per-render-frame-non-retail\\\",\\n"\n            << "  \\\"input_layer\\\": "',
)

replace_once(
    "native_runtime/CMakeLists.txt",
    "if(BUILD_TESTING)\n  add_test(\n    NAME shift_runtime_builtin_sparse_solver",
    "add_executable(shift_runtime_loop_policy_check\n  tests/runtime_loop_policy_check.cpp)\ntarget_include_directories(shift_runtime_loop_policy_check PRIVATE\n  ${CMAKE_CURRENT_SOURCE_DIR}/src)\ntarget_compile_options(shift_runtime_loop_policy_check PRIVATE\n  -Wall -Wextra -Wpedantic)\n\nif(BUILD_TESTING)\n  add_test(\n    NAME shift_runtime_loop_policy\n    COMMAND shift_runtime_loop_policy_check)\n  add_test(\n    NAME shift_runtime_builtin_sparse_solver",
)

replace_once(
    "tools/run_native_vertical_slice.py",
    "INTERACTIVE_FRAME_LIMIT = 0x7FFFFFFF\n\n",
    "",
)
replace_once(
    "tools/run_native_vertical_slice.py",
    "    if interactive:\n        frames = INTERACTIVE_FRAME_LIMIT\n    else:",
    "    if interactive:\n        frames = None\n    else:",
)
replace_once(
    "tools/run_native_vertical_slice.py",
    '    if input_steps:\n        argv.extend(["--input-script", str(resolved["input_script"])])\n    argv.extend(["--frames", str(frames)])\n    if validation:',
    '    if input_steps:\n        argv.extend(["--input-script", str(resolved["input_script"])])\n    if interactive:\n        argv.append("--continuous")\n    else:\n        argv.extend(["--frames", str(frames)])\n    if validation:',
)
replace_once(
    "tools/run_native_vertical_slice.py",
    '        "frame_limit_policy": (\n            "int32-max-with-window-quit"\n            if interactive\n            else "explicit-bounded-frame-count"\n        ),',
    '        "frame_limit_policy": (\n            "native-continuous-until-window-quit"\n            if interactive\n            else "explicit-bounded-frame-count"\n        ),',
)
replace_once(
    "tools/run_native_vertical_slice.py",
    '            "window_quit_drives_session_end": interactive,\n            "persistent_vehicle_transform_motion_claimed": False,',
    '            "window_quit_drives_session_end": interactive,\n            "native_continuous_runtime_loop_admitted": interactive,\n            "persistent_vehicle_transform_motion_claimed": False,',
)

replace_once(
    "tests/test_run_native_vertical_slice.py",
    '    assert plan["frames"] == MODULE.INTERACTIVE_FRAME_LIMIT\n    assert plan["frame_limit_policy"] == "int32-max-with-window-quit"\n    assert plan["boundary"]["window_quit_drives_session_end"] is True\n    index = plan["argv"].index("--frames")\n    assert plan["argv"][index + 1] == str(MODULE.INTERACTIVE_FRAME_LIMIT)\n',
    '    assert plan["frames"] is None\n    assert plan["frame_limit_policy"] == "native-continuous-until-window-quit"\n    assert plan["boundary"]["window_quit_drives_session_end"] is True\n    assert plan["boundary"]["native_continuous_runtime_loop_admitted"] is True\n    assert "--continuous" in plan["argv"]\n    assert "--frames" not in plan["argv"]\n',
)
replace_once(
    "tests/test_run_native_vertical_slice.py",
    '    assert plan["boundary"]["window_quit_drives_session_end"] is False\n    assert plan["boundary"]["persistent_vehicle_transform_motion_claimed"] is False',
    '    assert plan["boundary"]["window_quit_drives_session_end"] is False\n    assert plan["boundary"]["native_continuous_runtime_loop_admitted"] is False\n    assert plan["boundary"]["persistent_vehicle_transform_motion_claimed"] is False',
)

contract_path = Path("tests/test_native_runtime_contract.py")
contract = contract_path.read_text(encoding="utf-8")
contract += '''\n\n\ndef test_phase709_continuous_runtime_loop_is_explicit_and_non_retail():\n    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")\n    policy = Path("native_runtime/src/runtime_loop_policy.hpp").read_text(encoding="utf-8")\n    cmake = Path("native_runtime/CMakeLists.txt").read_text(encoding="utf-8")\n\n    assert '#include "runtime_loop_policy.hpp"' in source\n    assert 'option == "--continuous"' in source\n    assert "loop_policy.should_continue(quit, rendered)" in source\n    assert "one-native-fixed-step-per-render-frame-non-retail" in source\n    assert "--continuous cannot be combined with --input-script" in policy\n    assert "frame_limit_enabled" in policy\n    assert "shift_runtime_loop_policy_check" in cmake\n    assert "NAME shift_runtime_loop_policy" in cmake\n'''
contract_path.write_text(contract, encoding="utf-8")

replace_once(
    "docs/status/NATIVE_RUNTIME_STATUS.md",
    "7. Replace the bounded frame loop with the native game loop/state machine after render/state contracts stabilize.",
    "7. Phase 709 removes the interactive INT32_MAX surrogate and adds an explicit native continuous-until-window-quit loop policy. Deterministic/scripted runs remain frame-bounded. The current continuous schedule is still one native fixed step per rendered frame and is explicitly non-retail; retail outer-update cadence/game-loop ownership remains evidence-gated.",
)

Path("docs/PHASE709_CONTINUOUS_NATIVE_RUNTIME_LOOP.md").write_text(
    '''# Phase 709 — continuous native runtime loop

## Blocker removed

The first playable Linux vertical slice must stay alive as a real interactive
session while preserving native input, persistent BODY feedback, camera state,
and Vulkan submission across successive ticks. Before Phase 709, the vertical
slice simulated this by passing `--frames 2147483647` to a test-oriented bounded
loop. That was operationally long-lived but it was still a synthetic frame-count
sentinel rather than an explicit runtime execution contract.

Phase 709 replaces that sentinel with a Process 2-owned native loop policy:

```text
interactive keyboard profile
  -> --continuous
  -> X11 input/quit polling
  -> NativeRuntimeState::fixed_step()
  -> persistent BODY feedback scheduler
  -> Vulkan frame
  -> next iteration
  -> terminate only on window/quit event
```

`--frames N` remains the bounded deterministic path. When combined with
`--continuous`, an explicitly supplied `--frames N` is only a regression/safety
cap; the interactive vertical-slice launcher does not supply one.

## Scheduling boundary

This phase does **not** claim retail cadence. The runtime continues to execute
one existing native fixed-step boundary per rendered frame and reports:

```text
one-native-fixed-step-per-render-frame-non-retail
```

The existing `camera_schedule = native-fixed-step-non-retail-timing` remains
unchanged. No equality is asserted between the native fixed step and the retail
outer update. Retail cadence remains owned by Process 1 proof.

## Input and fail-closed behavior

Deterministic `SHIFT.NativeRuntimeInputScript/1` playback is finite by contract,
therefore `--continuous` + `--input-script` is rejected. Script cardinality and
explicit `--frames` must still match exactly.

Interactive keyboard mode now emits `frames: null` and
`frame_limit_policy: native-continuous-until-window-quit`; it passes
`--continuous` and no synthetic frame count.

## Regression / CI

`runtime_loop_policy.hpp` is the concrete policy consumed by
`shift_runtime.cpp`. `shift_runtime_loop_policy_check` covers:

- ordinary bounded execution;
- unbounded continuous execution terminated by quit;
- an explicit continuous safety cap for regression use;
- finite scripted execution;
- fail-closed continuous/script incompatibility;
- fail-closed script/frame cardinality mismatch.

CTest registers `shift_runtime_loop_policy`. Python regressions verify that the
vertical-slice launcher consumes the native continuous mode and that the main
runtime loop retains the explicit non-retail scheduling label.

## Remaining blockers

Phase 709 does not promote any Phase 699/708 external provider: `implement_now`
remains zero. It does not fabricate BODY0 bind semantics, drivetrain mapping,
vehicle pose integration, camera-source/controller semantics, or retail game
loop cadence. The next Process 2 integration should consume the first positive
Process 1 producer/bind/scheduling handoff, or another independent proven
runtime blocker.
''',
    encoding="utf-8",
)

Path(".github/workflows/native-runtime-phase709.yml").write_text(
    '''name: Native runtime Phase 709

on:
  push:
    branches: [main]
    paths:
      - 'native_runtime/src/runtime_loop_policy.hpp'
      - 'native_runtime/src/shift_runtime.cpp'
      - 'native_runtime/tests/runtime_loop_policy_check.cpp'
      - 'native_runtime/CMakeLists.txt'
      - 'tools/run_native_vertical_slice.py'
      - 'tests/test_run_native_vertical_slice.py'
      - 'tests/test_native_runtime_contract.py'
      - 'docs/PHASE709_CONTINUOUS_NATIVE_RUNTIME_LOOP.md'
      - '.github/workflows/native-runtime-phase709.yml'
  pull_request:
    paths:
      - 'native_runtime/src/runtime_loop_policy.hpp'
      - 'native_runtime/src/shift_runtime.cpp'
      - 'native_runtime/tests/runtime_loop_policy_check.cpp'
      - 'native_runtime/CMakeLists.txt'
      - 'tools/run_native_vertical_slice.py'
      - 'tests/test_run_native_vertical_slice.py'
      - 'tests/test_native_runtime_contract.py'
      - 'docs/PHASE709_CONTINUOUS_NATIVE_RUNTIME_LOOP.md'
      - '.github/workflows/native-runtime-phase709.yml'

jobs:
  phase709:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install native build dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake ninja-build g++ pkg-config libvulkan-dev libxcb1-dev glslang-tools
      - name: Configure
        run: cmake -S native_runtime -B native_runtime/build -G Ninja -DBUILD_TESTING=ON
      - name: Build loop regression
        run: cmake --build native_runtime/build --target shift_runtime_loop_policy_check shift_runtime
      - name: CTest loop policy
        run: ctest --test-dir native_runtime/build --output-on-failure -R '^shift_runtime_loop_policy$'
      - name: Python contracts
        run: python3 -m pytest -q tests/test_run_native_vertical_slice.py tests/test_native_runtime_contract.py
''',
    encoding="utf-8",
)

Path(".github/workflows/_process2_phase709_apply.yml").unlink()
Path("tools/_phase709_apply.py").unlink()
