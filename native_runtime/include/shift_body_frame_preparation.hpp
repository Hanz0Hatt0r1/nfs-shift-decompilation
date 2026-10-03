#pragma once

#include "shift_constraint_sample_refresh.hpp"

#include <array>

namespace shift::runtime::physics {

inline constexpr const char* kNativeBodyFramePreparationFormat =
    "SHIFT.NativeBodyFramePreparation/1";
inline constexpr const char* kBodyCoefficientInitSourceFunction =
    "FUN_007ba860";
inline constexpr const char* kBodyTensorSourceFunction =
    "FUN_007ba630";
inline constexpr const char* kBodyFramePrepareSourceFunction =
    "FUN_007ba7e0";

struct BodyCoefficientInitializationResult {
    std::array<float, 3> stored_coefficients{};
    std::array<double, 3> reciprocal_coefficients{};
};

BodyCoefficientInitializationResult
initialize_fun_007ba860_body_coefficients(
    const std::array<double, 3>& coefficients);

using BodyTensor3f = std::array<std::array<float, 3>, 3>;

BodyTensor3f build_fun_007ba630_body_tensor(
    const std::array<double, 3>& diagonal,
    const ConstraintRefreshFrame3f& basis);

struct BodyFramePreparationResult {
    ConstraintRefreshVector3d local_vector{};
    std::array<float, 3> scaled_local_vector{};
    ConstraintRefreshVector3d output_vector{};
};

BodyFramePreparationResult prepare_fun_007ba7e0_body_frame_vector(
    const ConstraintRefreshFrame3f& basis,
    const ConstraintRefreshVector3d& body_vector,
    const std::array<float, 3>& scale);

}  // namespace shift::runtime::physics
