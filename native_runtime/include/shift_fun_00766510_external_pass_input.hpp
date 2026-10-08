#pragma once

#include "shift_fun_00766510_query_scalar_handoff.hpp"
#include "shift_body_accumulator_primitives.hpp"

#include <cmath>
#include <optional>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00766510ExternalPassInputFormat =
    "SHIFT.Fun00766510ExternalPassInput/1";

// Phase745 same-pass handoff into the still-external remainder of FUN_00766510.
// The selected BMW path must carry both the exact FUN_00765c40 query-result scalar
// handoff and the caller-owned HDVehicle+0x38f0 application point recovered by
// Phase743. Generic historical fixtures may leave both fields absent.
struct Fun00766510ExternalPassInput {
    bool selected_bmw_domain = false;
    std::optional<Fun00766510QueryScalarHandoff> query_scalar_handoff{};
    std::optional<BodyAccumulatorVector3d> primary_application_point{};
};

inline void validate_fun_00766510_external_pass_input(
    const Fun00766510ExternalPassInput& input) {
    if (input.selected_bmw_domain) {
        if (!input.query_scalar_handoff.has_value() ||
            !input.primary_application_point.has_value()) {
            throw std::invalid_argument(
                "selected BMW FUN_00766510 input requires same-pass query handoff and +0x38f0 application point");
        }
    }
    if (input.primary_application_point.has_value()) {
        for (double value : *input.primary_application_point) {
            if (!std::isfinite(value)) {
                throw std::invalid_argument(
                    "FUN_00766510 primary application point must be finite");
            }
        }
    }
    if (input.query_scalar_handoff.has_value()) {
        const auto& handoff = *input.query_scalar_handoff;
        if (!std::isfinite(handoff.query_scalar) ||
            !std::isfinite(handoff.query_limit) ||
            !std::isfinite(handoff.clamped_query_scalar)) {
            throw std::invalid_argument(
                "FUN_00766510 same-pass query scalar handoff must be finite");
        }
    }
}

}  // namespace shift::runtime::physics
