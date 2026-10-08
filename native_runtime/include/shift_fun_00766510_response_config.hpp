#pragma once

#include "shift_wheel_contact_response.hpp"

#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00766510ResponseConfigFormat =
    "SHIFT.Fun00766510ResponseConfig/1";

inline constexpr std::size_t kFun00766510ResponseDerivedScaleOffset = 0x3908u;
inline constexpr std::size_t kFun00766510ResponseSetupScaleOffset = 0x3910u;
inline constexpr std::size_t kFun00766510ResponseCurveOffset = 0x3918u;
inline constexpr std::size_t kFun00766510ResponseTableOffset = 0x3950u;
inline constexpr std::size_t kFun00766510ResponseTableEntryCount = 6u;
inline constexpr std::size_t kFun00766510ResponseTableEntryStride = 0x18u;
inline constexpr std::size_t kFun00766510ResponseSelectorOffset = 0x3c78u;
inline constexpr std::size_t kFun00766510ResponseBaseCoefficientOffset = 0x3740u;
inline constexpr std::size_t kFun00766510ResponseLinearCoefficientOffset = 0x3748u;
inline constexpr std::size_t kFun00766510ResponseQuadraticCoefficientOffset = 0x3750u;

using Fun00766510ResponseTable =
    std::array<WheelContactVector3d, kFun00766510ResponseTableEntryCount>;

struct Fun00766510ResponseConfigSetup {
    double setup_scale = 0.0;                  // HDVehicle+0x3910
    WheelContactCurveParameters curve{};       // HDVehicle+0x3918
    Fun00766510ResponseTable response_table{}; // HDVehicle+0x3950..+0x39d8
};

struct Fun00766510ResponseConfigCoefficients {
    double base = 0.0;       // HDVehicle+0x3740
    double linear = 0.0;     // HDVehicle+0x3748
    double quadratic = 0.0;  // HDVehicle+0x3750
};

struct Fun00766510ResponseConfigPersistentState {
    double selector = 0.0;       // HDVehicle+0x3c78
    double derived_scale = 0.0;  // HDVehicle+0x3908
};

inline void validate_fun_00766510_response_config_setup(
    const Fun00766510ResponseConfigSetup& setup) {
    if (!std::isfinite(setup.setup_scale)) {
        throw std::invalid_argument(
            "FUN_00766510 response-config +0x3910 must be finite");
    }
    for (const auto& entry : setup.response_table) {
        for (const double value : entry) {
            if (!std::isfinite(value)) {
                throw std::invalid_argument(
                    "FUN_00766510 response-config table must be finite");
            }
        }
    }
}

inline Fun00766510ResponseConfigPersistentState
refresh_fun_00756ac0_response_config_state(
    const Fun00766510ResponseConfigCoefficients& coefficients,
    double selector) {
    if (!std::isfinite(coefficients.base) ||
        !std::isfinite(coefficients.linear) ||
        !std::isfinite(coefficients.quadratic) ||
        !std::isfinite(selector)) {
        throw std::invalid_argument(
            "FUN_00756ac0 response-config inputs must be finite");
    }

    const double selector_squared = selector * selector;
    Fun00766510ResponseConfigPersistentState state{};
    state.selector = selector;
    state.derived_scale =
        coefficients.quadratic * selector_squared +
        coefficients.linear * selector +
        coefficients.base;
    if (!std::isfinite(state.derived_scale)) {
        throw std::invalid_argument(
            "FUN_00756ac0 +0x3908 derived state overflow");
    }
    return state;
}

}  // namespace shift::runtime::physics
