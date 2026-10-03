#pragma once

#include "shift_body_frame_preparation.hpp"
#include "shift_post_solve_projection.hpp"

#include <functional>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeBodyFrameIntegrationFormat =
    "SHIFT.NativeBodyFrameIntegration/1";
inline constexpr const char* kNativeBodyArrayBasisCallbackFormat =
    "SHIFT.NativeBodyArrayBasisCallback/1";
inline constexpr const char* kBodyArrayIntegrationSourceFunction =
    "FUN_007b2270";
inline constexpr const char* kBodyFrameIntegrationSourceFunction =
    "FUN_007bab70";
inline constexpr const char* kBodyBasisRotationSourceFunction =
    "FUN_007afdd0";
inline constexpr std::size_t kBodyArraySourceStride = 0x170u;

using BodyFrameIntegrationVector3d = ConstraintRefreshVector3d;

struct BodyFrameIntegrationState {
    BodyFrameIntegrationVector3d origin{};
    BodyFrameIntegrationVector3d cross_vector{};
    BodyFrameIntegrationVector3d prepared_vector{};
    BodyAccumulatorState accumulators{};
    BodyFrameIntegrationVector3d motion_triplet{};
    double scalar_0x90 = 0.0;
    std::array<double, 3> reciprocal_coefficients{};
    ConstraintRefreshFrame3f basis{};
};

struct BodyFramePreBasisResult {
    BodyFrameIntegrationState state{};
    BodyFrameIntegrationVector3d rotation_increment{};
};

struct BodyFrameIntegrationResult {
    BodyFrameIntegrationState state{};
    BodyFrameIntegrationVector3d rotation_increment{};
    BodyTensor3f symmetric_tensor{};
};

using BodyBasisRotationCallback = std::function<ConstraintRefreshFrame3f(
    const ConstraintRefreshFrame3f& basis,
    const BodyFrameIntegrationVector3d& rotation_increment)>;

BodyFramePreBasisResult advance_fun_007bab70_pre_basis(
    const BodyFrameIntegrationState& state,
    double timestep);

BodyFrameIntegrationResult complete_fun_007bab70_post_basis(
    const BodyFramePreBasisResult& pre_basis,
    const ConstraintRefreshFrame3f& basis_after_fun_007afdd0,
    double timestep);

BodyFrameIntegrationResult execute_fun_007bab70_with_external_basis(
    const BodyFrameIntegrationState& state,
    const ConstraintRefreshFrame3f& basis_after_fun_007afdd0,
    double timestep);

std::vector<BodyFrameIntegrationResult>
execute_fun_007b2270_body_array_with_external_bases(
    const std::vector<BodyFrameIntegrationState>& bodies,
    const std::vector<ConstraintRefreshFrame3f>& bases_after_fun_007afdd0,
    double timestep);

std::vector<BodyFrameIntegrationResult>
execute_fun_007b2270_body_array_with_basis_callback(
    const std::vector<BodyFrameIntegrationState>& bodies,
    double timestep,
    const BodyBasisRotationCallback& basis_rotation);

}  // namespace shift::runtime::physics
