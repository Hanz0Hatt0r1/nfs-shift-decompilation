#include "shift_fun_00765c40_wheel_pair_refresh_stage.hpp"

#include <array>
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
        require(kFun00765c40WheelPairRefreshOffsets ==
                    std::array<std::array<std::size_t, 2>, 4>{{
                        {0x0ba0u, 0x0ba8u},
                        {0x1620u, 0x1628u},
                        {0x20a0u, 0x20a8u},
                        {0x2b20u, 0x2b28u},
                    }},
                "FUN_00765c40 wheel-pair destination geometry drift");
        require(kFun00765c40WheelPairRefreshStride == 0x0a80u,
                "FUN_00765c40 wheel-pair stride drift");
        require(fun_00765c40_wheel_pair_refresh_follows_positive_count(),
                "FUN_00765c40 wheel-pair retail scheduling drift");

        Fun00765c40WheelPairComputedInputs computed{};
        computed.qword_bits = {{
            {0x0123456789abcdefULL, 0xfedcba9876543210ULL},
            {0x0011223344556677ULL, 0x8899aabbccddeeffULL},
            {0x1111111111111111ULL, 0x2222222222222222ULL},
            {0x3333333333333333ULL, 0x4444444444444444ULL},
        }};

        const auto state =
            materialize_fun_00765c40_wheel_pair_refresh_stage(computed);
        require(state.qword_bits == computed.qword_bits,
                "FUN_00765c40 wheel-pair qword payloads must be preserved bit-for-bit");

        std::cout
            << "{\"format\":\"" << kFun00765c40WheelPairRefreshStageFormat << "\","
            << "\"ready\":true,"
            << "\"wheel_count\":4,"
            << "\"lane_count\":2,"
            << "\"qword_payloads_bit_preserved\":true,"
            << "\"arithmetic_internalized\":false,"
            << "\"top_level_provider_removed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
