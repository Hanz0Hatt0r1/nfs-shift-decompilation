#include "shift_fun_00766510_later_response_branch.hpp"

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
        require(kFun00766510LaterCurveOffset == 0x3a08u,
                "later-response curve offset drift");
        require(kFun00766510LaterApplicationOffsets[0] == 0x3a28u &&
                    kFun00766510LaterApplicationOffsets[1] == 0x3a30u &&
                    kFun00766510LaterApplicationOffsets[2] == 0x3a38u,
                "later-response application offsets drift");
        require(kFun00766510LaterTableOffset == 0x3a40u &&
                    kFun00766510LaterTableEntryCount == 6u &&
                    kFun00766510LaterTableEntryStride == 0x18u,
                "later-response table geometry drift");
        require(kFun00766510LaterRuntimeLaneOffset == 0x3ac0u &&
                    kFun00766510LaterPersistentLaneOffset == 0x3ac8u,
                "later-response mutable sixth-entry lanes drift");

        Fun00766510LaterResponseSetup setup{};
        setup.curve = pack_fun_00752f10_curve_parameters(0.0, 1.0, 1.0);
        setup.application_vector = {1.0, 2.0, 3.0};
        for (std::size_t entry = 0; entry < setup.setup_table.size(); ++entry) {
            setup.setup_table[entry] = {
                static_cast<double>(entry * 3u + 0u),
                static_cast<double>(entry * 3u + 1u),
                static_cast<double>(entry * 3u + 2u),
            };
        }
        setup.coefficients = {
            1.0, 2.0, 3.0,
            4.0, 5.0, 6.0,
            10.0, 20.0,
        };

        const auto persistent =
            refresh_fun_00756b10_later_response_state(
                setup.coefficients,
                2.0);
        require(persistent.selector == 2.0,
                "FUN_00756b10 selector witness drift");
        require(persistent.derived_scale == 17.0,
                "FUN_00756b10 +0x3a00 witness drift");
        require(persistent.persistent_lane == 38.0,
                "FUN_00756b10 +0x3ac8 witness drift");

        const auto runtime =
            materialize_fun_00766510_later_response_runtime_state(
                setup,
                persistent,
                0.25,
                -1.0);
        require(runtime.directional_factor == 1.0,
                "later-response directional factor witness drift");
        require(runtime.runtime_lane == 17.0,
                "later-response +0x3ac0 witness drift");
        require(runtime.table[5][0] == 15.0,
                "later-response sixth-entry first lane must remain setup-owned");
        require(runtime.table[5][1] == 17.0,
                "later-response sixth-entry second lane was not refreshed");
        require(runtime.table[5][2] == 38.0,
                "later-response sixth-entry third lane was not refreshed");
        require(setup.setup_table[5][1] == 16.0 &&
                    setup.setup_table[5][2] == 17.0,
                "runtime materialization mutated setup table snapshot");

        auto mutated = setup.coefficients;
        mutated.base_a = 9.0;
        mutated.base_b = 19.0;
        const auto mutated_state =
            refresh_fun_00756b10_later_response_state(mutated, 2.0);
        require(mutated_state.derived_scale == 25.0 &&
                    mutated_state.persistent_lane == 53.0,
                "mutable coefficient bases were incorrectly frozen");

        const auto restored =
            restore_fun_00766510_later_response_mutable_bases(mutated);
        require(restored.base_a == 10.0 && restored.base_b == 20.0,
                "later-response baseline restore witness drift");
        const auto restored_state =
            refresh_fun_00756b10_later_response_state(restored, 2.0);
        require(restored_state.derived_scale == 26.0 &&
                    restored_state.persistent_lane == 54.0,
                "restored later-response derived state witness drift");

        std::cout
            << "{\"format\":\"" << kFun00766510LaterResponseBranchFormat << "\","
            << "\"ready\":true,"
            << "\"table_entry_count\":6,"
            << "\"table_entry_stride\":\"0x18\","
            << "\"runtime_lane_offset\":\"0x3ac0\","
            << "\"persistent_lane_offset\":\"0x3ac8\","
            << "\"contact_response_provider_removed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
