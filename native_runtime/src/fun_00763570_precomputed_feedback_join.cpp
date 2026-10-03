#include "shift_fun_00763570_precomputed_feedback_join.hpp"

#include <optional>
#include <stdexcept>

namespace shift::runtime::physics {

Fun00763570PrecomputedFeedbackJoinResult
execute_fun_00765470_precomputed_longitudinal_feedback_join(
    const Fun00763570PrecomputedProvider& precomputed_provider,
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& reset_state,
    const PreparedBuiltinSolverFrame& solver_topology,
    const PreparedPostSolveBodyProjection& projection,
    const std::vector<std::uint8_t>& body_bytes,
    double timestep,
    const BodyBasisRotationCallback& basis_rotation,
    double tolerance) {

    if (!precomputed_provider) {
        throw std::invalid_argument(
            "FUN_00763570 precomputed feedback join requires transform provider");
    }

    std::optional<WheelLongitudinalBatchResult> longitudinal;
    std::size_t provider_call_count = 0u;

    const auto half_step = execute_fun_00765470_wheel_feedback_join(
        [&] {
            if (longitudinal.has_value() || provider_call_count != 0u) {
                throw std::runtime_error(
                    "FUN_00763570 precomputed provider invoked more than once");
            }
            ++provider_call_count;
            const auto input = precomputed_provider();
            longitudinal = execute_fun_00763570_precomputed_batch(
                input.wheels,
                input.rear_pair_average_enabled,
                input.mode,
                input.global_config_byte);
        },
        source,
        relations,
        reset_state,
        solver_topology,
        projection,
        body_bytes,
        timestep,
        basis_rotation,
        tolerance);

    if (!longitudinal.has_value() || provider_call_count != 1u) {
        throw std::runtime_error(
            "FUN_00763570 precomputed batch was not executed exactly once");
    }

    return {
        *longitudinal,
        half_step,
        provider_call_count,
    };
}

}  // namespace shift::runtime::physics
