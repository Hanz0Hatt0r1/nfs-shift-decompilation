#include "shift_constraint_relation_state_mutation.hpp"

#include <cstdint>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

void validate_state_cardinality(
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& state) {

    if (state.joint_state_bit0.size() != relations.joints.size() ||
        state.hinge_state_bit0.size() != relations.hinges.size() ||
        state.bar_state_bit0.size() != relations.bars.size()) {
        throw std::runtime_error(
            "constraint relation state mutation cardinality mismatch");
    }
}

void validate_body_index(
    const PreparedConstraintSampleRelationFrame& relations,
    std::size_t body_index,
    const char* label) {

    if (relations.body_count == 0u ||
        body_index >= relations.body_count) {
        throw std::runtime_error(
            std::string(label) +
            " BODY index is outside relation domain");
    }
}

template <typename Relation>
void validate_relation_endpoints(
    const PreparedConstraintSampleRelationFrame& relations,
    const Relation& relation,
    const char* label) {

    if (relation.positive.body_index >= relations.body_count ||
        relation.negative.body_index >= relations.body_count) {
        throw std::runtime_error(
            std::string(label) +
            " relation endpoint BODY index is outside relation domain");
    }
}

void validate_relation_frame(
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& state) {

    if (relations.body_count == 0u) {
        throw std::runtime_error(
            "constraint relation state mutation requires BODY domain");
    }
    validate_state_cardinality(relations, state);

    for (const auto& relation : relations.joints) {
        validate_relation_endpoints(
            relations, relation, "JOINT");
    }
    for (const auto& relation : relations.hinges) {
        validate_relation_endpoints(
            relations, relation, "HINGE");
    }
    for (const auto& relation : relations.bars) {
        validate_relation_endpoints(
            relations, relation, "BAR");
    }

    auto validate_bits = [](const auto& bits, const char* label) {
        for (const std::uint8_t bit : bits) {
            if (bit > 1u) {
                throw std::runtime_error(
                    std::string(label) +
                    " relation state bit0 must be 0 or 1");
            }
        }
    };
    validate_bits(state.joint_state_bit0, "JOINT");
    validate_bits(state.hinge_state_bit0, "HINGE");
    validate_bits(state.bar_state_bit0, "BAR");
}

template <typename Relation>
bool unordered_pair_matches(
    const Relation& relation,
    std::size_t first_body_index,
    std::size_t second_body_index) {

    const std::size_t positive =
        relation.positive.body_index;
    const std::size_t negative =
        relation.negative.body_index;
    return
        (positive == first_body_index &&
         negative == second_body_index) ||
        (positive == second_body_index &&
         negative == first_body_index);
}

void set_state_bit(
    std::uint8_t& bit,
    std::size_t& matched_count,
    std::size_t& newly_set_count) {

    ++matched_count;
    if (bit == 0u) {
        bit = 1u;
        ++newly_set_count;
    }
}

}  // namespace

ConstraintRelationStateMutationResult
apply_fun_00757d2c_pair_relation_state_mutation(
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& state,
    std::size_t first_body_index,
    std::size_t second_body_index) {

    validate_relation_frame(relations, state);
    validate_body_index(
        relations, first_body_index, "first");
    validate_body_index(
        relations, second_body_index, "second");

    ConstraintRelationStateMutationResult result{};
    result.frame = state;

    for (std::size_t index = 0;
         index < relations.joints.size();
         ++index) {
        if (unordered_pair_matches(
                relations.joints[index],
                first_body_index,
                second_body_index)) {
            set_state_bit(
                result.frame.joint_state_bit0[index],
                result.matched_joint_relation_count,
                result.newly_set_joint_relation_count);
        }
    }

    for (std::size_t index = 0;
         index < relations.hinges.size();
         ++index) {
        if (unordered_pair_matches(
                relations.hinges[index],
                first_body_index,
                second_body_index)) {
            set_state_bit(
                result.frame.hinge_state_bit0[index],
                result.matched_hinge_relation_count,
                result.newly_set_hinge_relation_count);
        }
    }

    return result;
}

ConstraintRelationStateMutationResult
apply_fun_00757d2c_bar_endpoint_state_mutation(
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& state,
    std::size_t body_index) {

    validate_relation_frame(relations, state);
    validate_body_index(
        relations, body_index, "BAR endpoint");

    ConstraintRelationStateMutationResult result{};
    result.frame = state;
    result.branch =
        ConstraintRelationStateMutationBranch::BarEndpoint;

    for (std::size_t index = 0;
         index < relations.bars.size();
         ++index) {
        const auto& relation =
            relations.bars[index];
        if (relation.positive.body_index == body_index ||
            relation.negative.body_index == body_index) {
            set_state_bit(
                result.frame.bar_state_bit0[index],
                result.matched_bar_relation_count,
                result.newly_set_bar_relation_count);
        }
    }

    return result;
}

ConstraintRelationStateMutationResult
apply_fun_00757d2c_component_relation_state_mutation(
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& state,
    std::optional<std::size_t> primary_body_index,
    std::optional<std::size_t> secondary_body_index,
    std::optional<std::size_t> rear_axle_body_index) {

    validate_relation_frame(relations, state);

    const auto validate_optional_body =
        [&](const std::optional<std::size_t>& body,
            const char* label) {
            if (body.has_value()) {
                validate_body_index(
                    relations, *body, label);
            }
        };
    validate_optional_body(
        primary_body_index, "component primary");
    validate_optional_body(
        secondary_body_index, "component secondary");
    validate_optional_body(
        rear_axle_body_index, "rear axle");

    ConstraintRelationStateMutationResult result{};
    result.frame = state;
    result.component_state_504_set = true;

    if (secondary_body_index.has_value()) {
        result.branch =
            ConstraintRelationStateMutationBranch::BarEndpoint;
        result.component_state_540_set = true;

        for (std::size_t index = 0;
             index < relations.bars.size();
             ++index) {
            const auto& relation =
                relations.bars[index];
            if (relation.positive.body_index ==
                    *secondary_body_index ||
                relation.negative.body_index ==
                    *secondary_body_index) {
                set_state_bit(
                    result.frame.bar_state_bit0[index],
                    result.matched_bar_relation_count,
                    result.newly_set_bar_relation_count);
            }
        }
        return result;
    }

    result.branch =
        ConstraintRelationStateMutationBranch::JointHingePair;
    if (!primary_body_index.has_value() ||
        !rear_axle_body_index.has_value()) {
        return result;
    }

    for (std::size_t index = 0;
         index < relations.joints.size();
         ++index) {
        if (unordered_pair_matches(
                relations.joints[index],
                *primary_body_index,
                *rear_axle_body_index)) {
            set_state_bit(
                result.frame.joint_state_bit0[index],
                result.matched_joint_relation_count,
                result.newly_set_joint_relation_count);
        }
    }

    for (std::size_t index = 0;
         index < relations.hinges.size();
         ++index) {
        if (unordered_pair_matches(
                relations.hinges[index],
                *primary_body_index,
                *rear_axle_body_index)) {
            set_state_bit(
                result.frame.hinge_state_bit0[index],
                result.matched_hinge_relation_count,
                result.newly_set_hinge_relation_count);
        }
    }

    return result;
}

ConstraintRelationStateMutationResult
apply_fun_00757d20_component_slot_relation_state_mutation(
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& state,
    const ConstraintRelationVehicleComponentMap& component_map,
    std::size_t component_slot) {

    if (component_slot >= component_map.components.size()) {
        throw std::runtime_error(
            "FUN_00757d20 component slot is outside 0..3");
    }

    const auto& component =
        component_map.components[component_slot];
    return apply_fun_00757d2c_component_relation_state_mutation(
        relations,
        state,
        component.primary_body_index,
        component.secondary_body_index,
        component_map.rear_axle_body_index);
}

}  // namespace shift::runtime::physics
