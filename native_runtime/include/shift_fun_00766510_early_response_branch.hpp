#pragma once

#include "shift_wheel_contact_response.hpp"

#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00766510EarlyResponseBranchFormat =
    "SHIFT.Fun00766510EarlyResponseBranch/1";

inline constexpr std::size_t kFun00766510EarlyClampOffset = 0x3b00u;
inline constexpr std::array<std::size_t, 3>
    kFun00766510EarlyApplicationOffsets = {0x3b08u, 0x3b10u, 0x3b18u};
inline constexpr std::size_t kFun00766510EarlyTableOffset = 0x3b20u;
inline constexpr std::size_t kFun00766510EarlyTableEntryCount = 6u;
inline constexpr std::size_t kFun00766510EarlyTableEntryStride = 0x18u;
inline constexpr std::size_t kFun00766510EarlyPersistentLaneOffset = 0x3ae8u;
inline constexpr std::size_t kFun00766510EarlyRuntimeLaneOffset = 0x3ba8u;
inline constexpr std::size_t kFun00766510EarlySelectorOffset = 0x3c90u;
inline constexpr std::size_t kFun00766510EarlyRuntimeBaseCoefficientOffset = 0x3af0u;
inline constexpr std::size_t kFun00766510EarlyRuntimeDeltaCoefficientOffset = 0x3af8u;

using Fun00766510EarlyResponseTable =
    std::array<WheelContactVector3d, kFun00766510EarlyTableEntryCount>;

struct Fun00766510EarlyResponseSetup {
    double clamp_setup_value = 0.0;                 // HDVehicle+0x3b00
    WheelContactVector3d application_vector{};      // +0x3b08/+0x3b10/+0x3b18
    Fun00766510EarlyResponseTable setup_table{};    // +0x3b20..+0x3ba8 at setup
};

struct Fun00766510EarlyResponsePersistentCoefficients {
    double base = 0.0;    // HDVehicle+0x37b0
    double slope = 0.0;   // HDVehicle+0x37b8
};

struct Fun00766510EarlyResponsePersistentState {
    double selector = 0.0;         // HDVehicle+0x3c90
    double persistent_lane = 0.0;  // HDVehicle+0x3ae8
};

struct Fun00766510EarlyResponseRuntimeInputs {
    double clamped_pair_sum = 0.0;
    double pair_delta = 0.0;
    double base_coefficient = 0.0;   // HDVehicle+0x3af0
    double delta_coefficient = 0.0;  // HDVehicle+0x3af8
};

struct Fun00766510EarlyResponseRuntimeState {
    double runtime_lane = 0.0;  // HDVehicle+0x3ba8
    Fun00766510EarlyResponseTable table{};
};

inline Fun00766510EarlyResponsePersistentState
refresh_fun_00756b60_early_response_state(
    const Fun00766510EarlyResponsePersistentCoefficients& coefficients,
    double selector) {
    if (!std::isfinite(coefficients.base) ||
        !std::isfinite(coefficients.slope) ||
        !std::isfinite(selector)) {
        throw std::invalid_argument(
            "FUN_00756b60 early-response inputs must be finite");
    }

    Fun00766510EarlyResponsePersistentState state{};
    state.selector = selector;
    state.persistent_lane = coefficients.slope * selector + coefficients.base;
    if (!std::isfinite(state.persistent_lane)) {
        throw std::invalid_argument(
            "FUN_00756b60 +0x3ae8 derived state overflow");
    }
    return state;
}

inline Fun00766510EarlyResponseRuntimeState
materialize_fun_00766510_early_response_runtime_state(
    const Fun00766510EarlyResponseSetup& setup,
    const Fun00766510EarlyResponsePersistentState& persistent,
    const Fun00766510EarlyResponseRuntimeInputs& inputs) {
    const std::array<double, 6> values = {
        setup.clamp_setup_value,
        persistent.selector,
        persistent.persistent_lane,
        inputs.clamped_pair_sum,
        inputs.pair_delta,
        inputs.base_coefficient,
    };
    for (const double value : values) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "FUN_00766510 early-response state contains non-finite value");
        }
    }
    if (!std::isfinite(inputs.delta_coefficient)) {
        throw std::invalid_argument(
            "FUN_00766510 early-response delta coefficient must be finite");
    }

    Fun00766510EarlyResponseRuntimeState state{};
    state.runtime_lane =
        inputs.base_coefficient * 0.5 * inputs.clamped_pair_sum +
        persistent.persistent_lane +
        std::abs(inputs.pair_delta) * inputs.delta_coefficient;
    if (!std::isfinite(state.runtime_lane)) {
        throw std::invalid_argument(
            "FUN_00766510 +0x3ba8 runtime lane overflow");
    }

    state.table = setup.setup_table;
    // Sixth table entry occupies +0x3b98/+0x3ba0/+0x3ba8. Retail rewrites
    // only the third lane immediately before FUN_007551e0. Keep the setup
    // snapshot separate so this runtime mutation cannot be mistaken for a
    // setup constant.
    state.table[5][2] = state.runtime_lane;
    return state;
}

}  // namespace shift::runtime::physics
