#include "shift_fun_00766510_primary_response_post_application.hpp"

#include <cmath>
#include <cstdint>
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

void require_near(double actual, double expected, const char* message) {
    if (std::abs(actual - expected) > 1e-12) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main() {
    try {
        require(kFun00766510CallerReferenceVectorOffset == 0x3b08u,
                "FUN_00766510 caller reference offset drift");
        require(kFun00766510CallerCrossAccumulatorXOffset == 0x40a0u &&
                    kFun00766510CallerCrossAccumulatorYOffset == 0x40a8u &&
                    kFun00766510CallerCrossAccumulatorZOffset == 0x40b0u,
                "FUN_00766510 caller cross accumulator offsets drift");
        require(kFun00753650RetailX87ControlWord == 0x027fu,
                "FUN_00753650 retail x87 control word drift");

        Fun00766510PrimaryResponsePostApplicationInput input{};
        input.caller_reference_vector = {1.0, 2.0, 3.0};
        input.transformed_response = {4.0, 5.0, 6.0};
        input.caller_cross_accumulator = {10.0, 20.0, 30.0};
        input.auxiliary_response = {0.5, -1.0, 2.0};
        input.auxiliary_accumulator = {1.0, 2.0, 3.0};

        const auto result =
            execute_fun_00766510_primary_response_post_application(input);
        require_near(result.caller_cross_delta[0], -3.0,
                     "FUN_00753650 cross X drift");
        require_near(result.caller_cross_delta[1], 6.0,
                     "FUN_00753650 cross Y drift");
        require_near(result.caller_cross_delta[2], -3.0,
                     "FUN_00753650 cross Z drift");
        require_near(result.caller_cross_accumulator[0], 7.0,
                     "FUN_00766510 +0x40a0 accumulation drift");
        require_near(result.caller_cross_accumulator[1], 26.0,
                     "FUN_00766510 +0x40a8 accumulation drift");
        require_near(result.caller_cross_accumulator[2], 27.0,
                     "FUN_00766510 +0x40b0 accumulation drift");
        require_near(result.auxiliary_accumulator[0], 1.5,
                     "FUN_00766510 auxiliary X accumulation drift");
        require_near(result.auxiliary_accumulator[1], 1.0,
                     "FUN_00766510 auxiliary Y accumulation drift");
        require_near(result.auxiliary_accumulator[2], 5.0,
                     "FUN_00766510 auxiliary Z accumulation drift");

        // Regression for the x87 operand direction. DE E1 would negate this
        // component; retail DE E9 must preserve the source left-cross-right sign.
        Fun00766510PrimaryResponsePostApplicationInput sign_input{};
        sign_input.caller_reference_vector = {0.0, 2.0, 3.0};
        sign_input.transformed_response = {0.0, 5.0, 7.0};
        const auto sign_result =
            execute_fun_00766510_primary_response_post_application(sign_input);
        require_near(sign_result.caller_cross_delta[0], -1.0,
                     "FUN_00753650 DE E9 subtraction direction drift");

        bool nonfinite_rejected = false;
        try {
            auto invalid = input;
            invalid.auxiliary_response[1] =
                std::numeric_limits<double>::quiet_NaN();
            (void)execute_fun_00766510_primary_response_post_application(invalid);
        } catch (const std::invalid_argument&) {
            nonfinite_rejected = true;
        }
        require(nonfinite_rejected,
                "FUN_00766510 post application accepted non-finite input");

        std::cout
            << "{\"format\":\""
            << kFun00766510PrimaryResponsePostApplicationFormat << "\","
            << "\"ready\":true,"
            << "\"fun_00753650_x87_control_word\":\"0x027f\","
            << "\"fun_00753650_subtract_opcode\":\"de e9\","
            << "\"caller_cross_offsets\":[\"0x40a0\",\"0x40a8\",\"0x40b0\"],"
            << "\"contact_response_provider_removed\":false,"
            << "\"external_provider_count\":7}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
