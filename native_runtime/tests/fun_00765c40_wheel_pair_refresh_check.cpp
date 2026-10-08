#include "shift_fun_00765c40_wheel_pair_refresh.hpp"

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
        require(kFun00765c40WheelPairLoopBOffsets ==
                    std::array<std::size_t, 8>{
                        0x0ba0u, 0x0ba8u,
                        0x1620u, 0x1628u,
                        0x20a0u, 0x20a8u,
                        0x2b20u, 0x2b28u},
                "FUN_00765c40 wheel-pair offsets drift");
        require(kFun00765c40WheelPairStride == 0x0a80u,
                "FUN_00765c40 wheel-pair stride drift");

        const auto state = materialize_fun_00765c40_wheel_pair_refresh(
            {0.25, 0.75, 3.0});
        for (const auto& pair : state) {
            require(pair[0] == 75.0,
                    "FUN_00765c40 max/clamp first-lane witness drift");
            require(pair[1] == 3.0,
                    "FUN_00765c40 unresolved sqrt-lane handoff drift");
        }

        const auto clamped = materialize_fun_00765c40_wheel_pair_refresh(
            {-1.0, 2.0, 4.5});
        for (const auto& pair : clamped) {
            require(pair[0] == 100.0,
                    "FUN_00765c40 [0,1] clamp witness drift");
            require(pair[1] == 4.5,
                    "FUN_00765c40 repeated sqrt-lane witness drift");
        }

        const auto equal = materialize_fun_00765c40_wheel_pair_refresh(
            {0.5, 0.5, 1.0});
        require(equal[0][0] == 50.0,
                "FUN_00765c40 equal-source first-lane witness drift");

        std::cout
            << "{\"format\":\"" << kFun00765c40WheelPairRefreshFormat << "\","
            << "\"ready\":true,"
            << "\"pair_count\":4,"
            << "\"first_lane_arithmetic_internalized\":true,"
            << "\"sqrt_lane_arithmetic_internalized\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
