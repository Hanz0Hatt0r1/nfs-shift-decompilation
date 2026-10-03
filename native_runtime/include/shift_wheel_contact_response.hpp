#pragma once

#include <array>

namespace shift::runtime::physics {

inline constexpr const char* kNativeWheelContactResponseFormat =
    "SHIFT.NativeWheelContactResponse/1";
inline constexpr const char* kWheelContactConsumerFunction = "FUN_00766510";
inline constexpr const char* kWheelContactCurvePackerFunction = "FUN_00752f10";
inline constexpr const char* kWheelContactDirectionalFactorFunction = "FUN_00755340";
inline constexpr const char* kWheelContactResponseBuilderFunction = "FUN_007551e0";

using WheelContactVector3d = std::array<double, 3>;

struct WheelContactCurveParameters {
    double amplitude = 0.0;
    double double_width = 0.0;
    double inverse_width_pi = 0.0;
    double half_offset = 0.0;
};

struct WheelContactResponseTable {
    std::array<WheelContactVector3d, 3> negative_or_zero{};
    std::array<WheelContactVector3d, 3> positive{};
    WheelContactVector3d component_scales{};
};

struct WheelContactQuadraticResponse {
    WheelContactVector3d response_vector{};
    WheelContactVector3d auxiliary_response{};
};

struct WheelContactResponse {
    double query_scalar_input = 0.0;
    double clamped_query_scalar = 0.0;
    double directional_factor = 0.0;
    double response_gain = 0.0;
    WheelContactVector3d response_vector{};
    WheelContactVector3d auxiliary_response{};
};

WheelContactCurveParameters pack_fun_00752f10_curve_parameters(
    double first,
    double width,
    double target);

double clamp_fun_00766510_query_scalar(double value, double upper);

double evaluate_fun_00755340_directional_factor(
    const WheelContactCurveParameters& curve,
    double tangent_x,
    double tangent_z);

WheelContactQuadraticResponse build_fun_007551e0_quadratic_response(
    const WheelContactResponseTable& table,
    const WheelContactVector3d& response_input);

WheelContactResponse evaluate_fun_00766510_contact_response(
    double query_scalar,
    double query_limit,
    double depth_slope,
    double base_offset,
    const WheelContactCurveParameters& directional_curve,
    const WheelContactResponseTable& response_table,
    double tangent_x,
    double tangent_z,
    const WheelContactVector3d& response_input);

}  // namespace shift::runtime::physics
