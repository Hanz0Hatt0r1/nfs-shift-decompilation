#include "shift_fun_00770e80_contact_outer_provider_chain.hpp"

#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using namespace shift::runtime::physics;

ContactOuterKernelInput make_valid_contact_outer_input() {
    ContactOuterKernelInput input{};
    input.planar_delta = {10.0, 0.0, 0.0};
    input.previous_distance_state = 8.0;
    input.distance_filter_cap = 1.0;
    input.speed_x = 20.0;
    input.speed_z = 0.0;
    input.surface_scalar = 10.0;
    input.base_scalar = 4.0;
    input.projected_scalar = 1.0;
    input.alignment_scalar = 0.5;
    input.param_3 = 2.0;
    return input;
}

Fun0076d100ContactOuterProvider make_valid_pass_provider(
    std::vector<std::string>& events) {
    return [&](std::size_t pass_index) {
        Fun0076d100ContactOuterProviderCallbacks callbacks{};
        const std::string suffix = ":" + std::to_string(pass_index);
        callbacks.contact_factor = [&events, suffix] {
            events.push_back(std::string(kFun00765c40ContactFactorFunction) + suffix);
        };
        callbacks.wheel_update = [&events, suffix] {
            events.push_back(std::string(kFun00758b50WheelUpdateFunction) + suffix);
        };
        callbacks.contact_response = [&events, suffix] {
            events.push_back(std::string(kFun00766510ContactResponseFunction) + suffix);
        };
        callbacks.contact_outer_input_provider = [&events, suffix] {
            events.push_back("FUN_007675f0-provider" + suffix);
            return make_valid_contact_outer_input();
        };
        callbacks.motion_read_gate = [&events, suffix] {
            events.push_back(std::string(kFun007682c0MotionReadGateFunction) + suffix);
        };
        return callbacks;
    };
}

}  // namespace

int main() {
    try {
        std::vector<std::uint8_t> body_bytes(kBodyRecordSize, 0u);

        // A valid typed FUN_007675f0 input must execute the native Phase 662
        // kernel at the proven anchor position before the half-step provider.
        std::vector<std::string> events;
        bool stopped_after_pass = false;
        try {
            (void)execute_fun_00770e80_contact_outer_provider_chain(
                0.5,
                body_bytes,
                make_valid_pass_provider(events),
                [&](std::size_t pass_index,
                    double,
                    const std::vector<std::uint8_t>&) ->
                    Fun00765470MachineScalarHalfStepInput {
                    events.push_back("half-step-provider:" + std::to_string(pass_index));
                    throw std::runtime_error("phase693-stop-after-pass");
                },
                [](std::size_t) {});
        } catch (const std::runtime_error& exc) {
            stopped_after_pass =
                std::string(exc.what()) == "phase693-stop-after-pass";
        }
        const std::vector<std::string> expected_events = {
            "FUN_00765c40:0",
            "FUN_00758b50:0",
            "FUN_00766510:0",
            "FUN_007675f0-provider:0",
            "FUN_007682c0:0",
            "half-step-provider:0",
        };
        if (!stopped_after_pass || events != expected_events) {
            throw std::runtime_error(
                "Phase 693 typed FUN_007675f0 anchor ordering mismatch");
        }

        // A typed provider value invalid under the already-native Phase 662
        // contract must fail at FUN_007675f0 before the following tail anchor or
        // half-step provider can execute. This proves the adapter does not keep
        // an arbitrary no-op callback in place of the recovered native kernel.
        events.clear();
        bool native_kernel_rejected = false;
        try {
            (void)execute_fun_00770e80_contact_outer_provider_chain(
                0.5,
                body_bytes,
                [&](std::size_t pass_index) {
                    auto callbacks = make_valid_pass_provider(events)(pass_index);
                    callbacks.contact_outer_input_provider = [&events, pass_index] {
                        events.push_back(
                            "FUN_007675f0-provider:" + std::to_string(pass_index));
                        ContactOuterKernelInput input{};
                        input.planar_delta = {0.0, 0.0, 0.0};
                        return input;
                    };
                    return callbacks;
                },
                [&](std::size_t,
                    double,
                    const std::vector<std::uint8_t>&) ->
                    Fun00765470MachineScalarHalfStepInput {
                    events.push_back("unexpected-half-step");
                    throw std::runtime_error("unexpected half-step");
                },
                [](std::size_t) {});
        } catch (const std::invalid_argument& exc) {
            native_kernel_rejected =
                std::string(exc.what()).find("zero X/Z delta") != std::string::npos;
        }
        const std::vector<std::string> expected_rejected_events = {
            "FUN_00765c40:0",
            "FUN_00758b50:0",
            "FUN_00766510:0",
            "FUN_007675f0-provider:0",
        };
        if (!native_kernel_rejected || events != expected_rejected_events) {
            throw std::runtime_error(
                "Phase 693 native FUN_007675f0 failure did not stop the chain");
        }

        // Missing typed input provider is rejected when the pass bundle is
        // admitted, before any of its anchor callbacks execute.
        events.clear();
        bool missing_provider_rejected = false;
        try {
            (void)execute_fun_00770e80_contact_outer_provider_chain(
                0.5,
                body_bytes,
                [&](std::size_t pass_index) {
                    auto callbacks = make_valid_pass_provider(events)(pass_index);
                    callbacks.contact_outer_input_provider = {};
                    return callbacks;
                },
                [&](std::size_t,
                    double,
                    const std::vector<std::uint8_t>&) ->
                    Fun00765470MachineScalarHalfStepInput {
                    throw std::runtime_error("unexpected half-step");
                },
                [](std::size_t) {});
        } catch (const std::invalid_argument&) {
            missing_provider_rejected = true;
        }
        if (!missing_provider_rejected || !events.empty()) {
            throw std::runtime_error(
                "Phase 693 missing typed contact-outer provider failed open");
        }

        bool missing_pass_provider_rejected = false;
        try {
            (void)execute_fun_00770e80_contact_outer_provider_chain(
                0.5,
                body_bytes,
                {},
                [](std::size_t,
                    double,
                    const std::vector<std::uint8_t>&) {
                    return Fun00765470MachineScalarHalfStepInput{};
                },
                [](std::size_t) {});
        } catch (const std::invalid_argument&) {
            missing_pass_provider_rejected = true;
        }
        if (!missing_pass_provider_rejected) {
            throw std::runtime_error(
                "Phase 693 missing physics-pass provider accepted");
        }

        std::cout
            << "{\"format\":\""
            << kNativeFun00770e80ContactOuterProviderChainFormat << "\","
            << "\"ready\":true,"
            << "\"phase691_scalar_provider_outer_chain_reused\":true,"
            << "\"fun_007675f0_typed_input_provider\":true,"
            << "\"fun_007675f0_native_kernel_internal\":true,"
            << "\"fun_007675f0_arbitrary_callback_external\":false,"
            << "\"fun_007675f0_input_production_external\":true,"
            << "\"machine_scalar_production_external\":true,"
            << "\"fixed_step_auto_schedule\":false,"
            << "\"complete_fun_007675f0_semantics\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
