#include "materialized_selected_session_race_mode.hpp"
#include "shift_fun_007682c0_projection_state.hpp"

#include <iostream>
#include <stdexcept>

namespace {

using namespace shift::runtime;
using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main() {
    try {
        for (std::int32_t difficulty = 0; difficulty <= 2; ++difficulty) {
            validate_race_mode_player_difficulty(
                RaceModePlayerDifficulty{true, difficulty});
        }

        bool missing_rejected = false;
        try {
            validate_race_mode_player_difficulty(RaceModePlayerDifficulty{});
        } catch (const std::invalid_argument&) {
            missing_rejected = true;
        }
        require(missing_rejected, "missing Player Difficulty failed open");

        bool out_of_domain_rejected = false;
        try {
            validate_race_mode_player_difficulty(
                RaceModePlayerDifficulty{true, 3});
        } catch (const std::invalid_argument&) {
            out_of_domain_rejected = true;
        }
        require(out_of_domain_rejected, "Player Difficulty 3 failed open");

        require(kMaterializedSelectedSessionPlayerDifficulty.ready,
                "selected-session Player Difficulty is not admitted");
        require(kMaterializedSelectedSessionPlayerDifficulty.player_difficulty == 1,
                "selected-session Player Difficulty drift");

        const Fun007560c0MotionReadGateSetup setup{true};
        const Fun00765c40LoadTerms loads{11.0, 22.0, 33.0, 44.0};
        const Fun007682c0DerivedProjectionState projection{};
        const auto input = compose_fun_007682c0_machine_input(
            setup,
            kMaterializedSelectedSessionPlayerDifficulty,
            0.25f,
            loads,
            projection);
        require(input.angle_mode == 1,
                "selected-session Player Difficulty did not reach FUN_007682c0");

        Fun007682c0MachineInput legacy{};
        legacy.angle_mode = 2;
        const Fun007682c0ExternalMachineInput marker = legacy;
        (void)marker;
        const auto input_again = compose_fun_007682c0_machine_input(
            setup,
            kMaterializedSelectedSessionPlayerDifficulty,
            0.25f,
            loads,
            projection);
        require(input_again.angle_mode == 1,
                "legacy late angle-mode value leaked into production composition");

        std::cout
            << "{\"format\":\"SHIFT.DAT00c128ccPlayerDifficultyOwnership/1\","
            << "\"ready\":true,"
            << "\"retail_domain_min\":0,"
            << "\"retail_domain_max\":2,"
            << "\"selected_session_player_difficulty\":1,"
            << "\"late_motion_read_provider_required\":false,"
            << "\"selected_policy_is_retail_observation\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
