#pragma once

#include "shift_fun_007682c0_machine_effect.hpp"

#include <array>
#include <cmath>
#include <cstdint>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun007682c0DerivedProjectionStateFormat =
    "SHIFT.Fun007682c0DerivedProjectionState/1";

// External PC fields still required at the FUN_00769ef0/FUN_007682c0 anchor.
// HDVehicle+0x4084/+0x408c are deliberately absent: PC FUN_00770e80 derives
// them after both half-step pairs and the following outer update reuses them.
struct Fun007682c0ExternalMachineInput {
    bool caller_gate_open = false;
    float steering = 0.0f;
    std::array<double, 4> load_terms{};
    float response_field_4054 = 0.0f;
    std::int32_t angle_mode = 0;

    Fun007682c0ExternalMachineInput() = default;

    // Compatibility conversion for fixture callers that still construct the
    // wider machine-kernel input. Projection fields are intentionally ignored.
    Fun007682c0ExternalMachineInput(const Fun007682c0MachineInput& legacy)
        : caller_gate_open(legacy.caller_gate_open),
          steering(legacy.steering),
          load_terms(legacy.load_terms),
          response_field_4054(legacy.response_field_4054),
          angle_mode(legacy.angle_mode) {}
};

struct Fun007682c0DerivedProjectionState {
    float field_x = 0.0f;
    float field_z = 0.0f;
};

inline Fun007682c0MachineInput compose_fun_007682c0_machine_input(
    const Fun007682c0ExternalMachineInput& external,
    const Fun007682c0DerivedProjectionState& projection) {
    Fun007682c0MachineInput input{};
    input.caller_gate_open = external.caller_gate_open;
    input.steering = external.steering;
    input.load_terms = external.load_terms;
    input.projection_field_x = projection.field_x;
    input.projection_field_z = projection.field_z;
    input.response_field_4054 = external.response_field_4054;
    input.angle_mode = external.angle_mode;
    return input;
}

// PC FUN_00770e80 snapshots BODY0 velocity before both passes, subtracts that
// snapshot from the post-pass BODY0 velocity, multiplies the double delta by
// 1/outer_timestep, then stores X/Z to HDVehicle+0x4084/+0x408c as f32.
inline Fun007682c0DerivedProjectionState derive_fun_007682c0_projection_state(
    double before_velocity_x,
    double before_velocity_z,
    double after_velocity_x,
    double after_velocity_z,
    double outer_timestep) {
    if (!std::isfinite(before_velocity_x) ||
        !std::isfinite(before_velocity_z) ||
        !std::isfinite(after_velocity_x) ||
        !std::isfinite(after_velocity_z)) {
        throw std::invalid_argument(
            "FUN_007682c0 projection derivation requires finite BODY0 velocity");
    }
    if (!std::isfinite(outer_timestep) || outer_timestep <= 0.0) {
        throw std::invalid_argument(
            "FUN_007682c0 projection derivation requires positive finite outer timestep");
    }

    const double reciprocal_timestep = 1.0 / outer_timestep;
    const double derived_x =
        (after_velocity_x - before_velocity_x) * reciprocal_timestep;
    const double derived_z =
        (after_velocity_z - before_velocity_z) * reciprocal_timestep;
    const float field_x = static_cast<float>(derived_x);
    const float field_z = static_cast<float>(derived_z);
    if (!std::isfinite(field_x) || !std::isfinite(field_z)) {
        throw std::invalid_argument(
            "FUN_007682c0 projection derivation overflowed f32 storage");
    }
    return Fun007682c0DerivedProjectionState{field_x, field_z};
}

}  // namespace shift::runtime::physics
