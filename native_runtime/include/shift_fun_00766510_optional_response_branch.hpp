#pragma once

#include "shift_wheel_contact_response.hpp"

#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00766510OptionalResponseBranchFormat =
    "SHIFT.Fun00766510OptionalResponseBranch/1";

inline constexpr std::size_t kFun00766510OptionalGateOffset = 0x3bc8u;
inline constexpr std::size_t kFun00766510OptionalMutableOffset = 0x3bd0u;
inline constexpr std::array<std::size_t, 9>
    kFun00766510OptionalCoefficientOffsets = {
        0x3bd8u, 0x3be0u, 0x3be8u, 0x3bf0u, 0x3bf8u,
        0x3c00u, 0x3c08u, 0x3c10u, 0x3c30u,
    };
inline constexpr std::array<std::size_t, 4>
    kFun00766510OptionalDerivedShapeOffsets = {
        0x3c18u, 0x3c20u, 0x3c28u, 0x3c38u,
    };
inline constexpr std::size_t kFun00766510OptionalCurveOffset = 0x3c40u;
inline constexpr std::array<std::size_t, 3>
    kFun00766510OptionalApplicationOffsets = {0x3c60u, 0x3c68u, 0x3c70u};

struct Fun00766510OptionalResponseSetup {
    bool gate_enabled = false;                         // HDVehicle+0x3bc8
    double mutable_initial = 0.0;                     // setup value for +0x3bd0
    std::array<double, 9> coefficients{};             // setup-owned coefficient block
    std::array<double, 4> derived_shape{};             // +0x3c18/+0x3c20/+0x3c28/+0x3c38
    WheelContactCurveParameters curve{};              // HDVehicle+0x3c40
    WheelContactVector3d application_vector{};        // +0x3c60/+0x3c68/+0x3c70
};

enum class Fun00766510OptionalMutableWriteSource {
    SetupEvaluation,
    Fun00757fa0IncrementResult,
    Fun00758170ClampResult,
    Fun00769d60ResetClampResult,
    Fun0076ed60StateLoad,
};

struct Fun00766510OptionalResponsePersistentState {
    double mutable_value = 0.0;  // HDVehicle+0x3bd0
    Fun00766510OptionalMutableWriteSource last_write =
        Fun00766510OptionalMutableWriteSource::SetupEvaluation;
};

inline void validate_fun_00766510_optional_response_setup(
    const Fun00766510OptionalResponseSetup& setup) {
    if (!std::isfinite(setup.mutable_initial)) {
        throw std::invalid_argument(
            "FUN_00766510 optional-response +0x3bd0 setup value must be finite");
    }
    for (const double value : setup.coefficients) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "FUN_00766510 optional-response coefficient must be finite");
        }
    }
    for (const double value : setup.derived_shape) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "FUN_00766510 optional-response derived shape must be finite");
        }
    }
    for (const double value : setup.application_vector) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "FUN_00766510 optional-response application vector must be finite");
        }
    }
}

inline Fun00766510OptionalResponsePersistentState
initialize_fun_00766510_optional_response_persistent_state(
    const Fun00766510OptionalResponseSetup& setup) {
    validate_fun_00766510_optional_response_setup(setup);
    return {
        setup.mutable_initial,
        Fun00766510OptionalMutableWriteSource::SetupEvaluation,
    };
}

inline void write_fun_00766510_optional_response_mutable_value(
    Fun00766510OptionalResponsePersistentState& state,
    double source_computed_value,
    Fun00766510OptionalMutableWriteSource source) {
    if (!std::isfinite(source_computed_value)) {
        throw std::invalid_argument(
            "FUN_00766510 optional-response +0x3bd0 write must be finite");
    }

    // Process 1 proves the writer surface but does not yet promote the exact
    // arithmetic of every mutator. Accept the source-computed result here
    // instead of inventing increment/clamp/reset formulas.
    state.mutable_value = source_computed_value;
    state.last_write = source;
}

inline bool fun_00766510_optional_response_gate_passes(
    const Fun00766510OptionalResponseSetup& setup,
    double local_50) {
    if (!std::isfinite(local_50)) {
        throw std::invalid_argument(
            "FUN_00766510 optional-response local_50 must be finite");
    }
    return setup.gate_enabled && local_50 < 0.0;
}

}  // namespace shift::runtime::physics
