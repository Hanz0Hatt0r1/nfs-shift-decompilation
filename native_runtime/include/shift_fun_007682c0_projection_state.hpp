#pragma once

#include "shift_bmw_m3_e36_response_field_4054.hpp"
#include "shift_fun_007560c0_motion_read_gate_setup.hpp"
#include "shift_fun_00765c40_load_terms.hpp"
#include "shift_fun_007682c0_machine_effect.hpp"

#include <cmath>
#include <cstdint>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun007682c0DerivedProjectionStateFormat =
    "SHIFT.Fun007682c0DerivedProjectionState/1";

// The only remaining late PC field consumed by FUN_00769ef0/FUN_007682c0 is
// DAT_00c128cc. HDVehicle+0xe0 is a FUN_007560c0 vehicle-setup snapshot,
// HDVehicle+0x4068 is derived before both passes, the four wheel load terms are
// outputs of FUN_00765c40 in each pass, selected-BMW +0x4054 is setup-derived,
// and HDVehicle+0x4084/+0x408c are session-owned previous-outer state.
struct Fun007682c0ExternalMachineInput {
    std::int32_t angle_mode = 0;

    Fun007682c0ExternalMachineInput() = default;

    // Compatibility conversion for fixture callers that still construct the
    // wider machine-kernel input. Gate, steering, load terms, +0x4054 and
    // projection fields are intentionally ignored because production receives
    // them from earlier proven owners.
    Fun007682c0ExternalMachineInput(const Fun007682c0MachineInput& legacy)
        : angle_mode(legacy.angle_mode) {}
};

struct Fun007682c0DerivedProjectionState {
    float field_x = 0.0f;
    float field_z = 0.0f;
};

inline Fun007682c0MachineInput compose_fun_007682c0_machine_input(
    const Fun007682c0ExternalMachineInput& external,
    const Fun007560c0MotionReadGateSetup& setup_gate,
    float steering,
    const Fun00765c40LoadTerms& load_terms,
    const Fun007682c0DerivedProjectionState& projection) {
    validate_fun_00765c40_load_terms(load_terms);

    Fun007682c0MachineInput input{};
    input.caller_gate_open = setup_gate.caller_gate_open;
    input.steering = steering;
    input.load_terms = load_terms;
    input.projection_field_x = projection.field_x;
    input.projection_field_z = projection.field_z;
    input.response_field_4054 = selected_bmw_m3_e36_response_field_4054();
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
