#pragma once

#include "shift_constraint_sample_refresh.hpp"

#include <cmath>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun007af040ColumnTransformFormat =
    "SHIFT.Fun007af040ColumnTransform/1";

inline ConstraintRefreshVector3d execute_fun_007af040_column_transform(
    const ConstraintRefreshFrame3f& matrix,
    double scalar) {
    if (!std::isfinite(scalar)) {
        throw std::invalid_argument("FUN_007af040 scalar must be finite");
    }
    for (const float value : matrix) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument("FUN_007af040 matrix contains non-finite f32");
        }
    }

    // PC retail FUN_007af040 explicitly narrows the QWORD scalar to f32, then
    // multiplies that f32 by the second matrix column at +0x04/+0x10/+0x1c.
    // Each f32 product is widened to f64 for the three output QWORD stores.
    const float narrowed = static_cast<float>(scalar);
    if (!std::isfinite(narrowed)) {
        throw std::invalid_argument("FUN_007af040 scalar overflows source f32 narrowing");
    }
    return {
        static_cast<double>(static_cast<float>(matrix[1] * narrowed)),
        static_cast<double>(static_cast<float>(matrix[4] * narrowed)),
        static_cast<double>(static_cast<float>(matrix[7] * narrowed)),
    };
}

}  // namespace shift::runtime::physics
