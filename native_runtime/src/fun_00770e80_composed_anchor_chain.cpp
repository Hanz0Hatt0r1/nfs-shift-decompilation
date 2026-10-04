#include "shift_fun_00770e80_composed_anchor_chain.hpp"

#include <stdexcept>
#include <utility>

namespace shift::runtime::physics {

Fun00770e80ComposedAnchorChainResult execute_fun_00770e80_composed_anchor_chain(
    double outer_timestep,
    const std::vector<std::uint8_t>& initial_body_bytes,
    const Fun0076d100AnchorProvider& physics_pass_provider,
    const Fun00765470MachineHalfStepProvider& half_step_provider,
    const Fun007b8810PostHalfStepCallback& post_half_step,
    const Fun0076d100PostAnchorBodyStateMutator& post_anchor_body_mutator) {

    if (!physics_pass_provider) {
        throw std::invalid_argument(
            "FUN_00770e80 composed chain requires physics-pass provider");
    }
    if (!half_step_provider) {
        throw std::invalid_argument(
            "FUN_00770e80 composed chain requires half-step provider");
    }
    if (!post_half_step) {
        throw std::invalid_argument(
            "FUN_00770e80 composed chain requires FUN_007b8810 callback");
    }

    Fun00770e80ComposedAnchorChainResult result{};
    result.final_body_bytes = initial_body_bytes;

    result.schedule = execute_fun_00770e80_two_half_step_schedule(
        outer_timestep,
        [&](std::size_t pass_index) {
            if (pass_index >= kFun00770e80PassCount) {
                throw std::runtime_error(
                    "FUN_00770e80 physics-pass index exceeds proven domain");
            }
            const auto callbacks = physics_pass_provider(pass_index);
            ++result.physics_pass_provider_call_count;
            result.physics_passes[pass_index] =
                execute_fun_0076d100_required_anchor_sequence(
                    callbacks.contact_factor,
                    callbacks.wheel_update,
                    callbacks.contact_response,
                    callbacks.contact_outer,
                    callbacks.motion_read_gate);

            if (post_anchor_body_mutator) {
                post_anchor_body_mutator(
                    pass_index,
                    result.final_body_bytes);
            }
        },
        [&](std::size_t pass_index, double half_timestep) {
            if (pass_index >= kFun00770e80PassCount) {
                throw std::runtime_error(
                    "FUN_00770e80 half-step index exceeds proven domain");
            }

            const auto input = half_step_provider(
                pass_index,
                half_timestep,
                result.final_body_bytes);
            ++result.half_step_provider_call_count;

            result.half_steps[pass_index] =
                execute_fun_00765470_machine_longitudinal_feedback_join(
                    [&] { return input.machine; },
                    input.source,
                    input.relations,
                    input.reset_state,
                    input.solver_topology,
                    input.projection,
                    result.final_body_bytes,
                    half_timestep,
                    input.basis_rotation,
                    input.tolerance);

            result.final_body_bytes =
                result.half_steps[pass_index]
                    .joined.half_step.feedback_integration.body_bytes;
        },
        post_half_step);

    if (result.physics_pass_provider_call_count != kFun00770e80PassCount ||
        result.half_step_provider_call_count != kFun00770e80PassCount) {
        throw std::runtime_error(
            "FUN_00770e80 composed chain provider cardinality mismatch");
    }

    return result;
}

}  // namespace shift::runtime::physics
