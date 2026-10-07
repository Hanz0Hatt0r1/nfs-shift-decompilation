#include "shift_fun_007682c0_projection_state.hpp"

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
        require(selected_bmw_native_session_player_difficulty() == 1,
                "selected native Player Difficulty drift");

        const Fun00765c40LoadTerms loads{1.0, 2.0, 3.0, 4.0};
        const Fun007682c0DerivedProjectionState projection{};
        const auto input = compose_fun_007682c0_machine_input(
            Fun007560c0MotionReadGateSetup{true},
            0.25f,
            loads,
            projection);

        require(input.angle_mode == 1,
                "DAT_00c128cc selected-session value was not composed");
        require(input.caller_gate_open,
                "selected difficulty composition changed setup gate");
        require(input.load_terms == loads,
                "selected difficulty composition changed typed load terms");

        std::cout
            << "{\"format\":\"" << kBmwNativeSessionPlayerDifficultyFormat << "\","
            << "\"ready\":true,"
            << "\"selected_player_difficulty\":1,"
            << "\"retail_domain_min\":0,"
            << "\"retail_domain_max\":2,"
            << "\"late_raw_input_provider_required\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
