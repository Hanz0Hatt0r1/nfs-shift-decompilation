#include "shift_fun_00763570_precomputed_feedback_join.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <utility>
#include <vector>

namespace {

using namespace shift::runtime::physics;

PreparedGeneratedBodyConstraintFrame make_frame() {
    PreparedGeneratedBodyConstraintFrame frame{};
    frame.scalar_count = 6;
    frame.matrix_double_count = 36;
    frame.bodies.resize(2);
    for (std::size_t index = 0; index < frame.bodies.size(); ++index) {
        auto& body = frame.bodies[index];
        body.body_index = index;
        body.matrix_double_count = 36;
        body.provider_present = false;
        body.row_indices = {0, 6, 12, 18, 24, 30};
        body.constraints.scalar_count = 6;
        body.constraints.body_position = {static_cast<double>(index), 0.0, 0.0};
        body.constraints.preprojection.body_frame = {
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };
        body.constraints.preprojection.angular_state = {
            1.0 + index, 2.0 + index, 3.0 + index};
        body.constraints.preprojection.linear_state = {
            4.0 + index, 5.0 + index, 6.0 + index};
        body.constraints.preprojection.inverse_scalar = 1.0;
        body.constraints.body_tensor = {{
            {{1.0, 0.0, 0.0}},
            {{0.0, 1.0, 0.0}},
            {{0.0, 0.0, 1.0}},
        }};
        body.constraints.scales.linear_scale = 1.0;
        body.constraints.scales.quadratic_scale = 1.0;

        PreparedJointSample joint{};
        joint.scalar_base = 0;
        joint.side_flag = index == 0 ? 1u : 0u;
        body.constraints.joints.push_back(joint);

        PreparedHingeSample hinge{};
        hinge.scalar_base = 3;
        hinge.side_flag = index == 0 ? 1u : 0u;
        hinge.position = {0.0, 1.0, 0.0};
        body.constraints.hinges.push_back(hinge);

        PreparedBarSample bar{};
        bar.scalar_base = 5;
        bar.side_flag = index == 0 ? 1u : 0u;
        body.constraints.bars.push_back(bar);
    }
    return frame;
}

PreparedConstraintSampleRelationFrame make_relations() {
    PreparedConstraintSampleRelationFrame relations{};
    relations.body_count = 2;

    PreparedJointConstraintRelation joint{};
    joint.positive = {0, 0};
    joint.negative = {1, 0};
    joint.positive_local_position = {1.0, 2.0, 3.0};
    joint.negative_local_position = {-1.0, -2.0, -3.0};
    relations.joints.push_back(joint);

    PreparedHingeConstraintRelation hinge{};
    hinge.positive = {0, 0};
    hinge.negative = {1, 0};
    hinge.positive_angular_local = {1.0, 0.0, 0.0};
    hinge.positive_linear_local = {0.0, 1.0, 0.0};
    relations.hinges.push_back(hinge);

    PreparedBarConstraintRelation bar{};
    bar.positive = {0, 0};
    bar.negative = {1, 0};
    bar.positive_local_point = {0.0, 0.0, 0.0};
    bar.negative_local_point = {0.0, 0.0, 0.0};
    relations.bars.push_back(bar);
    return relations;
}

PreparedPostSolveBodyProjection make_projection(
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations) {
    const auto refreshed = refresh_generated_body_constraint_frame(source, relations);
    PreparedPostSolveBodyProjection projection{};
    projection.solver_vector.assign(6, 0.0);
    projection.bodies.resize(source.bodies.size());
    projection.expected_bodies.resize(source.bodies.size());
    for (std::size_t body = 0; body < source.bodies.size(); ++body) {
        projection.bodies[body].angular =
            source.bodies[body].constraints.preprojection.angular_state;
        projection.bodies[body].linear =
            source.bodies[body].constraints.preprojection.linear_state;
        projection.expected_bodies[body] = projection.bodies[body];
    }

    const auto& jr = relations.joints[0];
    const auto& jp = refreshed.frame.bodies[jr.positive.body_index]
        .constraints.joints[jr.positive.sample_index];
    const auto& jn = refreshed.frame.bodies[jr.negative.body_index]
        .constraints.joints[jr.negative.sample_index];
    projection.joints.push_back({
        jr.positive.body_index, jr.negative.body_index, jp.scalar_base,
        jp.position, jn.position});

    const auto& hr = relations.hinges[0];
    const auto& hp = refreshed.frame.bodies[hr.positive.body_index]
        .constraints.hinges[hr.positive.sample_index];
    const auto& hn = refreshed.frame.bodies[hr.negative.body_index]
        .constraints.hinges[hr.negative.sample_index];
    projection.hinges.push_back({
        hr.positive.body_index, hr.negative.body_index, hp.scalar_base,
        hp.angular, hp.linear, hn.angular, hn.linear});

    const auto& br = relations.bars[0];
    const auto& bp = refreshed.frame.bodies[br.positive.body_index]
        .constraints.bars[br.positive.sample_index];
    const auto& bn = refreshed.frame.bodies[br.negative.body_index]
        .constraints.bars[br.negative.sample_index];
    projection.bars.push_back({
        br.positive.body_index, br.negative.body_index, bp.scalar_base,
        bp.point, bn.point, bp.direction});
    return projection;
}

PreparedBuiltinSolverFrame make_solver_topology(
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations) {
    const auto refreshed = refresh_generated_body_constraint_frame(source, relations);
    const auto generated = execute_prepared_generated_body_constraint_frame(refreshed.frame);
    PreparedBuiltinSolverFrame frame{};
    frame.matrix.assign(6, std::vector<double>(6, 0.0));
    for (std::size_t row = 0; row < 6; ++row) {
        for (std::size_t column = 0; column < 6; ++column) {
            frame.matrix[row][column] = generated.solver_matrix[row * 6 + column];
        }
    }
    frame.rhs = generated.solver_vector;
    frame.reset_nodes = {0, 1, 2, 3, 4, 5};
    auto graph = build_dense_solver_graph(6);
    frame.forward_records = std::move(graph.first);
    frame.reverse_records = std::move(graph.second);
    frame.expected_solution.assign(6, 0.0);
    return frame;
}

PreparedConstraintRelationResetFrame make_reset_state() {
    PreparedConstraintRelationResetFrame reset{};
    reset.joint_state_bit0 = {1u};
    reset.hinge_state_bit0 = {1u};
    reset.bar_state_bit0 = {1u};
    return reset;
}

void put_u64_le(std::vector<std::uint8_t>& bytes, std::size_t offset, std::uint64_t value) {
    for (std::size_t byte = 0; byte < 8u; ++byte) {
        bytes[offset + byte] = static_cast<std::uint8_t>((value >> (byte * 8u)) & 0xffu);
    }
}

void put_u32_le(std::vector<std::uint8_t>& bytes, std::size_t offset, std::uint32_t value) {
    for (std::size_t byte = 0; byte < 4u; ++byte) {
        bytes[offset + byte] = static_cast<std::uint8_t>((value >> (byte * 8u)) & 0xffu);
    }
}

void put_f64(std::vector<std::uint8_t>& bytes, std::size_t offset, double value) {
    std::uint64_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    put_u64_le(bytes, offset, bits);
}

void put_f32(std::vector<std::uint8_t>& bytes, std::size_t offset, float value) {
    std::uint32_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    put_u32_le(bytes, offset, bits);
}

void put_vec3(
    std::vector<std::uint8_t>& bytes,
    std::size_t base,
    const std::array<std::size_t, 3>& offsets,
    const std::array<double, 3>& values) {
    for (std::size_t component = 0; component < 3u; ++component) {
        put_f64(bytes, base + offsets[component], values[component]);
    }
}

std::vector<std::uint8_t> make_raw_bodies(
    const std::vector<BodyAccumulatorState>& accumulators) {
    std::vector<std::uint8_t> bytes(accumulators.size() * kBodyRecordSize, 0u);
    const std::array<float, 9> identity = {
        1.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f,
        0.0f, 0.0f, 1.0f,
    };
    for (std::size_t index = 0; index < accumulators.size(); ++index) {
        const std::size_t base = index * kBodyRecordSize;
        std::fill_n(
            bytes.begin() + static_cast<std::ptrdiff_t>(base),
            kBodyRecordSize,
            static_cast<std::uint8_t>(0x21u + index * 0x13u));
        put_vec3(bytes, base, body_record_offset::kOrigin,
            index == 0 ? std::array<double, 3>{1.0, 2.0, 3.0}
                       : std::array<double, 3>{-1.0, -2.0, -3.0});
        put_vec3(bytes, base, body_record_offset::kCrossVector,
            index == 0 ? std::array<double, 3>{0.1, 0.0, 0.0}
                       : std::array<double, 3>{0.2, 0.0, 0.0});
        put_vec3(bytes, base, body_record_offset::kPreparedVector,
            index == 0 ? std::array<double, 3>{10.0, 20.0, 30.0}
                       : std::array<double, 3>{5.0, 6.0, 7.0});
        put_vec3(bytes, base, body_record_offset::kAccumulatorA, accumulators[index].angular);
        put_vec3(bytes, base, body_record_offset::kAccumulatorB, accumulators[index].linear);
        put_vec3(bytes, base, body_record_offset::kMotionTriplet,
            index == 0 ? std::array<double, 3>{4.0, 5.0, 6.0}
                       : std::array<double, 3>{-4.0, -5.0, -6.0});
        put_f64(bytes, base + body_record_offset::kScalar0x90, index == 0 ? 0.5 : 0.25);
        put_vec3(bytes, base, body_record_offset::kReciprocalCoefficients,
            index == 0 ? std::array<double, 3>{2.0, 3.0, 5.0}
                       : std::array<double, 3>{1.0, 1.0, 1.0});
        for (std::size_t component = 0; component < identity.size(); ++component) {
            put_f32(bytes, base + body_record_offset::kBasis[component], identity[component]);
        }
    }
    return bytes;
}

BodyRecordBytes record_at(const std::vector<std::uint8_t>& bytes, std::size_t index) {
    BodyRecordBytes record{};
    const std::size_t base = index * kBodyRecordSize;
    std::copy_n(bytes.begin() + static_cast<std::ptrdiff_t>(base), kBodyRecordSize, record.begin());
    return record;
}

void require_close(double actual, double expected, const char* label) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > 1e-12) {
        throw std::runtime_error(label);
    }
}

Fun00763570PrecomputedInput make_longitudinal_input() {
    Fun00763570PrecomputedInput input{};
    for (std::size_t index = 0; index < kWheelLongitudinalCount; ++index) {
        auto& wheel = input.wheels[index];
        wheel.wheel_index = index;
        wheel.shared_velocity = {
            10.0 + static_cast<double>(index),
            20.0 + static_cast<double>(index),
            30.0 + static_cast<double>(index),
        };
        wheel.local_velocity = {
            1.0 + static_cast<double>(index),
            100.0 + static_cast<double>(index),
            200.0 + static_cast<double>(index),
        };
        wheel.reconstructed_world_velocity = {
            0.5 + 0.1 * static_cast<double>(index),
            1.0,
            1.5,
        };
    }
    input.rear_pair_average_enabled = true;
    input.mode = 0;
    input.global_config_byte = true;
    return input;
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        constexpr double timestep = 0.25;
        const auto source = make_frame();
        const auto relations = make_relations();
        const auto projection = make_projection(source, relations);
        const auto solver_topology = make_solver_topology(source, relations);
        const auto reset_state = make_reset_state();
        const auto raw = make_raw_bodies(projection.bodies);
        const auto longitudinal_input = make_longitudinal_input();

        bool provider_seen = false;
        std::size_t provider_calls = 0u;
        std::vector<BodyFrameIntegrationVector3d> rotation_inputs;
        const BodyBasisRotationCallback basis_provider =
            [&](const ConstraintRefreshFrame3f& basis,
                const BodyFrameIntegrationVector3d& rotation_increment) {
                if (!provider_seen) {
                    throw std::runtime_error(
                        "BODY integration ran before typed FUN_00763570 provider");
                }
                rotation_inputs.push_back(rotation_increment);
                return basis;
            };

        const auto joined =
            execute_fun_00765470_precomputed_longitudinal_feedback_join(
                [&] {
                    if (provider_seen) {
                        throw std::runtime_error(
                            "typed FUN_00763570 provider executed more than once");
                    }
                    provider_seen = true;
                    ++provider_calls;
                    return longitudinal_input;
                },
                source,
                relations,
                reset_state,
                solver_topology,
                projection,
                raw,
                timestep,
                basis_provider);

        if (!provider_seen || provider_calls != 1u ||
            joined.provider_call_count != 1u ||
            joined.half_step.wheel_shared_triplet_anchor_count != 1u) {
            throw std::runtime_error("Phase 686 provider/anchor count mismatch");
        }

        const auto& longitudinal = joined.longitudinal;
        require_close(longitudinal.reported_components[0], 1.0, "wheel 0 component mismatch");
        require_close(longitudinal.reported_components[1], 2.0, "wheel 1 component mismatch");
        require_close(longitudinal.reported_components[2], 3.5, "rear average component 2 mismatch");
        require_close(longitudinal.reported_components[3], 3.5, "rear average component 3 mismatch");
        for (std::size_t index = 0; index < kWheelLongitudinalCount; ++index) {
            const auto& observed = longitudinal.observations[index];
            if (observed.wheel_index != index) {
                throw std::runtime_error("Phase 686 wheel order mismatch");
            }
            for (std::size_t component = 0; component < 3u; ++component) {
                require_close(
                    observed.shared_velocity_after[component],
                    longitudinal_input.wheels[index].shared_velocity[component] -
                        longitudinal_input.wheels[index].reconstructed_world_velocity[component],
                    "Phase 686 subtraction mismatch");
            }
        }

        const auto& feedback = joined.half_step.feedback_integration;
        if (feedback.reset_call_count != 6u || feedback.reset_node_count != 6u ||
            feedback.solved_vector.size() != 6u ||
            feedback.max_matrix_anchor_error != 0.0) {
            throw std::runtime_error("Phase 686 solver metadata mismatch");
        }
        for (double value : feedback.solved_vector) {
            require_close(value, 0.0, "Phase 686 solved vector mismatch");
        }
        if (rotation_inputs.size() != 2u) {
            throw std::runtime_error("Phase 686 basis provider call count mismatch");
        }
        require_close(rotation_inputs[0][0], 0.025, "first rotation increment mismatch");
        require_close(rotation_inputs[1][0], 0.05, "second rotation increment mismatch");

        const auto body0 = decode_fun_007bab70_body_record(record_at(feedback.body_bytes, 0u));
        const std::array<double, 3> expected_origin = {2.0, 3.25, 4.5};
        const std::array<double, 3> expected_motion = {4.5, 5.625, 6.75};
        const std::array<double, 3> expected_prepared = {10.25, 20.5, 30.75};
        const std::array<double, 3> expected_cross = {20.5, 61.5, 153.75};
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(body0.origin[component], expected_origin[component], "joined origin mismatch");
            require_close(body0.motion_triplet[component], expected_motion[component], "joined motion mismatch");
            require_close(body0.prepared_vector[component], expected_prepared[component], "joined prepared mismatch");
            require_close(body0.cross_vector[component], expected_cross[component], "joined cross mismatch");
        }

        bool missing_provider_rejected = false;
        try {
            (void)execute_fun_00765470_precomputed_longitudinal_feedback_join(
                {}, source, relations, reset_state, solver_topology, projection,
                raw, timestep, basis_provider);
        } catch (const std::invalid_argument&) {
            missing_provider_rejected = true;
        }
        if (!missing_provider_rejected) {
            throw std::runtime_error("missing Phase 686 provider accepted");
        }

        bool malformed_wheel_rejected = false;
        try {
            (void)execute_fun_00765470_precomputed_longitudinal_feedback_join(
                [&] {
                    auto invalid = longitudinal_input;
                    invalid.wheels[2].wheel_index = 9u;
                    return invalid;
                },
                source, relations, reset_state, solver_topology, projection,
                raw, timestep, basis_provider);
        } catch (const std::invalid_argument&) {
            malformed_wheel_rejected = true;
        }
        if (!malformed_wheel_rejected) {
            throw std::runtime_error("malformed Phase 686 wheel order accepted");
        }

        bool nonfinite_precomputed_rejected = false;
        try {
            (void)execute_fun_00765470_precomputed_longitudinal_feedback_join(
                [&] {
                    auto invalid = longitudinal_input;
                    invalid.wheels[1].local_velocity[0] =
                        std::numeric_limits<double>::infinity();
                    return invalid;
                },
                source, relations, reset_state, solver_topology, projection,
                raw, timestep, basis_provider);
        } catch (const std::invalid_argument&) {
            nonfinite_precomputed_rejected = true;
        }
        if (!nonfinite_precomputed_rejected) {
            throw std::runtime_error("non-finite Phase 686 transform input accepted");
        }

        std::cout
            << "{\"format\":\"" << kNativeFun00763570PrecomputedFeedbackJoinFormat << "\","
            << "\"ready\":true,"
            << "\"provider_call_count\":" << joined.provider_call_count << ","
            << "\"native_fun_00763570_batch_used\":true,"
            << "\"phase685_join_reused\":true,"
            << "\"retail_wheel_order_preserved\":true,"
            << "\"rear_pair_average_preserved\":true,"
            << "\"persistent_body_result_preserved\":true,"
            << "\"fun_007af010_implemented\":false,"
            << "\"complete_fun_00763570_semantics\":false,"
            << "\"complete_fun_00765470_semantics\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
