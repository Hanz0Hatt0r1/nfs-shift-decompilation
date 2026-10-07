#include "shift_fun_00770e80_motion_read_machine_input_provider_chain.hpp"

#include "shift_body_record_adapter.hpp"

#include <memory>
#include <stdexcept>
#include <utility>

namespace shift::runtime::physics {
namespace {

struct MotionReadMachinePassState {
    std::size_t input_provider_call_count = 0u;
    std::size_t native_effect_call_count = 0u;
    std::size_t delta_application_call_count = 0u;
    bool input_present = false;
    bool result_present = false;
    Fun007682c0MachineInput input{};
    Fun007682c0MachineEffectResult result{};
};

void require_complete_pass_callbacks(
    const Fun0076d100MotionReadMachineInputProviderCallbacks& callbacks) {
    if (!callbacks.contact_factor ||
        !callbacks.wheel_update ||
        !callbacks.contact_response ||
        !callbacks.contact_outer_input_provider ||
        !callbacks.motion_read_input_provider) {
        throw std::invalid_argument(
            "FUN_00770e80 motion-read machine-input chain requires all active physics-pass providers");
    }
}

}  // namespace

Fun00770e80MotionReadMachineInputProviderChainResult
execute_fun_00770e80_motion_read_machine_input_provider_chain(
    double outer_timestep,
    const std::vector<std::uint8_t>& initial_body_bytes,
    const Fun0076d100MotionReadMachineInputProvider& physics_pass_provider,
    const Fun00765470MachineScalarHalfStepProvider& half_step_provider,
    const Fun007b8810PostHalfStepCallback& post_half_step) {
    if (!physics_pass_provider) {
        throw std::invalid_argument(
            "FUN_00770e80 motion-read machine-input chain requires physics-pass provider");
    }

    Fun00770e80MotionReadMachineInputProviderChainResult result{};
    std::array<std::shared_ptr<MotionReadMachinePassState>, kFun00770e80PassCount>
        states{};

    result.joined = execute_fun_00770e80_contact_outer_provider_chain(
        outer_timestep,
        initial_body_bytes,
        [&](std::size_t pass_index) {
            if (pass_index >= kFun00770e80PassCount) {
                throw std::logic_error(
                    "FUN_00770e80 motion-read machine-input pass index exceeds proven domain");
            }
            if (states[pass_index]) {
                throw std::logic_error(
                    "FUN_00770e80 motion-read machine-input provider invoked twice for one pass");
            }

            auto typed = physics_pass_provider(pass_index);
            require_complete_pass_callbacks(typed);

            auto state = std::make_shared<MotionReadMachinePassState>();
            states[pass_index] = state;

            Fun0076d100ContactOuterProviderCallbacks adapted{};
            adapted.contact_factor = std::move(typed.contact_factor);
            adapted.wheel_update = std::move(typed.wheel_update);
            adapted.contact_response = std::move(typed.contact_response);
            adapted.contact_outer_input_provider =
                std::move(typed.contact_outer_input_provider);
            adapted.contact_outer_distance_state_commit =
                std::move(typed.contact_outer_distance_state_commit);

            auto input_provider = std::move(typed.motion_read_input_provider);
            adapted.motion_read_gate =
                [state, input_provider = std::move(input_provider)]() mutable {
                    ++state->input_provider_call_count;
                    state->input = input_provider();
                    state->input_present = true;
                };

            adapted.post_pass_body_mutator =
                [state](std::vector<std::uint8_t>& current_body_bytes) {
                    if (!state->input_present) {
                        throw std::logic_error(
                            "FUN_007682c0 machine effect executed before raw retail inputs");
                    }
                    state->result = execute_fun_007682c0_machine_effect(
                        state->input,
                        current_body_bytes);
                    ++state->native_effect_call_count;
                    state->result_present = true;

                    if (state->result.effect.gate_open) {
                        apply_fun_007682c0_body0_accumulator_y_delta(
                            current_body_bytes,
                            state->result.effect.accumulator_y_delta);
                        ++state->delta_application_call_count;
                    }
                };
            return adapted;
        },
        half_step_provider,
        post_half_step);

    for (std::size_t pass_index = 0u;
         pass_index < kFun00770e80PassCount;
         ++pass_index) {
        const auto& state = states[pass_index];
        if (!state ||
            state->input_provider_call_count != 1u ||
            !state->input_present ||
            state->native_effect_call_count != 1u ||
            !state->result_present) {
            throw std::logic_error(
                "FUN_007682c0 machine-input/native-effect cardinality mismatch");
        }
        const std::size_t expected_applications =
            state->result.effect.gate_open ? 1u : 0u;
        if (state->delta_application_call_count != expected_applications) {
            throw std::logic_error(
                "FUN_007682c0 native effect BODY0 application cardinality mismatch");
        }

        result.motion_read_inputs[pass_index] = state->input;
        result.motion_read_results[pass_index] = state->result;
        result.motion_read_input_present[pass_index] = true;
        result.motion_read_result_present[pass_index] = true;
        result.motion_read_input_provider_call_counts[pass_index] =
            state->input_provider_call_count;
        result.motion_read_native_effect_call_counts[pass_index] =
            state->native_effect_call_count;
        result.motion_read_delta_application_call_counts[pass_index] =
            state->delta_application_call_count;
        result.motion_read_input_provider_call_count +=
            state->input_provider_call_count;
        result.motion_read_native_effect_call_count +=
            state->native_effect_call_count;
        result.motion_read_delta_application_call_count +=
            state->delta_application_call_count;
        if (state->result.effect.gate_open) {
            ++result.motion_read_gate_open_count;
        }
    }

    return result;
}

}  // namespace shift::runtime::physics
