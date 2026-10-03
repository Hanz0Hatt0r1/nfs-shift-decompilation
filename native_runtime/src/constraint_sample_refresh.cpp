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

void require_finite_scalar(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(label);
    }
}

double retail_x87_mul(float coefficient, double value) {
    // Retail loads the matrix coefficient with FLD m32real and the operand with
    // FLD/FMUL m64real, then stores one m64real result.  long double keeps the
    // x87-shaped extended intermediate rather than introducing the old f32
    // operand truncation.
    const long double product =
        static_cast<long double>(coefficient) *
        static_cast<long double>(value);
    return static_cast<double>(product);
}

double retail_x87_mul_add3(
    float coefficient0,
    double value0,
    float coefficient1,
    double value1,
    float coefficient2,
    double value2) {

    // Keep the exact retail instruction order: product0, product1, add, product2,
    // add, then FSTP m64real.  This intentionally differs from the older
    // decompiler-shaped expression ordering.
    long double accumulator =
        static_cast<long double>(coefficient0) *
        static_cast<long double>(value0);
    const long double product1 =
        static_cast<long double>(coefficient1) *
        static_cast<long double>(value1);
    accumulator = accumulator + product1;
    const long double product2 =
        static_cast<long double>(coefficient2) *
        static_cast<long double>(value2);
    accumulator = accumulator + product2;
    return static_cast<double>(accumulator);
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

    // Exact retail x87 operand widths/order at 0x007aefb0..0x007af002:
    //   m01*y + m00*x + m02*z
    //   m10*x + m11*y + m12*z
    //   m20*x + m21*y + m22*z
    // Vector operands are QWORD doubles; there is no f64 -> f32 cast.
    ConstraintRefreshVector3d result = {
        retail_x87_mul_add3(
            matrix[1], vector[1],
            matrix[0], vector[0],
            matrix[2], vector[2]),
        retail_x87_mul_add3(
            matrix[3], vector[0],
            matrix[4], vector[1],
            matrix[5], vector[2]),
        retail_x87_mul_add3(
            matrix[6], vector[0],
            matrix[7], vector[1],
            matrix[8], vector[2]),
    };
    require_finite(result, "FUN_007aefb0 result");
    return result;
}

ConstraintRefreshVector3d transform_fun_007af010_refresh(
    const ConstraintRefreshFrame3f& matrix,
    double scalar) {

    require_finite(matrix, "FUN_007af010 matrix");
    require_finite_scalar(scalar, "FUN_007af010 scalar is non-finite");

    // Retail 0x007af010..0x007af032 keeps the QWORD scalar on the x87 stack and
    // multiplies it by the first matrix column at +0x00/+0x0c/+0x18.
    ConstraintRefreshVector3d result = {
        retail_x87_mul(matrix[0], scalar),
        retail_x87_mul(matrix[3], scalar),
        retail_x87_mul(matrix[6], scalar),
    };
    require_finite(result, "FUN_007af010 result");
    return result;
}

ConstraintRefreshVector3d transform_fun_007af0a0_refresh(
    const ConstraintRefreshFrame3f& matrix,
    const ConstraintRefreshVector3d& vector) {

    require_finite(matrix, "FUN_007af0a0 matrix");
    require_finite(vector, "FUN_007af0a0 vector");

    // Exact retail x87 operand widths/order at 0x007af0a0..0x007af0f2:
    //   m10*y + m00*x + m20*z
    //   m01*x + m11*y + m21*z
    //   m02*x + m12*y + m22*z
    // Vector operands are QWORD doubles; there is no f64 -> f32 cast.
    ConstraintRefreshVector3d result = {
        retail_x87_mul_add3(
            matrix[3], vector[1],
            matrix[0], vector[0],
            matrix[6], vector[2]),
        retail_x87_mul_add3(
            matrix[1], vector[0],
            matrix[4], vector[1],
            matrix[7], vector[2]),
        retail_x87_mul_add3(
            matrix[2], vector[0],
            matrix[5], vector[1],
            matrix[8], vector[2]),
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
