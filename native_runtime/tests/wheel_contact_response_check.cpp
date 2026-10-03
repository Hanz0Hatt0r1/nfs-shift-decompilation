#include "shift_wheel_contact_response.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

constexpr double kPi = 3.141592653589793238462643383279502884;

void require_close(
    double actual,
    double expected,
    double tolerance,
    const char* label,
    double& max_error) {

    const double error = std::abs(actual - expected);
    max_error = std::max(max_error, error);
    if (!std::isfinite(actual) || error > tolerance) {
        throw std::runtime_error(label);
    }
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        double max_error = 0.0;

        require_close(
            clamp_fun_00766510_query_scalar(-2.0, 4.0),
            0.0,
            0.0,
            "FUN_00766510 negative clamp",
            max_error);
        require_close(
            clamp_fun_00766510_query_scalar(2.0, 4.0),
            2.0,
            0.0,
            "FUN_00766510 middle clamp",
            max_error);
        require_close(
            clamp_fun_00766510_query_scalar(9.0, 4.0),
            4.0,
            0.0,
            "FUN_00766510 upper clamp",
            max_error);

        const auto packed =
            pack_fun_00752f10_curve_parameters(0.25, 2.0, 1.5);
        require_close(packed.amplitude, 0.25, 0.0, "FUN_00752f10 amplitude", max_error);
        require_close(packed.double_width, 4.0, 0.0, "FUN_00752f10 double width", max_error);
        require_close(
            packed.inverse_width_pi,
            kPi / 2.0,
            1e-15,
            "FUN_00752f10 inverse width pi",
            max_error);
        require_close(packed.half_offset, 0.25, 0.0, "FUN_00752f10 half offset", max_error);

        const WheelContactCurveParameters directional_curve = {
            0.25,
            4.0,
            kPi / 2.0,
            0.25,
        };
        const double directional =
            evaluate_fun_00755340_directional_factor(
                directional_curve,
                1.0,
                1.0);
        const double angle = std::atan2(1.0, -1.0);
        const double angular =
            1.0 +
            (1.0 - std::cos(angle * kPi / 2.0)) * 0.25;
        const double expected_directional =
            angular * (1.0 - (1.0 - std::pow(0.5, 4.0)) * 0.25);
        require_close(
            directional,
            expected_directional,
            1e-15,
            "FUN_00755340 directional factor",
            max_error);

        const WheelContactCurveParameters zero_curve = {
            0.9,
            4.0,
            kPi / 2.0,
            0.25,
        };
        const double zero_angle = std::atan2(0.0, -0.0);
        const double expected_zero =
            1.0 +
            (1.0 - std::cos(zero_angle * kPi / 2.0)) * 0.25;
        require_close(
            evaluate_fun_00755340_directional_factor(
                zero_curve,
                0.0,
                0.0),
            expected_zero,
            1e-15,
            "FUN_00755340 zero-vector branch",
            max_error);

        WheelContactResponseTable table{};
        table.negative_or_zero = {{
            {{1.0, 2.0, 3.0}},
            {{4.0, 5.0, 6.0}},
            {{7.0, 8.0, 9.0}},
        }};
        table.positive = {{
            {{10.0, 20.0, 30.0}},
            {{40.0, 50.0, 60.0}},
            {{70.0, 80.0, 90.0}},
        }};
        table.component_scales = {1.0, 2.0, 3.0};
        const auto quadratic =
            build_fun_007551e0_quadratic_response(
                table,
                {-2.0, 3.0, 0.0});
        const double expected_vector[3] = {364.0, 458.0, 552.0};
        const double expected_aux[3] = {4.0, -18.0, 0.0};
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                quadratic.response_vector[component],
                expected_vector[component],
                0.0,
                "FUN_007551e0 response vector",
                max_error);
            require_close(
                quadratic.auxiliary_response[component],
                expected_aux[component],
                0.0,
                "FUN_007551e0 auxiliary vector",
                max_error);
        }

        const ConstraintRefreshFrame3f response_input_frame = {
            1.0f, 2.0f, 3.0f,
            4.0f, 5.0f, 6.0f,
            7.0f, 8.0f, 9.0f,
        };
        const auto transformed_response_input =
            transform_fun_00766510_response_input(
                response_input_frame,
                {0.25, -0.5, 1.5});
        const double expected_transformed_input[3] = {8.75, 10.0, 11.25};
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                transformed_response_input[component],
                expected_transformed_input[component],
                0.0,
                "FUN_00766510 response input transform",
                max_error);
        }

        const auto composed_curve =
            pack_fun_00752f10_curve_parameters(0.2, 2.0, 1.2);
        WheelContactResponseTable composed_table{};
        composed_table.negative_or_zero = {{
            {{1.0, 0.0, 0.0}},
            {{0.0, 2.0, 0.0}},
            {{0.0, 0.0, 3.0}},
        }};
        composed_table.positive = {{
            {{4.0, 0.0, 0.0}},
            {{0.0, 5.0, 0.0}},
            {{0.0, 0.0, 6.0}},
        }};
        composed_table.component_scales = {1.0, 1.0, 1.0};
        const auto composed =
            evaluate_fun_00766510_contact_response(
                9.0,
                4.0,
                2.0,
                1.0,
                composed_curve,
                composed_table,
                -1.0,
                3.0,
                {-1.0, 2.0, 3.0});
        require_close(
            composed.clamped_query_scalar,
            4.0,
            0.0,
            "FUN_00766510 composed clamp",
            max_error);
        require_close(
            composed.response_gain,
            9.0 * composed.directional_factor,
            1e-15,
            "FUN_00766510 composed gain",
            max_error);
        const double composed_vector[3] = {1.0, 20.0, 54.0};
        const double composed_aux[3] = {1.0, -4.0, -9.0};
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                composed.response_input[component],
                std::array<double, 3>{-1.0, 2.0, 3.0}[component],
                0.0,
                "FUN_00766510 stored response input",
                max_error);
            require_close(
                composed.response_vector[component],
                composed_vector[component],
                0.0,
                "FUN_00766510 composed response vector",
                max_error);
            require_close(
                composed.auxiliary_response[component],
                composed_aux[component],
                0.0,
                "FUN_00766510 composed auxiliary vector",
                max_error);
        }

        const ConstraintRefreshFrame3f identity_frame = {
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };
        const auto composed_from_body =
            evaluate_fun_00766510_contact_response_from_body_source(
                9.0,
                4.0,
                2.0,
                1.0,
                composed_curve,
                composed_table,
                -1.0,
                3.0,
                identity_frame,
                {-1.0, 2.0, 3.0});
        require_close(
            composed_from_body.response_gain,
            composed.response_gain,
            0.0,
            "FUN_00766510 body-source gain join",
            max_error);
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                composed_from_body.response_input[component],
                composed.response_input[component],
                0.0,
                "FUN_00766510 body-source response input join",
                max_error);
            require_close(
                composed_from_body.response_vector[component],
                composed.response_vector[component],
                0.0,
                "FUN_00766510 body-source response vector join",
                max_error);
            require_close(
                composed_from_body.auxiliary_response[component],
                composed.auxiliary_response[component],
                0.0,
                "FUN_00766510 body-source auxiliary join",
                max_error);
        }

        bool non_finite_rejected = false;
        try {
            (void)evaluate_fun_00755340_directional_factor(
                directional_curve,
                std::numeric_limits<double>::infinity(),
                0.0);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error(
                "FUN_00755340 accepted non-finite input");
        }

        bool non_finite_source_rejected = false;
        try {
            (void)transform_fun_00766510_response_input(
                identity_frame,
                {0.0, std::numeric_limits<double>::infinity(), 0.0});
        } catch (const std::invalid_argument&) {
            non_finite_source_rejected = true;
        }
        if (!non_finite_source_rejected) {
            throw std::runtime_error(
                "FUN_00766510 accepted non-finite body source vector");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeWheelContactResponse/1\","
            << "\"ready\":true,"
            << "\"consumer\":\"FUN_00766510\","
            << "\"curve_packer\":\"FUN_00752f10\","
            << "\"directional_factor\":\"FUN_00755340\","
            << "\"response_builder\":\"FUN_007551e0\","
            << "\"response_input_transform\":\"FUN_007af0a0\","
            << "\"response_input_transform_proven\":true,"
            << "\"body_frame_offset\":\"0xd4\","
            << "\"body_source_offset\":\"0x18\","
            << "\"non_finite_rejected\":true,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}
