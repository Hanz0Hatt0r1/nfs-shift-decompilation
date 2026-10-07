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

void require_near(double actual, double expected, const char* message) {
    if (std::abs(actual - expected) > 1e-12) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main() {
    try {
        require(kFun00766510BodyPointerOffset == 0x33a0u,
                "FUN_00766510 BODY pointer offset drift");
        require(kFun00766510BodyBasisOffset == 0xd4u,
                "FUN_00766510 BODY basis offset drift");
        require(kFun00766510ApplicationPointOffset == 0x38f0u,
                "FUN_00766510 application point offset drift");
        require(kFun00766510ResponseTableOffset == 0x3950u,
                "FUN_00766510 response table offset drift");
        require(kFun00766510ResponseGainOutputOffset == 0x39d0u,
                "FUN_00766510 response gain output offset drift");
        require(kFun00766510SelectedBmwBodyIndex == 0u,
                "FUN_00766510 selected BMW BODY identity drift");

        Fun00766510PrimaryResponseApplicationInput input{};
        input.body_frame = {
            1.0f, 2.0f, 3.0f,
            4.0f, 5.0f, 6.0f,
            7.0f, 8.0f, 9.0f,
        };
        input.body_accumulator.angular = {10.0, 20.0, 30.0};
        input.body_accumulator.linear = {1.0, 2.0, 3.0};
        input.application_point = {2.0, 3.0, 4.0};
        input.response.response_vector = {1.0, -2.0, 0.5};

        const auto result = execute_fun_00766510_primary_response_application(input);
        require_near(result.response_vector[0], 1.0,
                     "FUN_00766510 response-vector X drift");
        require_near(result.response_vector[1], -2.0,
                     "FUN_00766510 response-vector Y drift");
        require_near(result.response_vector[2], 0.5,
                     "FUN_00766510 response-vector Z drift");
        require_near(result.transformed_response[0], -1.5,
                     "FUN_00766510 transformed response X drift");
        require_near(result.transformed_response[1], -3.0,
                     "FUN_00766510 transformed response Y drift");
        require_near(result.transformed_response[2], -4.5,
                     "FUN_00766510 transformed response Z drift");
        require_near(result.body_accumulator.linear[0], -0.5,
                     "FUN_00766510 BODY linear X application drift");
        require_near(result.body_accumulator.linear[1], -1.0,
                     "FUN_00766510 BODY linear Y application drift");
        require_near(result.body_accumulator.linear[2], -1.5,
                     "FUN_00766510 BODY linear Z application drift");
        require_near(result.body_accumulator.angular[0], 8.5,
                     "FUN_00766510 BODY angular X application drift");
        require_near(result.body_accumulator.angular[1], 23.0,
                     "FUN_00766510 BODY angular Y application drift");
        require_near(result.body_accumulator.angular[2], 28.5,
                     "FUN_00766510 BODY angular Z application drift");

        bool nonfinite_rejected = false;
        try {
            auto invalid = input;
            invalid.response.response_vector[0] =
                std::numeric_limits<double>::quiet_NaN();
            (void)execute_fun_00766510_primary_response_application(invalid);
        } catch (const std::invalid_argument&) {
            nonfinite_rejected = true;
        }
        require(nonfinite_rejected,
                "FUN_00766510 primary application accepted non-finite response");

        std::cout
            << "{\"format\":\"" << kFun00766510PrimaryResponseApplicationFormat << "\","
            << "\"ready\":true,"
            << "\"body_pointer_offset\":\"0x33a0\","
            << "\"body_basis_offset\":\"0xd4\","
            << "\"application_point_offset\":\"0x38f0\","
            << "\"response_table_offset\":\"0x3950\","
            << "\"selected_bmw_body_index\":0,"
            << "\"contact_response_provider_removed\":false,"
            << "\"external_provider_count\":7}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
