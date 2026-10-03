#include "shift_wheel_longitudinal_velocity.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

template <typename Range>
void require_finite(const Range& values, const char* label) {
    for (const auto value : values) {
        if (!std::isfinite(static_cast<double>(value))) {
            throw std::invalid_argument(
                std::string(label) + " contains non-finite value");
        }
    }
}

void require_finite_value(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(
            std::string(label) + " must be finite");
    }
}

}  // namespace

WheelLongitudinalVector3d apply_fun_00755f80_reconstructed_subtraction(
    const WheelLongitudinalVector3d& shared_velocity,
    const WheelLongitudinalVector3d& reconstructed_world_velocity) {

    require_finite(shared_velocity, "FUN_00755f80 shared velocity");
    require_finite(
        reconstructed_world_velocity,
        "FUN_00755f80 reconstructed world velocity");

    WheelLongitudinalVector3d result{};
    for (std::size_t component = 0; component < result.size(); ++component) {
        result[component] =
            shared_velocity[component] - reconstructed_world_velocity[component];
    }
    require_finite(result, "FUN_00755f80 shared velocity result");
    return result;
}

WheelLongitudinalObservation execute_fun_00755f80_precomputed_handoff(
    const WheelLongitudinalInput& input) {

    if (input.wheel_index >= kWheelLongitudinalCount) {
        throw std::invalid_argument(
            "FUN_00755f80 wheel index must be in [0, 3]");
    }
    require_finite(input.shared_velocity, "FUN_00755f80 shared velocity");
    require_finite(input.local_velocity, "FUN_00755f80 local velocity");
    require_finite(
        input.reconstructed_world_velocity,
        "FUN_00755f80 reconstructed world velocity");

    WheelLongitudinalObservation result{};
    result.wheel_index = input.wheel_index;
    result.wheel_object_offset =
        kWheelLongitudinalBaseOffset + input.wheel_index * kWheelLongitudinalStride;
    result.input_velocity = input.shared_velocity;
    result.local_velocity = input.local_velocity;
    result.longitudinal_component = input.local_velocity[0];
    require_finite_value(
        result.longitudinal_component,
        "FUN_00755f80 longitudinal component");
    result.reconstructed_world_velocity = input.reconstructed_world_velocity;
    result.shared_velocity_after =
        apply_fun_00755f80_reconstructed_subtraction(
            input.shared_velocity,
            input.reconstructed_world_velocity);
    return result;
}

WheelLongitudinalBatchResult execute_fun_00763570_precomputed_batch(
    const std::array<WheelLongitudinalInput, kWheelLongitudinalCount>& inputs,
    bool rear_pair_average_enabled,
    int mode,
    bool global_config_byte) {

    WheelLongitudinalBatchResult result{};

    for (std::size_t wheel = 0; wheel < kWheelLongitudinalCount; ++wheel) {
        if (inputs[wheel].wheel_index != wheel) {
            throw std::invalid_argument(
                "FUN_00763570 wheel inputs must preserve retail order 0,1,2,3");
        }
        result.observations[wheel] =
            execute_fun_00755f80_precomputed_handoff(inputs[wheel]);
        result.reported_components[wheel] =
            result.observations[wheel].longitudinal_component;
    }

    if (rear_pair_average_enabled && mode == 0 && global_config_byte) {
        const double rear =
            (result.reported_components[2] + result.reported_components[3]) * 0.5;
        require_finite_value(rear, "FUN_00763570 rear pair average");
        result.reported_components[2] = rear;
        result.reported_components[3] = rear;
    }

    require_finite(
        result.reported_components,
        "FUN_00763570 reported components");
    return result;
}

}  // namespace shift::runtime::physics
