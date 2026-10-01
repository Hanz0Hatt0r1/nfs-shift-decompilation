#include "shift_constraint_sample_refresh.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

template <typename Range>
void require_finite(const Range& values, const char* label) {
    for (const auto value : values) {
        if (!std::isfinite(static_cast<double>(value))) {
            throw std::invalid_argument(
                std::string(label) + " contains non-finite value");
        }
    }
}

ConstraintRefreshVector3d cross(
    const ConstraintRefreshVector3d& left,
    const ConstraintRefreshVector3d& right) {

    return {
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    };
}

}  // namespace

ConstraintRefreshVector3d transform_fun_007aefb0_refresh(
    const ConstraintRefreshFrame3f& matrix,
    const ConstraintRefreshVector3d& vector) {

    require_finite(matrix, "FUN_007aefb0 matrix");
    require_finite(vector, "FUN_007aefb0 vector");

    const float x = static_cast<float>(vector[0]);
    const float y = static_cast<float>(vector[1]);
    const float z = static_cast<float>(vector[2]);
    ConstraintRefreshVector3d result = {
        static_cast<double>(
            matrix[2] * z + matrix[0] * x + matrix[1] * y),
        static_cast<double>(
            matrix[5] * z + matrix[4] * y + matrix[3] * x),
        static_cast<double>(
            matrix[8] * z + matrix[7] * y + matrix[6] * x),
    };
    require_finite(result, "FUN_007aefb0 result");
    return result;
}

ConstraintRefreshVector3d transform_fun_007af0a0_refresh(
    const ConstraintRefreshFrame3f& matrix,
    const ConstraintRefreshVector3d& vector) {

    require_finite(matrix, "FUN_007af0a0 matrix");
    require_finite(vector, "FUN_007af0a0 vector");

    const float x = static_cast<float>(vector[0]);
    const float y = static_cast<float>(vector[1]);
    const float z = static_cast<float>(vector[2]);
    ConstraintRefreshVector3d result = {
        static_cast<double>(
            matrix[6] * z + matrix[0] * x + matrix[3] * y),
        static_cast<double>(
            matrix[7] * z + matrix[4] * y + matrix[1] * x),
        static_cast<double>(
            matrix[8] * z + matrix[5] * y + matrix[2] * x),
    };
    require_finite(result, "FUN_007af0a0 result");
    return result;
}

JointConstraintRefreshResult refresh_fun_007b2da0_joint(
    const JointConstraintRefreshInput& input) {

    JointConstraintRefreshResult result{};
    result.positive_position =
        transform_fun_007aefb0_refresh(
            input.positive_body_frame,
            input.positive_local_position);
    result.negative_position =
        transform_fun_007aefb0_refresh(
            input.negative_body_frame,
            input.negative_local_position);
    return result;
}

HingeConstraintRefreshResult refresh_fun_007b2de0_hinge(
    const HingeConstraintRefreshInput& input) {

    HingeConstraintRefreshResult result{};
    result.positive_angular =
        transform_fun_007aefb0_refresh(
            input.positive_body_frame,
            input.positive_angular_local);
    result.positive_linear =
        transform_fun_007aefb0_refresh(
            input.positive_body_frame,
            input.positive_linear_local);

    const ConstraintRefreshVector3d negative_angular_seed =
        transform_fun_007af0a0_refresh(
            input.negative_body_frame,
            result.positive_angular);
    result.negative_linear_local =
        cross(
            input.negative_primary_local,
            negative_angular_seed);
    result.negative_angular_local =
        cross(
            result.negative_linear_local,
            input.negative_primary_local);

    require_finite(
        result.negative_linear_local,
        "FUN_007b2de0 negative cross row");
    require_finite(
        result.negative_angular_local,
        "FUN_007b2de0 negative rebuilt row");

    result.negative_angular =
        transform_fun_007aefb0_refresh(
            input.negative_body_frame,
            result.negative_angular_local);
    result.negative_linear =
        transform_fun_007aefb0_refresh(
            input.negative_body_frame,
            result.negative_linear_local);
    return result;
}

BarConstraintRefreshResult refresh_fun_007b2f70_bar(
    const BarConstraintRefreshInput& input) {

    require_finite(
        input.positive_body_position,
        "FUN_007b2f70 positive BODY position");
    require_finite(
        input.negative_body_position,
        "FUN_007b2f70 negative BODY position");

    BarConstraintRefreshResult result{};
    result.positive_point =
        transform_fun_007aefb0_refresh(
            input.positive_body_frame,
            input.positive_local_point);
    result.negative_point =
        transform_fun_007aefb0_refresh(
            input.negative_body_frame,
            input.negative_local_point);

    long double dx =
        static_cast<long double>(result.positive_point[0]) +
        static_cast<long double>(input.positive_body_position[0]) -
        static_cast<long double>(input.negative_body_position[0]) -
        static_cast<long double>(result.negative_point[0]);
    long double dy =
        static_cast<long double>(result.positive_point[1]) +
        static_cast<long double>(input.positive_body_position[1]) -
        static_cast<long double>(input.negative_body_position[1]) -
        static_cast<long double>(result.negative_point[1]);
    long double dz =
        static_cast<long double>(result.positive_point[2]) +
        static_cast<long double>(input.positive_body_position[2]) -
        static_cast<long double>(input.negative_body_position[2]) -
        static_cast<long double>(result.negative_point[2]);

    const long double length_sq =
        dx * dx + dy * dy + dz * dz;
    if (!std::isfinite(length_sq)) {
        throw std::invalid_argument(
            "FUN_007b2f70 direction norm is non-finite");
    }
    if (length_sq != 0.0L) {
        const long double inverse_length =
            1.0L / std::sqrt(length_sq);
        dx *= inverse_length;
        dy *= inverse_length;
        dz *= inverse_length;
    }
    result.direction = {
        static_cast<double>(dx),
        static_cast<double>(dy),
        static_cast<double>(dz),
    };
    require_finite(
        result.direction,
        "FUN_007b2f70 direction");
    return result;
}

ConstraintSampleRefreshFrameResult refresh_fun_007b3ed0_constraints(
    const ConstraintSampleRefreshFrameInput& input) {

    ConstraintSampleRefreshFrameResult result{};
    result.joints.reserve(input.joints.size());
    for (const auto& joint : input.joints) {
        result.joints.push_back(
            refresh_fun_007b2da0_joint(joint));
    }

    result.hinges.reserve(input.hinges.size());
    for (const auto& hinge : input.hinges) {
        result.hinges.push_back(
            refresh_fun_007b2de0_hinge(hinge));
    }

    result.bars.reserve(input.bars.size());
    for (const auto& bar : input.bars) {
        result.bars.push_back(
            refresh_fun_007b2f70_bar(bar));
    }

    result.joint_count = result.joints.size();
    result.hinge_count = result.hinges.size();
    result.bar_count = result.bars.size();
    return result;
}

}  // namespace shift::runtime::physics
