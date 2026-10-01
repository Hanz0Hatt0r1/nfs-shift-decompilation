#include "shift_constraint_relation_reset_frame.hpp"

#include <cstdlib>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

template <typename Fn>
void require_runtime_error(
    Fn&& fn,
    const char* needle,
    const char* label) {

    bool rejected = false;
    try {
        fn();
    } catch (const std::runtime_error& error) {
        rejected =
            std::string(error.what()).find(needle) !=
            std::string::npos;
    }
    if (!rejected) {
        throw std::runtime_error(
            std::string(label) + " was not rejected");
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        using namespace shift::runtime::physics;

        if (argc != 4) {
            std::cerr
                << "usage: shift_runtime_constraint_relation_reset_frame_check "
                << "FILE.gbcf FILE.csrf FILE.crrf\n";
            return EXIT_FAILURE;
        }

        const auto frame =
            load_prepared_generated_body_constraint_frame(
                argv[1]);
        const auto relations =
            load_prepared_constraint_sample_relation_frame(
                argv[2]);
        const auto reset_state =
            load_prepared_constraint_relation_reset_frame(
                argv[3]);

        const auto selected =
            select_fun_007b3f40_reset_nodes(
                frame,
                relations,
                reset_state);

        const std::vector<std::size_t> expected = {
            0u,
            1u,
            2u,
            5u,
        };
        if (selected.scalar_count != 6u ||
            selected.joint_relation_count != 1u ||
            selected.hinge_relation_count != 1u ||
            selected.bar_relation_count != 1u ||
            selected.selected_joint_relation_count != 1u ||
            selected.selected_hinge_relation_count != 0u ||
            selected.selected_bar_relation_count != 1u ||
            selected.reset_nodes != expected) {
            throw std::runtime_error(
                "constraint relation reset selection oracle mismatch");
        }

        require_runtime_error(
            [&]() {
                auto bad = reset_state;
                bad.bar_state_bit0.clear();
                (void)select_fun_007b3f40_reset_nodes(
                    frame,
                    relations,
                    bad);
            },
            "state cardinality mismatch",
            "reset state cardinality mismatch");

        require_runtime_error(
            [&]() {
                auto bad_frame = frame;
                bad_frame.bodies[
                    relations.joints[0].positive.body_index]
                    .constraints.joints[
                        relations.joints[0].positive.sample_index]
                    .side_flag = 0u;
                (void)select_fun_007b3f40_reset_nodes(
                    bad_frame,
                    relations,
                    reset_state);
            },
            "side identity mismatch",
            "reset endpoint side mismatch");

        require_runtime_error(
            [&]() {
                auto bad_relations = relations;
                auto bad_state = reset_state;
                bad_relations.bars.push_back(
                    bad_relations.bars.front());
                bad_state.bar_state_bit0.push_back(1u);
                (void)select_fun_007b3f40_reset_nodes(
                    frame,
                    bad_relations,
                    bad_state);
            },
            "scalar layout overlaps",
            "reset scalar overlap");

        require_runtime_error(
            [&]() {
                auto bad_relations = relations;
                auto bad_state = reset_state;
                bad_relations.bars.clear();
                bad_state.bar_state_bit0.clear();
                (void)select_fun_007b3f40_reset_nodes(
                    frame,
                    bad_relations,
                    bad_state);
            },
            "scalar layout is incomplete",
            "reset scalar gap");

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeConstraintRelationResetFrameCheck/1\",\n"
            << "  \"packet_format\": "
            << "\"SHIFT.NativeConstraintRelationResetFramePacket/1\",\n"
            << "  \"source_function\": \"FUN_007b3f40\",\n"
            << "  \"reset_function\": \"FUN_007b2210\",\n"
            << "  \"relation_state_offset\": 112,\n"
            << "  \"relation_state_tested_bit\": 0,\n"
            << "  \"positive_sample_pointer_offset\": 124,\n"
            << "  \"joint_scalar_base_offset\": 48,\n"
            << "  \"hinge_scalar_base_offset\": 148,\n"
            << "  \"bar_scalar_base_offset\": 48,\n"
            << "  \"joint_reset_width\": 3,\n"
            << "  \"hinge_reset_width\": 2,\n"
            << "  \"bar_reset_width\": 1,\n"
            << "  \"selected_joint_relations\": "
            << selected.selected_joint_relation_count << ",\n"
            << "  \"selected_hinge_relations\": "
            << selected.selected_hinge_relation_count << ",\n"
            << "  \"selected_bar_relations\": "
            << selected.selected_bar_relation_count << ",\n"
            << "  \"selected_reset_nodes\": [0, 1, 2, 5],\n"
            << "  \"state_cardinality_fail_closed\": true,\n"
            << "  \"side_identity_fail_closed\": true,\n"
            << "  \"scalar_overlap_fail_closed\": true,\n"
            << "  \"scalar_gap_fail_closed\": true,\n"
            << "  \"reset_nodes_stored_in_packet\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_constraint_relation_reset_frame_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
