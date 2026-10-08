#include "shift_fun_00765c40_wheel_plane_refresh_stage.hpp"

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
        require(kFun00765c40WheelPlaneRefreshCount == 4u,
                "FUN_00765c40 wheel plane count drift");
        require(kFun00765c40WheelPlaneRefreshOffsets ==
                    std::array<std::size_t, 4>{0x0a70u, 0x14f0u, 0x1f70u, 0x29f0u},
                "FUN_00765c40 wheel plane offsets drift");
        require(fun_00765c40_wheel_plane_refresh_is_first_stage(),
                "FUN_00765c40 wheel plane ordering drift");

        Fun00765c40WheelPlaneRefreshComputedInputs computed{
            0x3ff0000000000000ULL,
            0x4000000000000000ULL,
            0x4008000000000000ULL,
            0x4010000000000000ULL,
        };
        const auto state =
            materialize_fun_00765c40_wheel_plane_refresh_stage(computed);
        require(state.qword_bits == computed,
                "FUN_00765c40 wheel plane qwords must be preserved bit-for-bit");

        std::cout
            << "{\"format\":\"" << kFun00765c40WheelPlaneRefreshStageFormat << "\","
            << "\"ready\":true,"
            << "\"count\":4,"
            << "\"payloads_bit_preserved\":true,"
            << "\"source_arithmetic_internalized\":false,"
            << "\"top_level_provider_removed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
