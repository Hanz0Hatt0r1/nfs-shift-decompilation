#include "shift_fun_007682c0_projection_state.hpp"

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
        for (std::size_t index = 0u; index < kFun00765c40WheelCount; ++index) {
            const std::size_t absolute =
                kFun00765c40WheelArrayOffset +
                index * kFun00765c40WheelStride +
                kFun00765c40WheelLoadFieldOffset;
            require(absolute == kFun00765c40HDVehicleLoadTermOffsets[index],
                    "FUN_00765c40 wheel load absolute offset mismatch");
        }

        const Fun007560c0MotionReadGateSetup setup_gate{true};
        const Fun00765c40LoadTerms contact_loads{11.0, 22.0, 33.0, 44.0};
        const Fun007682c0DerivedProjectionState projection{};
        const auto composed = compose_fun_007682c0_machine_input(
            setup_gate,
            0.5f,
            contact_loads,
            projection);

        require(composed.load_terms == contact_loads,
                "typed FUN_00765c40 load terms were not composed");
        require(composed.angle_mode == kBmwNativeSilverstonePlayerDifficulty &&
                    composed.caller_gate_open,
                "setup-owned gate or selected Player Difficulty was not preserved");

        bool nonfinite_rejected = false;
        try {
            Fun00765c40LoadTerms invalid = contact_loads;
            invalid[0] = std::numeric_limits<double>::quiet_NaN();
            (void)compose_fun_007682c0_machine_input(
                setup_gate,
                0.5f,
                invalid,
                projection);
        } catch (const std::invalid_argument&) {
            nonfinite_rejected = true;
        }
        require(nonfinite_rejected,
                "non-finite FUN_00765c40 load term failed open");

        std::cout
            << "{\"format\":\"" << kFun00765c40LoadTermsFormat << "\","
            << "\"ready\":true,"
            << "\"wheel_count\":4,"
            << "\"wheel_stride_hex\":\"0xa80\","
            << "\"wheel_load_field_hex\":\"0x738\","
            << "\"external_motion_read_load_terms_present\":false,"
            << "\"selected_player_difficulty_internal\":true,"
            << "\"typed_contact_factor_load_terms_consumed\":true,"
            << "\"per_pass_refresh_required\":true}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
