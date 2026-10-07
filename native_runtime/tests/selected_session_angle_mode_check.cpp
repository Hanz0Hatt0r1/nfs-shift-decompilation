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
        require(kSelectedSessionPlayerDifficulty == 1,
                "selected native session difficulty drift");
        require(selected_session_fun_007682c0_angle_mode() == 1,
                "selected-session angle mode mismatch");

        Fun007682c0MachineInput legacy{};
        legacy.caller_gate_open = true;
        legacy.angle_mode = 2;
        const Fun007682c0ExternalMachineInput external = legacy;
        const Fun00765c40LoadTerms load_terms{1.0, 2.0, 3.0, 4.0};
        const Fun007682c0DerivedProjectionState projection{};
        const auto composed = compose_fun_007682c0_machine_input(
            external,
            0.0f,
            load_terms,
            projection);
        require(composed.angle_mode == 1 && composed.angle_mode != legacy.angle_mode,
                "late external angle-mode override leaked into production input");

        std::cout
            << "{\"format\":\"" << kSelectedSessionAngleModeFormat << "\","
            << "\"ready\":true,"
            << "\"session_target\":\"" << kSelectedSessionTarget << "\","
            << "\"player_difficulty\":1,"
            << "\"late_external_angle_mode_present\":false,"
            << "\"retail_live_selector_inferred\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
