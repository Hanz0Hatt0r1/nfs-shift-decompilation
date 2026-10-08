#include "shift_fun_00766510_early_response_branch.hpp"

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
        require(kFun00766510EarlyClampOffset == 0x3b00u,
                "early-response clamp offset drift");
        require(kFun00766510EarlyApplicationOffsets[0] == 0x3b08u &&
                    kFun00766510EarlyApplicationOffsets[1] == 0x3b10u &&
                    kFun00766510EarlyApplicationOffsets[2] == 0x3b18u,
                "early-response application offsets drift");
        require(kFun00766510EarlyTableOffset == 0x3b20u &&
                    kFun00766510EarlyTableEntryCount == 6u &&
                    kFun00766510EarlyTableEntryStride == 0x18u,
                "early-response table geometry drift");
        require(kFun00766510EarlyPersistentLaneOffset == 0x3ae8u &&
                    kFun00766510EarlyRuntimeLaneOffset == 0x3ba8u,
                "early-response dynamic lane offsets drift");

        Fun00766510EarlyResponseSetup setup{};
        setup.clamp_setup_value = 7.0;
        setup.application_vector = {1.0, 2.0, 3.0};
        for (std::size_t entry = 0; entry < setup.setup_table.size(); ++entry) {
            setup.setup_table[entry] = {
                static_cast<double>(entry * 3u + 0u),
                static_cast<double>(entry * 3u + 1u),
                static_cast<double>(entry * 3u + 2u),
            };
        }

        const Fun00766510EarlyResponsePersistentCoefficients coefficients{
            4.0,
            5.0,
        };
        const auto persistent =
            refresh_fun_00756b60_early_response_state(coefficients, 3.0);
        require(persistent.selector == 3.0,
                "FUN_00756b60 selector witness drift");
        require(persistent.persistent_lane == 19.0,
                "FUN_00756b60 +0x3ae8 witness drift");

        const Fun00766510EarlyResponseRuntimeInputs runtime_inputs{
            8.0,   // clamped pair sum
            -3.0,  // pair delta; abs(delta) must be used
            2.0,   // +0x3af0
            4.0,   // +0x3af8
        };
        const auto runtime =
            materialize_fun_00766510_early_response_runtime_state(
                setup,
                persistent,
                runtime_inputs);

        // 2 * 0.5 * 8 + 19 + abs(-3) * 4 = 39.
        require(runtime.runtime_lane == 39.0,
                "early-response +0x3ba8 witness drift");
        require(runtime.table[5][0] == 15.0 &&
                    runtime.table[5][1] == 16.0,
                "early-response sixth-entry setup lanes changed");
        require(runtime.table[5][2] == 39.0,
                "early-response sixth-entry runtime lane was not refreshed");
        require(setup.setup_table[5][2] == 17.0,
                "runtime materialization mutated setup table snapshot");

        std::cout
            << "{\"format\":\"" << kFun00766510EarlyResponseBranchFormat << "\","
            << "\"ready\":true,"
            << "\"table_entry_count\":6,"
            << "\"table_entry_stride\":\"0x18\","
            << "\"persistent_lane_offset\":\"0x3ae8\","
            << "\"runtime_lane_offset\":\"0x3ba8\","
            << "\"contact_response_provider_removed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
