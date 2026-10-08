#include "shift_fun_007584f0_interpolation_call_seam.hpp"
#include "shift_fun_007584f0_persistent_write_stage.hpp"

#include <iostream>
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

        const Fun00765c40LoadTerms loads = {-0.5, 2.0, 8.0, 9.0};
        const Fun007584f0ComputedInputs computed{
            {11.0, 13.0},
            interpolation.value,
        };
        const auto state = materialize_fun_007584f0_persistent_write_stage(
            loads,
            computed);
        require(state.wheel_values[0] == 0.0,
                "FUN_007584f0 non-positive load must write zero qword");
        require(state.wheel_values[1] == 13.0,
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
            << "\"positive_qword_arithmetic_internalized\":false,"
            << "\"branch_semantics_internalized\":true,"
            << "\"computed_arithmetic_internalized\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
