#pragma once

#include "shift_fun_00770e80_composed_anchor_chain.hpp"
#include "shift_fun_00770e80_scalar_provider_anchor_chain.hpp"

#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <vector>

namespace shift::runtime {

inline constexpr const char* kNativeExplicitOuterUpdateRuntimeStateFormat =
    "SHIFT.NativeExplicitOuterUpdateRuntimeState/1";

struct ExplicitOuterUpdateRuntimeState {
    bool initialized = false;
    std::uint64_t explicit_update_count = 0u;
    std::uint32_t body_count = 0u;
    std::size_t body_byte_count = 0u;
    double last_outer_timestep = 0.0;
    std::size_t last_physics_pass_provider_call_count = 0u;
    std::size_t last_half_step_provider_call_count = 0u;
    std::size_t last_scalar_provider_call_count = 0u;
    std::size_t last_applied_rotation_count = 0u;
    std::size_t last_zero_noop_count = 0u;
    std::vector<std::uint8_t> body_bytes;

    void initialize_body_state(
        const std::vector<std::uint8_t>& initial_body_bytes,
        std::uint32_t runtime_body_count,
        bool workspace_ready) {
        if (!workspace_ready) {
            throw std::runtime_error(
                "explicit outer update requires ready physics workspace");
        }
        if (runtime_body_count == 0u) {
            throw std::invalid_argument(
                "explicit outer update requires non-zero BODY count");
        }
        const std::size_t expected_bytes =
            static_cast<std::size_t>(runtime_body_count) *
            physics::kBodyRecordSize;
        if (initial_body_bytes.size() != expected_bytes) {
            throw std::invalid_argument(
                "explicit outer update BODY byte cardinality mismatch");
        }

        initialized = true;
        explicit_update_count = 0u;
        body_count = runtime_body_count;
        body_byte_count = expected_bytes;
        last_outer_timestep = 0.0;
        last_physics_pass_provider_call_count = 0u;
        last_half_step_provider_call_count = 0u;
        last_scalar_provider_call_count = 0u;
        last_applied_rotation_count = 0u;
        last_zero_noop_count = 0u;
        body_bytes = initial_body_bytes;
    }

    void validate_runtime_boundary(
        std::uint32_t runtime_body_count,
        bool workspace_ready,
        bool participant_ready,
        bool participant_identity_join_proven) const {
        if (!initialized) {
            throw std::runtime_error(
                "explicit outer update BODY state is not initialized");
        }
        if (!workspace_ready) {
            throw std::runtime_error(
                "explicit outer update requires ready physics workspace");
        }
        if (!participant_ready || !participant_identity_join_proven) {
            throw std::runtime_error(
                "explicit outer update requires ready participant identity");
        }
        if (runtime_body_count != body_count) {
            throw std::runtime_error(
                "explicit outer update runtime BODY count mismatch");
        }
        const std::size_t expected_bytes =
            static_cast<std::size_t>(runtime_body_count) *
            physics::kBodyRecordSize;
        if (body_byte_count != expected_bytes || body_bytes.size() != expected_bytes) {
            throw std::runtime_error(
                "explicit outer update persistent BODY state cardinality mismatch");
        }
    }

    physics::Fun00770e80ComposedAnchorChainResult execute(
        std::uint32_t runtime_body_count,
        bool workspace_ready,
        bool participant_ready,
        bool participant_identity_join_proven,
        double outer_timestep,
        const physics::Fun0076d100AnchorProvider& physics_pass_provider,
        const physics::Fun00765470MachineHalfStepProvider& half_step_provider,
        const physics::Fun007b8810PostHalfStepCallback& post_half_step) {
        validate_runtime_boundary(
            runtime_body_count,
            workspace_ready,
            participant_ready,
            participant_identity_join_proven);

        auto result = physics::execute_fun_00770e80_composed_anchor_chain(
            outer_timestep,
            body_bytes,
            physics_pass_provider,
            half_step_provider,
            post_half_step);

        const std::size_t expected_bytes =
            static_cast<std::size_t>(runtime_body_count) *
            physics::kBodyRecordSize;
        if (result.final_body_bytes.size() != expected_bytes) {
            throw std::runtime_error(
                "explicit outer update returned malformed persistent BODY state");
        }

        body_bytes = result.final_body_bytes;
        body_byte_count = body_bytes.size();
        last_outer_timestep = outer_timestep;
        last_physics_pass_provider_call_count =
            result.physics_pass_provider_call_count;
        last_half_step_provider_call_count =
            result.half_step_provider_call_count;
        last_scalar_provider_call_count = 0u;
        last_applied_rotation_count = 0u;
        last_zero_noop_count = 0u;
        ++explicit_update_count;
        return result;
    }

    physics::Fun00770e80ScalarProviderAnchorChainResult
    execute_with_fun_007afdd0_scalar_provider(
        std::uint32_t runtime_body_count,
        bool workspace_ready,
        bool participant_ready,
        bool participant_identity_join_proven,
        double outer_timestep,
        const physics::Fun0076d100AnchorProvider& physics_pass_provider,
        const physics::Fun00765470MachineScalarHalfStepProvider& half_step_provider,
        const physics::Fun007b8810PostHalfStepCallback& post_half_step) {
        validate_runtime_boundary(
            runtime_body_count,
            workspace_ready,
            participant_ready,
            participant_identity_join_proven);

        auto result = physics::execute_fun_00770e80_scalar_provider_anchor_chain(
            outer_timestep,
            body_bytes,
            physics_pass_provider,
            half_step_provider,
            post_half_step);

        const std::size_t expected_bytes =
            static_cast<std::size_t>(runtime_body_count) *
            physics::kBodyRecordSize;
        if (result.joined.final_body_bytes.size() != expected_bytes) {
            throw std::runtime_error(
                "explicit scalar-provider outer update returned malformed BODY state");
        }

        body_bytes = result.joined.final_body_bytes;
        body_byte_count = body_bytes.size();
        last_outer_timestep = outer_timestep;
        last_physics_pass_provider_call_count =
            result.joined.physics_pass_provider_call_count;
        last_half_step_provider_call_count =
            result.joined.half_step_provider_call_count;
        last_scalar_provider_call_count = result.scalar_provider_call_count;
        last_applied_rotation_count = result.applied_rotation_count;
        last_zero_noop_count = result.zero_noop_count;
        ++explicit_update_count;
        return result;
    }
};

}  // namespace shift::runtime
