#include "runtime_loop_policy.hpp"

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
        std::cerr << "bounded loop policy mismatch\n";
        return 1;
    }

    const auto continuous =
        make_runtime_loop_policy(true, false, 120, false, 0);
    if (!continuous.continuous || continuous.frame_limit_enabled ||
        !continuous.should_continue(false, 0) ||
        !continuous.should_continue(false, 2000000000) ||
        continuous.should_continue(true, 0)) {
        std::cerr << "continuous loop policy mismatch\n";
        return 1;
    }

    const auto capped =
        make_runtime_loop_policy(true, true, 3, false, 0);
    if (!capped.continuous || !capped.frame_limit_enabled ||
        capped.frame_limit != 3 ||
        !capped.should_continue(false, 2) ||
        capped.should_continue(false, 3)) {
        std::cerr << "continuous safety-cap policy mismatch\n";
        return 1;
    }

    const auto scripted =
        make_runtime_loop_policy(false, false, 120, true, 5);
    if (scripted.continuous || !scripted.frame_limit_enabled ||
        scripted.frame_limit != 5) {
        std::cerr << "scripted loop policy mismatch\n";
        return 1;
    }

    bool rejected_continuous_script = false;
    try {
        (void)make_runtime_loop_policy(true, false, 120, true, 5);
    } catch (const std::invalid_argument&) {
        rejected_continuous_script = true;
    }
    if (!rejected_continuous_script) {
        std::cerr << "continuous input script was not rejected\n";
        return 1;
    }

    bool rejected_script_mismatch = false;
    try {
        (void)make_runtime_loop_policy(false, true, 4, true, 5);
    } catch (const std::invalid_argument&) {
        rejected_script_mismatch = true;
    }
    if (!rejected_script_mismatch) {
        std::cerr << "script/frame mismatch was not rejected\n";
        return 1;
    }

    std::cout
        << "{\"format\":\"SHIFT.NativeRuntimeLoopPolicyRegression/1\","
        << "\"bounded\":true,\"continuous\":true,"
        << "\"continuous_safety_cap\":true,"
        << "\"script_fail_closed\":true}\n";
    return 0;
}
