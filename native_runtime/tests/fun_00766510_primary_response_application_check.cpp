#include "shift_fun_00766510_primary_response_application.hpp"

#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void require_close(double actual, double expected, const char* message) {
    if (std::abs(actual - expected) > 1e-12) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main() {
    try {
        require(kFun00766510PrimaryLeverArmOffset == 0x38f0u,
                "FUN_00766510 primary lever-arm offset drift");
        require(kFun00766510PrimaryResponseTableOffset == 0x3950u,
                "FUN_00766510 primary response-table offset drift");
        require(kFun00766510CallerCrossAccumulatorOffset == 0x40a0u,
                "FUN_00766510 caller cross-accumulator offset drift");

        Fun00766510PrimaryResponseApplicationInput input{};
        // Exact +90 degree Z-style basis witness for FUN_007aefb0 ordering:
        // result = {-y, x, z}.
        input.body_frame = {
             0.0f, -1.0f, 0.0f,
             1.0f,  0.0f, 0.0f,
             0.0f,  0.0f, 1.0f,
        };
        input.body_accumulator.angular = {4.0, 5.0, 6.0};
        input.body_accumulator.linear = {1.0, 2.0, 3.0};
        input.point_or_lever_arm = {10.0, 20.0, 30.0};
        input.response_vector = {2.0, -3.0, 5.0};
        input.auxiliary_response = {0.5, -1.0, 2.0};
        input.caller_reference_vector = {7.0, 11.0, 13.0};
        input.caller_cross_accumulator = {100.0, 200.0, 300.0};
        input.auxiliary_accumulator = {10.0, 20.0, 30.0};

        const auto result =
            execute_fun_00766510_primary_response_application(input);

        const BodyAccumulatorVector3d expected_transformed = {3.0, 2.0, 5.0};
        const BodyAccumulatorVector3d expected_body_linear = {4.0, 4.0, 8.0};
        const BodyAccumulatorVector3d expected_body_angular = {44.0, 45.0, -34.0};
        const BodyAccumulatorVector3d expected_cross_delta = {29.0, 4.0, -19.0};
        const BodyAccumulatorVector3d expected_cross_accumulator = {129.0, 204.0, 281.0};
        const WheelContactVector3d expected_auxiliary_accumulator = {10.5, 19.0, 32.0};

        for (std::size_t component = 0u; component < 3u; ++component) {
            require_close(result.transformed_response[component],
                          expected_transformed[component],
                          "FUN_00766510 transformed response drift");
            require_close(result.body_accumulator.linear[component],
                          expected_body_linear[component],
                          "FUN_00766510 BODY linear accumulator drift");
            require_close(result.body_accumulator.angular[component],
                          expected_body_angular[component],
                          "FUN_00766510 BODY angular accumulator drift");
            require_close(result.caller_cross_delta[component],
                          expected_cross_delta[component],
                          "FUN_00753650 caller cross delta drift");
            require_close(result.caller_cross_accumulator[component],
                          expected_cross_accumulator[component],
                          "FUN_00766510 +0x40a0 caller accumulator drift");
            require_close(result.auxiliary_accumulator[component],
                          expected_auxiliary_accumulator[component],
                          "FUN_00766510 auxiliary accumulator drift");
        }

        bool nonfinite_rejected = false;
        try {
            auto invalid = input;
            invalid.response_vector[1] = std::numeric_limits<double>::infinity();
            (void)execute_fun_00766510_primary_response_application(invalid);
        } catch (const std::invalid_argument&) {
            nonfinite_rejected = true;
        }
        require(nonfinite_rejected,
                "FUN_00766510 primary response application accepted non-finite input");

        std::cout
            << "{\"format\":\"" << kFun00766510PrimaryResponseApplicationFormat << "\","
            << "\"ready\":true,"
            << "\"fun_007aefb0_transform\":true,"
            << "\"fun_007baa70_application\":true,"
            << "\"fun_00753650_cross_join\":true,"
            << "\"auxiliary_accumulation\":true,"
            << "\"contact_response_provider_removed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
