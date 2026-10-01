#include "shift_constraint_relation_state_mutation.hpp"

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

shift::runtime::physics::ConstraintSampleEndpointRef
endpoint(std::size_t body) {
    return {body, 0u};
}

}  // namespace

int main() {
    try {
        using namespace shift::runtime::physics;

        PreparedConstraintSampleRelationFrame relations{};
        relations.body_count = 5u;

        PreparedJointConstraintRelation joint_a{};
        joint_a.positive = endpoint(0u);
        joint_a.negative = endpoint(1u);
        PreparedJointConstraintRelation joint_b{};
        joint_b.positive = endpoint(1u);
        joint_b.negative = endpoint(2u);
        relations.joints = {joint_a, joint_b};

        PreparedHingeConstraintRelation hinge_a{};
        hinge_a.positive = endpoint(1u);
        hinge_a.negative = endpoint(0u);
        PreparedHingeConstraintRelation hinge_b{};
        hinge_b.positive = endpoint(2u);
        hinge_b.negative = endpoint(3u);
        relations.hinges = {hinge_a, hinge_b};

        PreparedBarConstraintRelation bar_a{};
        bar_a.positive = endpoint(0u);
        bar_a.negative = endpoint(4u);
        PreparedBarConstraintRelation bar_b{};
        bar_b.positive = endpoint(3u);
        bar_b.negative = endpoint(4u);
        PreparedBarConstraintRelation bar_c{};
        bar_c.positive = endpoint(2u);
        bar_c.negative = endpoint(2u);
        relations.bars = {bar_a, bar_b, bar_c};

        PreparedConstraintRelationResetFrame state{};
        state.joint_state_bit0 = {0u, 1u};
        state.hinge_state_bit0 = {0u, 0u};
        state.bar_state_bit0 = {1u, 0u, 0u};

        const auto pair =
            apply_fun_00757d2c_pair_relation_state_mutation(
                relations,
                state,
                0u,
                1u);
        if (pair.frame.joint_state_bit0 !=
                std::vector<std::uint8_t>({1u, 1u}) ||
            pair.frame.hinge_state_bit0 !=
                std::vector<std::uint8_t>({1u, 0u}) ||
            pair.frame.bar_state_bit0 !=
                state.bar_state_bit0 ||
            pair.matched_joint_relation_count != 1u ||
            pair.matched_hinge_relation_count != 1u ||
            pair.matched_bar_relation_count != 0u ||
            pair.newly_set_joint_relation_count != 1u ||
            pair.newly_set_hinge_relation_count != 1u ||
            pair.newly_set_bar_relation_count != 0u) {
            throw std::runtime_error(
                "FUN_00757d2c pair mutation oracle mismatch");
        }

        const auto reversed =
            apply_fun_00757d2c_pair_relation_state_mutation(
                relations,
                state,
                1u,
                0u);
        if (reversed.frame.joint_state_bit0 !=
                pair.frame.joint_state_bit0 ||
            reversed.frame.hinge_state_bit0 !=
                pair.frame.hinge_state_bit0) {
            throw std::runtime_error(
                "FUN_00757d2c pair matching is not unordered");
        }

        const auto unmatched =
            apply_fun_00757d2c_pair_relation_state_mutation(
                relations,
                state,
                0u,
                3u);
        if (unmatched.frame.joint_state_bit0 !=
                state.joint_state_bit0 ||
            unmatched.frame.hinge_state_bit0 !=
                state.hinge_state_bit0 ||
            unmatched.matched_joint_relation_count != 0u ||
            unmatched.matched_hinge_relation_count != 0u) {
            throw std::runtime_error(
                "FUN_00757d2c unmatched pair changed state");
        }

        const auto bar =
            apply_fun_00757d2c_bar_endpoint_state_mutation(
                relations,
                state,
                4u);
        if (bar.frame.bar_state_bit0 !=
                std::vector<std::uint8_t>({1u, 1u, 0u}) ||
            bar.frame.joint_state_bit0 !=
                state.joint_state_bit0 ||
            bar.frame.hinge_state_bit0 !=
                state.hinge_state_bit0 ||
            bar.matched_bar_relation_count != 2u ||
            bar.newly_set_bar_relation_count != 1u) {
            throw std::runtime_error(
                "FUN_00757d2c BAR endpoint mutation oracle mismatch");
        }

        const auto bar_self =
            apply_fun_00757d2c_bar_endpoint_state_mutation(
                relations,
                state,
                2u);
        if (bar_self.frame.bar_state_bit0 !=
                std::vector<std::uint8_t>({1u, 0u, 1u}) ||
            bar_self.matched_bar_relation_count != 1u ||
            bar_self.newly_set_bar_relation_count != 1u) {
            throw std::runtime_error(
                "FUN_00757d2c BAR self-endpoint mutation mismatch");
        }

        require_runtime_error(
            [&]() {
                (void)apply_fun_00757d2c_pair_relation_state_mutation(
                    relations,
                    state,
                    5u,
                    0u);
            },
            "outside relation domain",
            "out-of-range pair BODY");

        require_runtime_error(
            [&]() {
                auto bad_state = state;
                bad_state.hinge_state_bit0.pop_back();
                (void)apply_fun_00757d2c_pair_relation_state_mutation(
                    relations,
                    bad_state,
                    0u,
                    1u);
            },
            "cardinality mismatch",
            "state cardinality mismatch");

        require_runtime_error(
            [&]() {
                auto bad_relations = relations;
                bad_relations.bars[0].negative.body_index = 5u;
                (void)apply_fun_00757d2c_bar_endpoint_state_mutation(
                    bad_relations,
                    state,
                    4u);
            },
            "endpoint BODY index",
            "invalid relation endpoint");

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeConstraintRelationStateMutationCheck/1\",\n"
            << "  \"source_function\": \"FUN_00757d2c\",\n"
            << "  \"relation_state_offset\": 112,\n"
            << "  \"tested_bit\": 0,\n"
            << "  \"pair_branch_joint_hinge\": true,\n"
            << "  \"pair_match_unordered\": true,\n"
            << "  \"bar_branch_endpoint_match\": true,\n"
            << "  \"mutation_set_only\": true,\n"
            << "  \"preexisting_bits_preserved\": true,\n"
            << "  \"scheduler_integrated\": false,\n"
            << "  \"event_timing_assigned\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_constraint_relation_state_mutation_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
