#include "shift_constraint_reset_state_frame.hpp"

#include <algorithm>
#include <cstdlib>
#include <exception>
#include <iostream>
#include <numeric>
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

void require_nodes(
    const std::vector<std::size_t>& actual,
    const std::vector<std::size_t>& expected,
    const char* label) {

    if (actual != expected) {
        throw std::runtime_error(
            std::string(label) + " reset-node mismatch");
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        using namespace shift::runtime::physics;
        if (argc != 4) {
            std::cerr
                << "usage: shift_runtime_constraint_reset_state_frame_check "
                << "FILE.gbcf FILE.csrf FILE.crst\n";
            return EXIT_FAILURE;
        }

        const auto generated =
            load_prepared_generated_body_constraint_frame(argv[1]);
        const auto relations =
            load_prepared_constraint_sample_relation_frame(argv[2]);
        const auto reset_state =
            load_prepared_constraint_reset_state_frame(argv[3]);

        const auto refreshed =
            refresh_generated_body_constraint_frame(
                generated,
                relations);
        const auto selected =
            derive_fun_007b2210_reset_nodes(
                refreshed.frame,
                relations,
                reset_state);

        std::vector<std::size_t> all_nodes(40u);
        std::iota(all_nodes.begin(), all_nodes.end(), 0u);
        require_nodes(
            selected.reset_nodes,
            all_nodes,
            "all-low-bit");
        if (selected.joint_relation_count != 4u ||
            selected.hinge_relation_count != 4u ||
            selected.bar_relation_count != 20u ||
            selected.selected_joint_relation_count != 4u ||
            selected.selected_hinge_relation_count != 4u ||
            selected.selected_bar_relation_count != 20u) {
            throw std::runtime_error(
                "constraint reset selection relation counts mismatch");
        }

        auto mixed = reset_state;
        std::fill(
            mixed.joint_runtime_flags.begin(),
            mixed.joint_runtime_flags.end(),
            0u);
        std::fill(
            mixed.hinge_runtime_flags.begin(),
            mixed.hinge_runtime_flags.end(),
            0u);
        std::fill(
            mixed.bar_runtime_flags.begin(),
            mixed.bar_runtime_flags.end(),
            0u);
        mixed.joint_runtime_flags.at(0) = 1u;
        mixed.hinge_runtime_flags.at(0) = 1u;
        mixed.bar_runtime_flags.at(0) = 1u;
        if (mixed.joint_runtime_flags.size() > 1u) {
            mixed.joint_runtime_flags[1] = 2u;
        }
        const auto mixed_selected =
            derive_fun_007b2210_reset_nodes(
                refreshed.frame,
                relations,
                mixed);
        require_nodes(
            mixed_selected.reset_nodes,
            std::vector<std::size_t>{0u, 1u, 2u, 3u, 4u, 20u},
            "mixed-width");
        if (mixed_selected.selected_joint_relation_count != 1u ||
            mixed_selected.selected_hinge_relation_count != 1u ||
            mixed_selected.selected_bar_relation_count != 1u) {
            throw std::runtime_error(
                "constraint reset low-bit selection mismatch");
        }

        auto no_low_bits = mixed;
        no_low_bits.joint_runtime_flags.assign(
            no_low_bits.joint_runtime_flags.size(),
            2u);
        no_low_bits.hinge_runtime_flags.assign(
            no_low_bits.hinge_runtime_flags.size(),
            4u);
        no_low_bits.bar_runtime_flags.assign(
            no_low_bits.bar_runtime_flags.size(),
            8u);
        const auto none =
            derive_fun_007b2210_reset_nodes(
                refreshed.frame,
                relations,
                no_low_bits);
        if (!none.reset_nodes.empty()) {
            throw std::runtime_error(
                "non-low runtime bits selected reset nodes");
        }

        require_runtime_error(
            [&]() {
                auto bad = reset_state;
                bad.bar_runtime_flags.pop_back();
                (void)derive_fun_007b2210_reset_nodes(
                    refreshed.frame,
                    relations,
                    bad);
            },
            "relation counts do not match CSRF",
            "reset relation count mismatch");

        require_runtime_error(
            [&]() {
                auto bad_frame = refreshed.frame;
                bad_frame.bodies[
                    relations.joints.front().negative.body_index]
                    .constraints.joints[
                        relations.joints.front().negative.sample_index]
                    .scalar_base = 5u;
                (void)derive_fun_007b2210_reset_nodes(
                    bad_frame,
                    relations,
                    reset_state);
            },
            "scalar bases do not match",
            "reset endpoint scalar mismatch");

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeConstraintResetStateFrameCheck/1\",\n"
            << "  \"packet_format\": "
            << "\"SHIFT.NativeConstraintResetStateFramePacket/1\",\n"
            << "  \"frame_function\": \"FUN_007b3f40\",\n"
            << "  \"reset_function\": \"FUN_007b2210\",\n"
            << "  \"observed_low_bit_writer\": \"FUN_00757d2c\",\n"
            << "  \"selection_mask\": 1,\n"
            << "  \"joint_relation_count\": 4,\n"
            << "  \"hinge_relation_count\": 4,\n"
            << "  \"bar_relation_count\": 20,\n"
            << "  \"all_selected_reset_nodes\": 40,\n"
            << "  \"mixed_selected_reset_nodes\": 6,\n"
            << "  \"non_low_bits_ignored\": true,\n"
            << "  \"stores_scalar_bases\": false,\n"
            << "  \"stores_reset_nodes\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_constraint_reset_state_frame_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
