#pragma once

#include "runtime_state.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <utility>
#include <vector>

namespace shift::runtime::test_fixture {

using namespace physics;

inline PreparedGeneratedBodyConstraintFrame make_frame() {
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

inline PreparedConstraintSampleRelationFrame make_relations() {
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

inline PreparedPostSolveBodyProjection make_projection(
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

inline PreparedBuiltinSolverFrame make_solver_topology(
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

inline PreparedConstraintRelationResetFrame make_reset_state() {
    PreparedConstraintRelationResetFrame reset{};
    reset.joint_state_bit0 = {1u};
    reset.hinge_state_bit0 = {1u};
    reset.bar_state_bit0 = {1u};
    return reset;
}

inline void put_u64_le(
    std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    std::uint64_t value) {
    for (std::size_t byte = 0; byte < 8u; ++byte) {
        bytes[offset + byte] =
            static_cast<std::uint8_t>((value >> (byte * 8u)) & 0xffu);
    }
}

inline void put_u32_le(
    std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    std::uint32_t value) {
    for (std::size_t byte = 0; byte < 4u; ++byte) {
        bytes[offset + byte] =
            static_cast<std::uint8_t>((value >> (byte * 8u)) & 0xffu);
    }
}

inline void put_f64(
    std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    double value) {
    std::uint64_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    put_u64_le(bytes, offset, bits);
}

inline void put_f32(
    std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    float value) {
    std::uint32_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    put_u32_le(bytes, offset, bits);
}

inline void put_vec3(
    std::vector<std::uint8_t>& bytes,
    std::size_t base,
    const std::array<std::size_t, 3>& offsets,
    const std::array<double, 3>& values) {
    for (std::size_t component = 0; component < 3u; ++component) {
        put_f64(bytes, base + offsets[component], values[component]);
    }
}

inline std::vector<std::uint8_t> make_raw_bodies(
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

inline BodyRecordBytes record_at(
    const std::vector<std::uint8_t>& bytes,
    std::size_t index) {
    BodyRecordBytes record{};
    const std::size_t base = index * kBodyRecordSize;
    std::copy_n(
        bytes.begin() + static_cast<std::ptrdiff_t>(base),
        kBodyRecordSize,
        record.begin());
    return record;
}

inline void require_close(double actual, double expected, const char* label) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > 1e-12) {
        throw std::runtime_error(label);
    }
}

inline Fun00763570MachineInput make_machine_input() {
    Fun00763570MachineInput input{};
    const ConstraintRefreshFrame3f diagonal = {
        2.0f, 0.0f, 0.0f,
        0.0f, 3.0f, 0.0f,
        0.0f, 0.0f, 4.0f,
    };
    for (std::size_t index = 0; index < kWheelLongitudinalCount; ++index) {
        input.wheels[index].wheel_index = index;
        input.wheels[index].body_frame = diagonal;
        input.wheels[index].shared_velocity = {
            10.0 + static_cast<double>(index),
            20.0 + static_cast<double>(index),
            30.0 + static_cast<double>(index),
        };
    }
    input.rear_pair_average_enabled = true;
    input.mode = 0;
    input.global_config_byte = true;
    return input;
}

inline Fun0076d100AnchorProvider make_pass_provider() {
    return [](std::size_t) {
        Fun0076d100AnchorCallbacks callbacks{};
        callbacks.contact_factor = [] {};
        callbacks.wheel_update = [] {};
        callbacks.contact_response = [] {};
        callbacks.contact_outer = [] {};
        callbacks.motion_read_gate = [] {};
        return callbacks;
    };
}

inline ContactOuterKernelInput make_contact_outer_input() {
    ContactOuterKernelInput input{};
    input.planar_delta = {10.0, 0.0, 0.0};
    input.previous_distance_state = 8.0;
    input.distance_filter_cap = 1.0;
    input.speed_x = 20.0;
    input.speed_z = 0.0;
    input.surface_scalar = 10.0;
    input.base_scalar = 4.0;
    input.projected_scalar = 1.0;
    input.alignment_scalar = 0.5;
    input.param_3 = 2.0;
    return input;
}

inline Fun0076d100ContactOuterProvider make_contact_outer_pass_provider(
    std::size_t* input_provider_calls = nullptr) {
    return [input_provider_calls](std::size_t) {
        Fun0076d100ContactOuterProviderCallbacks callbacks{};
        callbacks.contact_factor = [] {};
        callbacks.wheel_update = [] {};
        callbacks.contact_response = [] {};
        callbacks.contact_outer_input_provider = [input_provider_calls] {
            if (input_provider_calls != nullptr) {
                ++(*input_provider_calls);
            }
            return make_contact_outer_input();
        };
        callbacks.motion_read_gate = [] {};
        return callbacks;
    };
}

}  // namespace shift::runtime::test_fixture
