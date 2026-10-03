#include "shift_wheel_contact_response.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

constexpr double kPi = 3.141592653589793238462643383279502884;

template <typename Range>
void require_finite(const Range& values, const char* label) {
    for (const auto value : values) {
        if (!std::isfinite(static_cast<double>(value))) {
            throw std::invalid_argument(
                std::string(label) + " contains non-finite value");
        }
    }
}

void require_finite_value(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(
            std::string(label) + " must be finite");
    }
}

void require_curve(const WheelContactCurveParameters& curve) {
    require_finite_value(curve.amplitude, "FUN_00755340 amplitude");
    require_finite_value(curve.double_width, "FUN_00755340 double width");
    require_finite_value(curve.inverse_width_pi, "FUN_00755340 inverse width pi");
    require_finite_value(curve.half_offset, "FUN_00755340 half offset");
}

void require_table(const WheelContactResponseTable& table) {
    for (const auto& vector : table.negative_or_zero) {
        require_finite(vector, "FUN_007551e0 negative/zero response vector");
    }
    for (const auto& vector : table.positive) {
        require_finite(vector, "FUN_007551e0 positive response vector");
    }
    require_finite(table.component_scales, "FUN_007551e0 component scales");
}

}  // namespace

WheelContactCurveParameters pack_fun_00752f10_curve_parameters(
    double first,
    double width,
    double target) {

    require_finite_value(first, "FUN_00752f10 first");
    require_finite_value(width, "FUN_00752f10 width");
    require_finite_value(target, "FUN_00752f10 target");

    WheelContactCurveParameters result{};
    result.amplitude = first;
    result.double_width = width + width;
    result.inverse_width_pi = width > 0.0 ? kPi / width : 0.0;
    result.half_offset = (target - 1.0) * 0.5;
    require_curve(result);
    return result;
}

double clamp_fun_00766510_query_scalar(double value, double upper) {
    require_finite_value(value, "FUN_00766510 query scalar");
    require_finite_value(upper, "FUN_00766510 query upper bound");
    if (value < 0.0) {
        return 0.0;
    }
    if (value > upper) {
        return upper;
    }
    return value;
}

double evaluate_fun_00755340_directional_factor(
    const WheelContactCurveParameters& curve,
    double tangent_x,
    double tangent_z) {

    require_curve(curve);
    require_finite_value(tangent_x, "FUN_00755340 tangent x");
    require_finite_value(tangent_z, "FUN_00755340 tangent z");

    double angular = 1.0;
    if (curve.half_offset != 0.0) {
        const double angle = std::atan2(tangent_x, -tangent_z);
        if (curve.double_width > std::abs(angle)) {
            angular =
                1.0 +
                (1.0 - std::cos(angle * curve.inverse_width_pi)) *
                    curve.half_offset;
        }
    }

    const double z2 = tangent_z * tangent_z;
    const double denominator = tangent_x * tangent_x + z2;
    double result = angular;
    if (denominator > 0.0) {
        const double ratio = z2 / denominator;
        const double ratio2 = ratio * ratio;
        const double ratio4 = ratio2 * ratio2;
        result =
            angular *
            (1.0 - (1.0 - ratio4) * curve.amplitude);
    }
    require_finite_value(result, "FUN_00755340 result");
    return result;
}

WheelContactQuadraticResponse build_fun_007551e0_quadratic_response(
    const WheelContactResponseTable& table,
    const WheelContactVector3d& response_input) {

    require_table(table);
    require_finite(response_input, "FUN_007551e0 response input");

    WheelContactQuadraticResponse result{};
    for (std::size_t component = 0; component < 3u; ++component) {
        const double value = response_input[component];
        const auto& selected =
            value <= 0.0
                ? table.negative_or_zero[component]
                : table.positive[component];
        const double square = value * value;
        for (std::size_t axis = 0; axis < 3u; ++axis) {
            result.response_vector[axis] += selected[axis] * square;
        }
        double auxiliary = square * table.component_scales[component];
        if (value > 0.0) {
            auxiliary = -auxiliary;
        }
        result.auxiliary_response[component] = auxiliary;
    }

    require_finite(result.response_vector, "FUN_007551e0 response vector");
    require_finite(result.auxiliary_response, "FUN_007551e0 auxiliary response");
    return result;
}

WheelContactVector3d transform_fun_00766510_response_input(
    const ConstraintRefreshFrame3f& body_frame,
    const WheelContactVector3d& body_source_vector) {

    return transform_fun_007af0a0_refresh(
        body_frame,
        body_source_vector);
}

WheelContactResponse evaluate_fun_00766510_contact_response(
    double query_scalar,
    double query_limit,
    double depth_slope,
    double base_offset,
    const WheelContactCurveParameters& directional_curve,
    const WheelContactResponseTable& response_table,
    double tangent_x,
    double tangent_z,
    const WheelContactVector3d& response_input) {

    require_finite_value(depth_slope, "FUN_00766510 depth slope");
    require_finite_value(base_offset, "FUN_00766510 base offset");

    WheelContactResponse result{};
    result.query_scalar_input = query_scalar;
    result.clamped_query_scalar =
        clamp_fun_00766510_query_scalar(query_scalar, query_limit);
    result.directional_factor =
        evaluate_fun_00755340_directional_factor(
            directional_curve,
            tangent_x,
            tangent_z);
    result.response_gain =
        (depth_slope * result.clamped_query_scalar + base_offset) *
        result.directional_factor;
    result.response_input = response_input;

    const auto quadratic =
        build_fun_007551e0_quadratic_response(
            response_table,
            response_input);
    result.response_vector = quadratic.response_vector;
    result.auxiliary_response = quadratic.auxiliary_response;

    require_finite(result.response_input, "FUN_00766510 response input");
    require_finite_value(result.response_gain, "FUN_00766510 response gain");
    return result;
}

WheelContactResponse evaluate_fun_00766510_contact_response_from_body_source(
    double query_scalar,
    double query_limit,
    double depth_slope,
    double base_offset,
    const WheelContactCurveParameters& directional_curve,
    const WheelContactResponseTable& response_table,
    double tangent_x,
    double tangent_z,
    const ConstraintRefreshFrame3f& body_frame,
    const WheelContactVector3d& body_source_vector) {

    const auto response_input =
        transform_fun_00766510_response_input(
            body_frame,
            body_source_vector);
    return evaluate_fun_00766510_contact_response(
        query_scalar,
        query_limit,
        depth_slope,
        base_offset,
        directional_curve,
        response_table,
        tangent_x,
        tangent_z,
        response_input);
}

}  // namespace shift::runtime::physics
