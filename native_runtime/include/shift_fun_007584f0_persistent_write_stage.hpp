#pragma once

#include "shift_fun_00765c40_load_terms.hpp"

#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun007584f0PersistentWriteStageFormat =
    "SHIFT.Fun007584f0PersistentWriteStage/1";

inline constexpr std::array<std::size_t, 2>
    kFun007584f0WheelPersistentOffsets = {0x0d40u, 0x17c0u};
inline constexpr std::size_t kFun007584f0WheelPersistentCount = 2u;
inline constexpr std::size_t kFun007584f0WheelStride = 0x0a80u;
inline constexpr std::size_t kFun007584f0FilteredStateOffset = 0x3420u;

// These values are the outputs of the still-uninternalized arithmetic inside
// FUN_007584f0.  P2.4 consumes them explicitly so native code can already own
// the proven persistent-write branches without inventing x87/vector math.
struct Fun007584f0ComputedInputs {
    std::array<double, 2> positive_branch_values{};
    float interpolation_result = 0.0f;  // return value of FUN_00783a30
};

struct Fun007584f0PersistentWriteState {
    std::array<double, 2> wheel_values{};  // HDVehicle+0xd40/+0x17c0
    float filtered_value = 0.0f;           // HDVehicle+0x3420
};

inline void validate_fun_007584f0_computed_inputs(
    const Fun007584f0ComputedInputs& inputs) {
    for (const double value : inputs.positive_branch_values) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "FUN_007584f0 positive-branch result must be finite");
        }
    }
    if (!std::isfinite(inputs.interpolation_result)) {
        throw std::invalid_argument(
            "FUN_007584f0 interpolation result must be finite");
    }
}

inline Fun007584f0PersistentWriteState
materialize_fun_007584f0_persistent_write_stage(
    const Fun00765c40LoadTerms& load_terms,
    const Fun007584f0ComputedInputs& computed) {
    validate_fun_00765c40_load_terms(load_terms);
    validate_fun_007584f0_computed_inputs(computed);

    Fun007584f0PersistentWriteState state{};
    for (std::size_t wheel = 0; wheel < kFun007584f0WheelPersistentCount; ++wheel) {
        // Retail FUN_007584f0 explicitly writes a zero qword on the
        // non-positive +0x738 branch; only the positive branch consumes the
        // still-external computed qword.
        state.wheel_values[wheel] =
            load_terms[wheel] <= 0.0 ? 0.0 : computed.positive_branch_values[wheel];
    }
    state.filtered_value = computed.interpolation_result;
    return state;
}

}  // namespace shift::runtime::physics
