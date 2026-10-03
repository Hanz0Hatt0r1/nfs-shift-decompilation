#include "shift_fun_00770e80_motion_read_effect_provider_chain.hpp"

#include <cstdint>
#include <iostream>
#include <limits>
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

Fun0076d100MotionReadEffectProvider make_valid_pass_provider(
    std::vector<std::string>& events,
    std::vector<double>& consumed,
    bool gate_open = true,
    double delta = -2.5) {
    return [&](std::size_t pass_index) {
        Fun0076d100MotionReadEffectProviderCallbacks callbacks{};
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
        callbacks.motion_read_effect_provider =
            [&events, suffix, gate_open, delta] {
                events.push_back("FUN_007682c0-effect-provider" + suffix);
                return Fun007682c0AccumulatorEffect{gate_open, gate_open ? delta : 0.0};
            };
        callbacks.motion_read_delta_consumer =
            [&events, &consumed, suffix](double value) {
                events.push_back("FUN_007682c0-delta-consumer" + suffix);
                consumed.push_back(value);
            };
        return callbacks;
    };
}

}  // namespace

int main() {
    try {
        std::vector<std::uint8_t> body_bytes(kBodyRecordSize, 0u);

        // The previous arbitrary FUN_007682c0 callback is now an adapter that
        // obtains one typed effect and forwards only the proven +0x50 delta to
        // a typed consumer before the half-step provider can execute.
        std::vector<std::string> events;
        std::vector<double> consumed;
        bool stopped_after_pass = false;
        try {
            (void)execute_fun_00770e80_motion_read_effect_provider_chain(
                0.5,
                body_bytes,
                make_valid_pass_provider(events, consumed),
                [&](std::size_t pass_index,
                    double,
                    const std::vector<std::uint8_t>&) ->
                    Fun00765470MachineScalarHalfStepInput {
                    events.push_back("half-step-provider:" + std::to_string(pass_index));
                    throw std::runtime_error("phase696-stop-after-pass");
                },
                [](std::size_t) {});
        } catch (const std::runtime_error& exc) {
            stopped_after_pass =
                std::string(exc.what()) == "phase696-stop-after-pass";
        }
        const std::vector<std::string> expected_events = {
            "FUN_00765c40:0",
            "FUN_00758b50:0",
            "FUN_00766510:0",
            "FUN_007675f0-provider:0",
            "FUN_007682c0-effect-provider:0",
            "FUN_007682c0-delta-consumer:0",
            "half-step-provider:0",
        };
        if (!stopped_after_pass || events != expected_events ||
            consumed != std::vector<double>{-2.5}) {
            throw std::runtime_error(
                "Phase 696 typed FUN_007682c0 anchor ordering mismatch");
        }

        // A closed source gate has no accumulator application side effect.
        events.clear();
        consumed.clear();
        stopped_after_pass = false;
        try {
            (void)execute_fun_00770e80_motion_read_effect_provider_chain(
                0.5,
                body_bytes,
                make_valid_pass_provider(events, consumed, false, 0.0),
                [&](std::size_t pass_index,
                    double,
                    const std::vector<std::uint8_t>&) ->
                    Fun00765470MachineScalarHalfStepInput {
                    events.push_back("half-step-provider:" + std::to_string(pass_index));
                    throw std::runtime_error("phase696-stop-after-pass");
                },
                [](std::size_t) {});
        } catch (const std::runtime_error& exc) {
            stopped_after_pass =
                std::string(exc.what()) == "phase696-stop-after-pass";
        }
        const std::vector<std::string> expected_closed_events = {
            "FUN_00765c40:0",
            "FUN_00758b50:0",
            "FUN_00766510:0",
            "FUN_007675f0-provider:0",
            "FUN_007682c0-effect-provider:0",
            "half-step-provider:0",
        };
        if (!stopped_after_pass || events != expected_closed_events ||
            !consumed.empty()) {
            throw std::runtime_error(
                "Phase 696 closed FUN_007682c0 gate produced a side effect");
        }

        // Invalid typed effects fail before the delta consumer and before the
        // following half-step boundary.
        events.clear();
        consumed.clear();
        bool closed_nonzero_rejected = false;
        try {
            (void)execute_fun_00770e80_motion_read_effect_provider_chain(
                0.5,
                body_bytes,
                [&](std::size_t pass_index) {
                    auto callbacks =
                        make_valid_pass_provider(events, consumed)(pass_index);
                    callbacks.motion_read_effect_provider = [&events, pass_index] {
                        events.push_back(
                            "FUN_007682c0-effect-provider:" + std::to_string(pass_index));
                        return Fun007682c0AccumulatorEffect{false, 1.0};
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
            closed_nonzero_rejected =
                std::string(exc.what()).find("closed gate") != std::string::npos;
        }
        if (!closed_nonzero_rejected || !consumed.empty() ||
            (!events.empty() && events.back() == "unexpected-half-step")) {
            throw std::runtime_error(
                "Phase 696 invalid closed-gate effect failed open");
        }

        events.clear();
        consumed.clear();
        bool nonfinite_rejected = false;
        try {
            (void)execute_fun_00770e80_motion_read_effect_provider_chain(
                0.5,
                body_bytes,
                [&](std::size_t pass_index) {
                    auto callbacks =
                        make_valid_pass_provider(events, consumed)(pass_index);
                    callbacks.motion_read_effect_provider = [&events, pass_index] {
                        events.push_back(
                            "FUN_007682c0-effect-provider:" + std::to_string(pass_index));
                        return Fun007682c0AccumulatorEffect{
                            true,
                            std::numeric_limits<double>::quiet_NaN()};
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
            nonfinite_rejected =
                std::string(exc.what()).find("non-finite") != std::string::npos;
        }
        if (!nonfinite_rejected || !consumed.empty()) {
            throw std::runtime_error(
                "Phase 696 non-finite FUN_007682c0 effect failed open");
        }

        // Missing typed boundaries are rejected when the pass bundle is
        // admitted, before any Phase 684 callback side effect occurs.
        events.clear();
        consumed.clear();
        bool missing_effect_provider_rejected = false;
        try {
            (void)execute_fun_00770e80_motion_read_effect_provider_chain(
                0.5,
                body_bytes,
                [&](std::size_t pass_index) {
                    auto callbacks =
                        make_valid_pass_provider(events, consumed)(pass_index);
                    callbacks.motion_read_effect_provider = {};
                    return callbacks;
                },
                [&](std::size_t,
                    double,
                    const std::vector<std::uint8_t>&) {
                    return Fun00765470MachineScalarHalfStepInput{};
                },
                [](std::size_t) {});
        } catch (const std::invalid_argument&) {
            missing_effect_provider_rejected = true;
        }
        if (!missing_effect_provider_rejected || !events.empty()) {
            throw std::runtime_error(
                "Phase 696 missing FUN_007682c0 effect provider failed open");
        }

        bool missing_delta_consumer_rejected = false;
        try {
            (void)execute_fun_00770e80_motion_read_effect_provider_chain(
                0.5,
                body_bytes,
                [&](std::size_t pass_index) {
                    auto callbacks =
                        make_valid_pass_provider(events, consumed)(pass_index);
                    callbacks.motion_read_delta_consumer = {};
                    return callbacks;
                },
                [&](std::size_t,
                    double,
                    const std::vector<std::uint8_t>&) {
                    return Fun00765470MachineScalarHalfStepInput{};
                },
                [](std::size_t) {});
        } catch (const std::invalid_argument&) {
            missing_delta_consumer_rejected = true;
        }
        if (!missing_delta_consumer_rejected || !events.empty()) {
            throw std::runtime_error(
                "Phase 696 missing FUN_007682c0 delta consumer failed open");
        }

        std::cout
            << "{\"format\":\""
            << kNativeFun00770e80MotionReadEffectProviderChainFormat << "\","
            << "\"ready\":true,"
            << "\"phase693_contact_outer_provider_chain_reused\":true,"
            << "\"fun_007682c0_typed_effect_provider\":true,"
            << "\"fun_007682c0_typed_accumulator_delta_consumer\":true,"
            << "\"fun_007682c0_arbitrary_callback_external\":false,"
            << "\"fun_007682c0_effect_production_external\":true,"
            << "\"fun_007682c0_body_identity_application_external\":true,"
            << "\"fun_007682c0_machine_scalar_production_external\":true,"
            << "\"host_sqrt_substitution_allowed\":false,"
            << "\"fixed_step_auto_schedule\":false,"
            << "\"complete_fun_007682c0_semantics\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
