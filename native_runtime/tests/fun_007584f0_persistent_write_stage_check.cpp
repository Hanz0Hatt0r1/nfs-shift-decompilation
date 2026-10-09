#include "shift_fun_007584f0_interpolation_call_seam.hpp"
#include "shift_fun_007584f0_persistent_write_stage.hpp"
#include "shift_fun_007584f0_positive_qword_reduction.hpp"

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

}  // namespace

int main() {
    try {
        require(kFun007584f0WheelPersistentOffsets ==
                    std::array<std::size_t, 2>{0x0d40u, 0x17c0u},
                "FUN_007584f0 wheel persistent offsets drift");
        require(kFun007584f0WheelStride == 0x0a80u,
                "FUN_007584f0 wheel persistent stride drift");
        require(kFun007584f0FilteredStateOffset == 0x3420u,
                "FUN_007584f0 filtered-state offset drift");
        require(kFun007584f0InterpolationHelper == 0x00783a30u,
                "FUN_007584f0 interpolation helper drift");
        require(kFun007584f0InterpolationCallSite == 0x007587efu,
                "FUN_007584f0 interpolation call site drift");
        require(kFun007584f0InterpolationStoreSite == 0x007587f4u,
                "FUN_007584f0 interpolation store site drift");
        require(kFun007584f0InterpolationArgumentCount == 4u,
                "FUN_007584f0 interpolation argument count drift");
        require(kFun007584f0PositiveQwordReductionStart == 0x007586f9u,
                "FUN_007584f0 positive-qword reduction start drift");
        require(kFun007584f0PositiveQwordStoreSite == 0x00758731u,
                "FUN_007584f0 positive-qword store-site drift");
        require(kFun007584f0AlternateZeroStoreSite == 0x0075873bu,
                "FUN_007584f0 alternate zero-store site drift");
        require(fun_007584f0_positive_qword_destination_offset(0u) == 0x0d40u &&
                    fun_007584f0_positive_qword_destination_offset(1u) == 0x17c0u,
                "FUN_007584f0 positive-qword destination geometry drift");

        const Fun007584f0InterpolationArguments interpolation_arguments{{
            0.0f,
            2.0f,
            1.0f,
            1.0f,
        }};
        const auto interpolation =
            execute_fun_007584f0_interpolation_native(interpolation_arguments);
        require(interpolation.helper_call_count == 1u,
                "FUN_007584f0 interpolation helper call count drift");
        require(interpolation.destination_offset == 0x3420u,
                "FUN_007584f0 interpolation destination drift");
        require(interpolation.value == 1.0f,
                "FUN_007584f0 native FUN_00783a30 formula drift");

        const Fun007584f0PositiveQwordReductionInput qword_input{
            {2.0, 3.0, 4.0},
            {5.0, 7.0, 11.0},
            {13.0, 17.0, 19.0},
        };
        const double positive_qword =
            execute_fun_007584f0_positive_qword_reduction(qword_input);
        require(positive_qword == 75.0 / 153.0,
                "FUN_007584f0 positive-qword reduction formula drift");

        bool rejected_zero_denominator = false;
        try {
            (void)execute_fun_007584f0_positive_qword_reduction({
                {1.0, 0.0, 0.0},
                {2.0, 3.0, 4.0},
                {0.0, 1.0, 0.0},
            });
        } catch (const std::invalid_argument&) {
            rejected_zero_denominator = true;
        }
        require(rejected_zero_denominator,
                "FUN_007584f0 zero positive-qword denominator failed open");

        bool rejected_non_finite_vector = false;
        try {
            (void)execute_fun_007584f0_positive_qword_reduction({
                {std::numeric_limits<double>::infinity(), 0.0, 0.0},
                {1.0, 0.0, 0.0},
                {1.0, 0.0, 0.0},
            });
        } catch (const std::invalid_argument&) {
            rejected_non_finite_vector = true;
        }
        require(rejected_non_finite_vector,
                "FUN_007584f0 non-finite positive-qword vector failed open");

        const Fun00765c40LoadTerms loads = {-0.5, 2.0, 8.0, 9.0};
        const Fun007584f0ComputedInputs computed{
            {11.0, positive_qword},
            interpolation.value,
        };
        const auto state = materialize_fun_007584f0_persistent_write_stage(
            loads,
            computed);
        require(state.wheel_values[0] == 0.0,
                "FUN_007584f0 non-positive load must write zero qword");
        require(state.wheel_values[1] == positive_qword,
                "FUN_007584f0 positive load must preserve computed qword");
        require(state.filtered_value == 1.0f,
                "FUN_007584f0 +0x3420 interpolation handoff drift");

        const Fun00765c40LoadTerms zero_loads = {0.0, 0.0, 1.0, 1.0};
        const auto zero_state = materialize_fun_007584f0_persistent_write_stage(
            zero_loads,
            computed);
        require(zero_state.wheel_values[0] == 0.0 &&
                    zero_state.wheel_values[1] == 0.0,
                "FUN_007584f0 zero load must take alternate zero branch");

        std::cout
            << "{\"format\":\"" << kFun007584f0PersistentWriteStageFormat << "\","
            << "\"ready\":true,"
            << "\"persistent_write_count\":3,"
            << "\"interpolation_call_seam_format\":\""
            << kFun007584f0InterpolationCallSeamFormat << "\","
            << "\"interpolation_helper_call_count\":1,"
            << "\"interpolation_helper_formula_internalized\":true,"
            << "\"positive_qword_reduction_format\":\""
            << kFun007584f0PositiveQwordReductionFormat << "\","
            << "\"positive_qword_final_reduction_internalized\":true,"
            << "\"positive_qword_input_vectors_internalized\":false,"
            << "\"branch_semantics_internalized\":true,"
            << "\"computed_arithmetic_internalized\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
