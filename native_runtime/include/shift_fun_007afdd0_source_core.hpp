#pragma once

#include "shift_constraint_sample_refresh.hpp"

#include <array>

namespace shift::runtime::physics {

inline constexpr const char* kNativeFun007afdd0SourceCoreFormat =
    "SHIFT.NativeFun007afdd0SourceCore/1";
inline constexpr const char* kFun007afdd0SourceFunction = "FUN_007afdd0";
inline constexpr const char* kFun007afdd0SineHelper = "FUN_00900c40";
inline constexpr const char* kFun007afdd0CosineHelper = "FUN_00900b10";

struct Fun007afdd0ScalarBoundary {
    float squared_magnitude_test = 0.0f;
    float sqrt_magnitude = 0.0f;
    float sine = 0.0f;
    float cosine = 1.0f;
};

struct Fun007afdd0SourceCoreResult {
    bool applied = false;
    std::array<float, 3> normalized_axis{};
    ConstraintRefreshFrame3f rotation_coefficients{};
    ConstraintRefreshFrame3f basis{};
};

Fun007afdd0SourceCoreResult execute_fun_007afdd0_source_core(
    const ConstraintRefreshFrame3f& basis,
    const ConstraintRefreshVector3d& rotation_increment,
    const Fun007afdd0ScalarBoundary& scalars);

}  // namespace shift::runtime::physics
