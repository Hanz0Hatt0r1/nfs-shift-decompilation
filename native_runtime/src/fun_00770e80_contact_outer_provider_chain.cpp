#include "shift_fun_00770e80_contact_outer_provider_chain.hpp"

#include <memory>
#include <stdexcept>
#include <utility>

namespace shift::runtime::physics {
namespace {

struct ContactOuterPassState {
    std::size_t input_provider_call_count = 0u;
    std::size_t native_call_count = 0u;
    bool result_present = false;
    ContactOuterKernelResult result{};
};

void require_complete_pass_callbacks(
    const Fun0076d100ContactOuterProviderCallbacks& callbacks) {
    if (!callbacks.contact_factor ||
        !callbacks.wheel_update ||
        !callbacks.contact_response ||
        !callbacks.contact_outer_input_provider ||
        !callbacks.motion_read_gate) {
        throw std::invalid_argument(
            "FUN_00770e80 contact-outer provider chain requires all physics-pass boundaries");
    }
}

}  // namespace

Fun00770e80ContactOuterProviderChainResult
execute_fun_00770e80_contact_outer_provider_chain(
    double outer_timestep,
    const std::vector<std::uint8_t>& initial_body_bytes,
    const Fun0076d100ContactOuterProvider& physics_pass_provider,
    const Fun00765470MachineScalarHalfStepProvider& half_step_provider,
    const Fun007b8810PostHalfStepCallback& post_half_step,
    const Fun0076d100PostAnchorBodyStateMutator& post_anchor_body_mutator) {
    if (!physics_pass_provider) {
        throw std::invalid_argument(
            "FUN_00770e80 contact-outer provider chain requires physics-pass provider");
    }

    Fun00770e80ContactOuterProviderChainResult result{};
    std::array<std::shared_ptr<ContactOuterPassState>, kFun00770e80PassCount> states{};

    result.joined = execute_fun_00770e80_scalar_provider_anchor_chain(
        outer_timestep,
        initial_body_bytes,
        [&](std::size_t pass_index) {
            if (pass_index >= kFun00770e80PassCount) {
                throw std::logic_error(
                    "FUN_00770e80 contact-outer pass index exceeds proven domain");
            }
            if (states[pass_index]) {
                throw std::logic_error(
                    "FUN_00770e80 contact-outer provider invoked twice for one pass");
            }

            auto typed = physics_pass_provider(pass_index);
            require_complete_pass_callbacks(typed);

            auto state = std::make_shared<ContactOuterPassState>();
            states[pass_index] = state;

            Fun0076d100AnchorCallbacks adapted{};
            adapted.contact_factor = std::move(typed.contact_factor);
            adapted.wheel_update = std::move(typed.wheel_update);
            adapted.contact_response = std::move(typed.contact_response);
            adapted.motion_read_gate = std::move(typed.motion_read_gate);

            auto contact_outer_input_provider =
                std::move(typed.contact_outer_input_provider);
            adapted.contact_outer =
                [state, contact_outer_input_provider =
                    std::move(contact_outer_input_provider)]() mutable {
                    ++state->input_provider_call_count;
                    const ContactOuterKernelInput input =
                        contact_outer_input_provider();
                    state->result =
                        execute_fun_007675f0_outer_arithmetic(input);
                    ++state->native_call_count;
                    state->result_present = true;
                };
            return adapted;
        },
        half_step_provider,
        post_half_step,
        post_anchor_body_mutator);

    for (std::size_t pass_index = 0u;
         pass_index < kFun00770e80PassCount;
         ++pass_index) {
        const auto& state = states[pass_index];
        if (!state ||
            state->input_provider_call_count != 1u ||
            state->native_call_count != 1u ||
            !state->result_present) {
            throw std::logic_error(
                "FUN_007675f0 typed provider/native execution cardinality mismatch");
        }
        result.contact_outer_results[pass_index] = state->result;
        result.contact_outer_result_present[pass_index] = true;
        result.contact_outer_input_provider_call_counts[pass_index] =
            state->input_provider_call_count;
        result.contact_outer_native_call_counts[pass_index] =
            state->native_call_count;
        result.contact_outer_input_provider_call_count +=
            state->input_provider_call_count;
        result.contact_outer_native_call_count += state->native_call_count;
        if (state->result.gate_open) {
            ++result.contact_outer_gate_open_count;
        }
    }

    return result;
}

}  // namespace shift::runtime::physics
