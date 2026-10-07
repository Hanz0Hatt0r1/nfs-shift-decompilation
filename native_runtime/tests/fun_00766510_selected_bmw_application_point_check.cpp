#include "shift_fun_00766510_selected_bmw_application_point.hpp"

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
        require(kFun00765c40RotatedScratchOffset == 0x38f0u,
                "FUN_00765c40/FUN_00766510 rotated scratch offset drift");

        Fun00765c40SelectedBmwWorldPositionResult source{};
        source.world_transform.body_rotated_local = {1.25, -2.5, 3.75};
        source.world_transform.world_position = {101.25, 197.5, 303.75};

        const auto& application_point =
            fun_00766510_selected_bmw_primary_application_point(source);
        require(&application_point == &source.world_transform.body_rotated_local,
                "FUN_00766510 application point was copied/recomputed instead of aliasing Phase727 scratch");
        require(application_point[0] == 1.25 &&
                    application_point[1] == -2.5 &&
                    application_point[2] == 3.75,
                "FUN_00766510 application point value drift");
        require(application_point != source.world_transform.world_position,
                "FUN_00766510 application point incorrectly used origin-added query world position");

        std::cout
            << "{\"format\":\"" << kFun00766510SelectedBmwApplicationPointFormat << "\","
            << "\"ready\":true,"
            << "\"storage_offset\":\"0x38f0\","
            << "\"aliases_phase727_body_rotated_local\":true,"
            << "\"uses_world_position\":false,"
            << "\"runtime_provider_handoff_joined\":false,"
            << "\"external_provider_count\":7}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
