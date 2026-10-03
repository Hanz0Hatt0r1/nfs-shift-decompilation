#pragma once

#include <array>
#include <cstddef>
#include <vector>

namespace shift::runtime::physics {

using ConstraintRefreshFrame3f = std::array<float, 9>;
using ConstraintRefreshVector3d = std::array<double, 3>;

struct JointConstraintRefreshInput {
    ConstraintRefreshFrame3f positive_body_frame{};
    ConstraintRefreshFrame3f negative_body_frame{};
    ConstraintRefreshVector3d positive_local_position{};
    ConstraintRefreshVector3d negative_local_position{};
};

struct JointConstraintRefreshResult {
    ConstraintRefreshVector3d positive_position{};
    ConstraintRefreshVector3d negative_position{};
};

struct HingeConstraintRefreshInput {
    ConstraintRefreshFrame3f positive_body_frame{};
    ConstraintRefreshFrame3f negative_body_frame{};
    ConstraintRefreshVector3d positive_angular_local{};
    ConstraintRefreshVector3d positive_linear_local{};
    ConstraintRefreshVector3d negative_primary_local{};
};

struct HingeConstraintRefreshResult {
    ConstraintRefreshVector3d positive_angular{};
    ConstraintRefreshVector3d positive_linear{};
    ConstraintRefreshVector3d negative_angular_local{};
    ConstraintRefreshVector3d negative_linear_local{};
    ConstraintRefreshVector3d negative_angular{};
    ConstraintRefreshVector3d negative_linear{};
};

struct BarConstraintRefreshInput {
    ConstraintRefreshFrame3f positive_body_frame{};
    ConstraintRefreshFrame3f negative_body_frame{};
    ConstraintRefreshVector3d positive_body_position{};
    ConstraintRefreshVector3d negative_body_position{};
    ConstraintRefreshVector3d positive_local_point{};
    ConstraintRefreshVector3d negative_local_point{};
};

struct BarConstraintRefreshResult {
    ConstraintRefreshVector3d positive_point{};
    ConstraintRefreshVector3d negative_point{};
    ConstraintRefreshVector3d direction{};
};

struct ConstraintSampleRefreshFrameInput {
    std::vector<JointConstraintRefreshInput> joints;
    std::vector<HingeConstraintRefreshInput> hinges;
    std::vector<BarConstraintRefreshInput> bars;
};

struct ConstraintSampleRefreshFrameResult {
    std::vector<JointConstraintRefreshResult> joints;
    std::vector<HingeConstraintRefreshResult> hinges;
    std::vector<BarConstraintRefreshResult> bars;
    std::size_t joint_count = 0;
    std::size_t hinge_count = 0;
    std::size_t bar_count = 0;
};

ConstraintRefreshVector3d transform_fun_007aefb0_refresh(
    const ConstraintRefreshFrame3f& matrix,
    const ConstraintRefreshVector3d& vector);

ConstraintRefreshVector3d transform_fun_007af010_refresh(
    const ConstraintRefreshFrame3f& matrix,
    double scalar);

ConstraintRefreshVector3d transform_fun_007af0a0_refresh(
    const ConstraintRefreshFrame3f& matrix,
    const ConstraintRefreshVector3d& vector);

JointConstraintRefreshResult refresh_fun_007b2da0_joint(
    const JointConstraintRefreshInput& input);

HingeConstraintRefreshResult refresh_fun_007b2de0_hinge(
    const HingeConstraintRefreshInput& input);

BarConstraintRefreshResult refresh_fun_007b2f70_bar(
    const BarConstraintRefreshInput& input);

ConstraintSampleRefreshFrameResult refresh_fun_007b3ed0_constraints(
    const ConstraintSampleRefreshFrameInput& input);

}  // namespace shift::runtime::physics
