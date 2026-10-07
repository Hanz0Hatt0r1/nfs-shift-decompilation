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
        Fun007682c0MachineInput legacy{};
        legacy.caller_gate_open = true;
        legacy.angle_mode = 2;
        const Fun007682c0ExternalMachineInput compatibility = legacy;
        (void)compatibility;
        const RaceModePlayerDifficulty difficulty{true, 1};
        const Fun00765c40LoadTerms loads{1.0, 2.0, 3.0, 4.0};
        const Fun007682c0DerivedProjectionState projection{};

        const auto closed = compose_fun_007682c0_machine_input(
            Fun007560c0MotionReadGateSetup{false},
            difficulty,
            0.0f,
            loads,
            projection);
        require(!closed.caller_gate_open,
                "legacy late gate overrode closed FUN_007560c0 setup state");

        const auto open = compose_fun_007682c0_machine_input(
            Fun007560c0MotionReadGateSetup{true},
            difficulty,
            0.0f,
            loads,
            projection);
        require(open.caller_gate_open,
                "open FUN_007560c0 setup state was not consumed");
        require(open.angle_mode == 1,
                "session-owned RaceModeInfo Player Difficulty was not consumed");
        require(open.angle_mode != legacy.angle_mode,
                "legacy late angle mode leaked into production composition");

        std::cout
            << "{\"format\":\"" << kFun007560c0MotionReadGateSetupFormat << "\","
            << "\"ready\":true,"
            << "\"late_gate_field_present\":false,"
            << "\"legacy_gate_ignored\":true,"
            << "\"setup_gate_consumed\":true,"
            << "\"angle_mode_remains_external\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
