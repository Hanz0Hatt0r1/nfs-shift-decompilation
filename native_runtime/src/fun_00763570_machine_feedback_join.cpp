#include "shift_fun_00763570_machine_feedback_join.hpp"

#include <stdexcept>

namespace shift::runtime::physics {

Fun00763570PrecomputedInput build_fun_00763570_machine_precomputed_input(
    const Fun00763570MachineInput& input) {

    Fun00763570PrecomputedInput result{};
    result.rear_pair_average_enabled = input.rear_pair_average_enabled;
    result.mode = input.mode;
    result.global_config_byte = input.global_config_byte;

    for (std::size_t wheel = 0; wheel < kWheelLongitudinalCount; ++wheel) {
        const auto& machine = input.wheels[wheel];
        if (machine.wheel_index != wheel) {
            throw std::invalid_argument(
                "FUN_00763570 machine inputs must preserve retail order 0,1,2,3");
        }

        const auto local = transform_fun_007af0a0_refresh(
            machine.body_frame,
            machine.shared_velocity);
        const auto reconstructed = transform_fun_007af010_refresh(
            machine.body_frame,
            local[0]);

        result.wheels[wheel].wheel_index = machine.wheel_index;
        result.wheels[wheel].shared_velocity = machine.shared_velocity;
        result.wheels[wheel].local_velocity = local;
        result.wheels[wheel].reconstructed_world_velocity = reconstructed;
    }

    return result;
}

Fun00763570MachineFeedbackJoinResult
execute_fun_00765470_machine_longitudinal_feedback_join(
    const Fun00763570MachineProvider& machine_provider,
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& reset_state,
    const PreparedBuiltinSolverFrame& solver_topology,
    const PreparedPostSolveBodyProjection& projection,
    const std::vector<std::uint8_t>& body_bytes,
    double timestep,
    const BodyBasisRotationCallback& basis_rotation,
    double tolerance) {

    if (!machine_provider) {
        throw std::invalid_argument(
            "FUN_00763570 machine feedback join requires transform input provider");
    }

    std::size_t provider_call_count = 0u;
    const auto joined =
        execute_fun_00765470_precomputed_longitudinal_feedback_join(
            [&] {
                if (provider_call_count != 0u) {
                    throw std::runtime_error(
                        "FUN_00763570 machine provider invoked more than once");
                }
                ++provider_call_count;
                return build_fun_00763570_machine_precomputed_input(
                    machine_provider());
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

    if (provider_call_count != 1u) {
        throw std::runtime_error(
            "FUN_00763570 machine provider was not executed exactly once");
    }

    return {
        joined,
        provider_call_count,
        kWheelLongitudinalCount,
    };
}

}  // namespace shift::runtime::physics
