#pragma once

#include "shift_wheel_contact_response.hpp"

#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00766510LaterResponseBranchFormat =
    "SHIFT.Fun00766510LaterResponseBranch/1";

inline constexpr std::size_t kFun00766510LaterCurveOffset = 0x3a08u;
inline constexpr std::array<std::size_t, 3>
    kFun00766510LaterApplicationOffsets = {0x3a28u, 0x3a30u, 0x3a38u};
inline constexpr std::size_t kFun00766510LaterTableOffset = 0x3a40u;
inline constexpr std::size_t kFun00766510LaterTableEntryCount = 6u;
inline constexpr std::size_t kFun00766510LaterTableEntryStride = 0x18u;
inline constexpr std::size_t kFun00766510LaterDerivedScaleOffset = 0x3a00u;
inline constexpr std::size_t kFun00766510LaterRuntimeLaneOffset = 0x3ac0u;
inline constexpr std::size_t kFun00766510LaterPersistentLaneOffset = 0x3ac8u;
inline constexpr std::size_t kFun00766510LaterSelectorOffset = 0x3cb0u;
inline constexpr std::size_t kFun00766510LaterBaseABaselineOffset = 0x3cb8u;
inline constexpr std::size_t kFun00766510LaterBaseBBaselineOffset = 0x3cc0u;

using Fun00766510LaterResponseTable =
    std::array<WheelContactVector3d, kFun00766510LaterTableEntryCount>;

struct Fun00766510LaterResponseCoefficients {
    double base_a = 0.0;       // HDVehicle+0x3770, mutable
    double linear_a = 0.0;     // HDVehicle+0x3778
    double quadratic_a = 0.0;  // HDVehicle+0x3780
    double base_b = 0.0;       // HDVehicle+0x3788, mutable
    double linear_b = 0.0;     // HDVehicle+0x3790
    double quadratic_b = 0.0;  // HDVehicle+0x3798
    double baseline_a = 0.0;   // HDVehicle+0x3cb8
    double baseline_b = 0.0;   // HDVehicle+0x3cc0
};

struct Fun00766510LaterResponseSetup {
    WheelContactCurveParameters curve{};             // HDVehicle+0x3a08
    WheelContactVector3d application_vector{};       // +0x3a28/+0x3a30/+0x3a38
    Fun00766510LaterResponseTable setup_table{};      // +0x3a40..+0x3ac8 at setup
    Fun00766510LaterResponseCoefficients coefficients{};
};

struct Fun00766510LaterResponsePersistentState {
    double selector = 0.0;         // HDVehicle+0x3cb0
    double derived_scale = 0.0;    // HDVehicle+0x3a00
    double persistent_lane = 0.0;  // HDVehicle+0x3ac8
};

struct Fun00766510LaterResponseRuntimeState {
    double directional_factor = 0.0;
    double runtime_lane = 0.0;  // HDVehicle+0x3ac0
    Fun00766510LaterResponseTable table{};
};

inline void validate_fun_00766510_later_response_coefficients(
    const Fun00766510LaterResponseCoefficients& coefficients) {
    const std::array<double, 8> values = {
        coefficients.base_a,
        coefficients.linear_a,
        coefficients.quadratic_a,
        coefficients.base_b,
        coefficients.linear_b,
        coefficients.quadratic_b,
        coefficients.baseline_a,
        coefficients.baseline_b,
    };
    for (const double value : values) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "FUN_00766510 later-response coefficients contain non-finite value");
        }
    }
}

inline Fun00766510LaterResponsePersistentState refresh_fun_00756b10_later_response_state(
    const Fun00766510LaterResponseCoefficients& coefficients,
    double selector) {
    validate_fun_00766510_later_response_coefficients(coefficients);
    if (!std::isfinite(selector)) {
        throw std::invalid_argument(
            "FUN_00756b10 selector must be finite");
    }

    const double selector_squared = selector * selector;
    Fun00766510LaterResponsePersistentState state{};
    state.selector = selector;
    state.derived_scale =
        coefficients.quadratic_a * selector_squared +
        coefficients.linear_a * selector +
        coefficients.base_a;
    state.persistent_lane =
        coefficients.quadratic_b * selector_squared +
        coefficients.linear_b * selector +
        coefficients.base_b;
    if (!std::isfinite(state.derived_scale) ||
        !std::isfinite(state.persistent_lane)) {
        throw std::invalid_argument(
            "FUN_00756b10 later-response derived state overflow");
    }
    return state;
}

inline Fun00766510LaterResponseCoefficients
restore_fun_00766510_later_response_mutable_bases(
    Fun00766510LaterResponseCoefficients coefficients) {
    validate_fun_00766510_later_response_coefficients(coefficients);
    coefficients.base_a = coefficients.baseline_a;
    coefficients.base_b = coefficients.baseline_b;
    return coefficients;
}

inline Fun00766510LaterResponseRuntimeState
materialize_fun_00766510_later_response_runtime_state(
    const Fun00766510LaterResponseSetup& setup,
    const Fun00766510LaterResponsePersistentState& persistent,
    double tangent_x,
    double tangent_z) {
    if (!std::isfinite(persistent.selector) ||
        !std::isfinite(persistent.derived_scale) ||
        !std::isfinite(persistent.persistent_lane)) {
        throw std::invalid_argument(
            "FUN_00766510 later-response persistent state contains non-finite value");
    }

    Fun00766510LaterResponseRuntimeState state{};
    state.directional_factor = evaluate_fun_00755340_directional_factor(
        setup.curve,
        tangent_x,
        tangent_z);
    state.runtime_lane =
        state.directional_factor * persistent.derived_scale;
    if (!std::isfinite(state.runtime_lane)) {
        throw std::invalid_argument(
            "FUN_00766510 +0x3ac0 runtime lane overflow");
    }

    state.table = setup.setup_table;
    // Sixth table entry occupies +0x3ab8/+0x3ac0/+0x3ac8. Retail rewrites
    // the second lane every branch evaluation and the third lane comes from
    // persistent FUN_00756b10-derived state. The setup snapshot is therefore
    // deliberately not treated as immutable after construction.
    state.table[5][1] = state.runtime_lane;
    state.table[5][2] = persistent.persistent_lane;
    return state;
}

}  // namespace shift::runtime::physics
