#include "shift_fun_00770e80_scalar_provider_anchor_chain.hpp"

#include <memory>
#include <stdexcept>

namespace shift::runtime::physics {
namespace {

struct ScalarPassState {
    std::size_t expected_body_count = 0u;
    std::size_t next_body_index = 0u;
    std::size_t provider_call_count = 0u;
    std::size_t applied_rotation_count = 0u;
    std::size_t zero_noop_count = 0u;
};

}  // namespace

Fun00770e80ScalarProviderAnchorChainResult
execute_fun_00770e80_scalar_provider_anchor_chain(
    double outer_timestep,
    const std::vector<std::uint8_t>& initial_body_bytes,
    const Fun0076d100AnchorProvider& physics_pass_provider,
    const Fun00765470MachineScalarHalfStepProvider& half_step_provider,
    const Fun007b8810PostHalfStepCallback& post_half_step,
    const Fun0076d100PostAnchorBodyStateMutator& post_anchor_body_mutator) {
    if (!half_step_provider) {
        throw std::invalid_argument(
            "FUN_00770e80 scalar-provider chain requires half-step provider");
    }

    Fun00770e80ScalarProviderAnchorChainResult result{};
    std::array<std::shared_ptr<ScalarPassState>, kFun00770e80PassCount> states{};

    result.joined = execute_fun_00770e80_composed_anchor_chain(
        outer_timestep,
        initial_body_bytes,
        physics_pass_provider,
        [&](std::size_t pass_index,
            double half_timestep,
            const std::vector<std::uint8_t>& current_body_bytes) {
            if (pass_index >= kFun00770e80PassCount) {
                throw std::runtime_error(
                    "FUN_00770e80 scalar-provider pass index exceeds proven domain");
            }
            if (current_body_bytes.empty() ||
                current_body_bytes.size() % kBodyRecordSize != 0u) {
                throw std::invalid_argument(
                    "FUN_00770e80 scalar-provider chain requires exact BODY records");
            }

            const auto typed = half_step_provider(
                pass_index,
                half_timestep,
                current_body_bytes);
            if (!typed.scalar_provider) {
                throw std::invalid_argument(
                    "FUN_00770e80 scalar-provider half-step requires FUN_007afdd0 scalars");
            }

            auto state = std::make_shared<ScalarPassState>();
            state->expected_body_count = current_body_bytes.size() / kBodyRecordSize;
            states[pass_index] = state;

            const auto scalar_provider = typed.scalar_provider;
            BodyBasisRotationCallback basis_rotation =
                [state, scalar_provider](
                    const ConstraintRefreshFrame3f& basis,
                    const BodyFrameIntegrationVector3d& rotation_increment) {
                    if (state->next_body_index >= state->expected_body_count) {
                        throw std::logic_error(
                            "FUN_007afdd0 scalar provider exceeded BODY domain");
                    }
                    const std::size_t body_index = state->next_body_index;
                    const auto scalars = scalar_provider(
                        body_index,
                        basis,
                        rotation_increment);
                    const auto core = execute_fun_007afdd0_source_core(
                        basis,
                        rotation_increment,
                        scalars);
                    ++state->next_body_index;
                    ++state->provider_call_count;
                    if (core.applied) {
                        ++state->applied_rotation_count;
                    } else {
                        ++state->zero_noop_count;
                    }
                    return core.basis;
                };

            Fun00765470MachineHalfStepInput adapted{};
            adapted.machine = typed.machine;
            adapted.source = typed.source;
            adapted.relations = typed.relations;
            adapted.reset_state = typed.reset_state;
            adapted.solver_topology = typed.solver_topology;
            adapted.projection = typed.projection;
            adapted.basis_rotation = std::move(basis_rotation);
            adapted.tolerance = typed.tolerance;
            return adapted;
        },
        post_half_step,
        post_anchor_body_mutator);

    for (std::size_t pass_index = 0u;
         pass_index < kFun00770e80PassCount;
         ++pass_index) {
        const auto& state = states[pass_index];
        if (!state ||
            state->next_body_index != state->expected_body_count ||
            state->provider_call_count != state->expected_body_count) {
            throw std::logic_error(
                "FUN_007afdd0 scalar-provider BODY iteration count mismatch");
        }
        result.scalar_provider_call_counts[pass_index] = state->provider_call_count;
        result.applied_rotation_counts[pass_index] = state->applied_rotation_count;
        result.zero_noop_counts[pass_index] = state->zero_noop_count;
        result.scalar_provider_call_count += state->provider_call_count;
        result.applied_rotation_count += state->applied_rotation_count;
        result.zero_noop_count += state->zero_noop_count;
    }

    return result;
}

}  // namespace shift::runtime::physics
