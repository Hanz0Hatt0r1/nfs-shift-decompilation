#include "shift_body_feedback_record_bridge.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
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
        body.row_indices = {0, 1, 2, 3, 4, 5};
        body.constraints.scalar_count = 6;
        body.constraints.body_position = {
            static_cast<double>(index), 0.0, 0.0};
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
        bar.side_bias = 0.0;
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
        jr.positive.body_index,
        jr.negative.body_index,
        jp.scalar_base,
        jp.position,
        jn.position,
    });

    const auto& hr = relations.hinges[0];
    const auto& hp = refreshed.frame.bodies[hr.positive.body_index]
        .constraints.hinges[hr.positive.sample_index];
    const auto& hn = refreshed.frame.bodies[hr.negative.body_index]
        .constraints.hinges[hr.negative.sample_index];
    projection.hinges.push_back({
        hr.positive.body_index,
        hr.negative.body_index,
        hp.scalar_base,
        hp.angular,
        hp.linear,
        hn.angular,
        hn.linear,
    });

    const auto& br = relations.bars[0];
    const auto& bp = refreshed.frame.bodies[br.positive.body_index]
        .constraints.bars[br.positive.sample_index];
    const auto& bn = refreshed.frame.bodies[br.negative.body_index]
        .constraints.bars[br.negative.sample_index];
    projection.bars.push_back({
        br.positive.body_index,
        br.negative.body_index,
        bp.scalar_base,
        bp.point,
        bn.point,
        bp.direction,
    });
    return projection;
}

PreparedBuiltinSolverFrame make_solver_topology(
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations) {
    const auto refreshed = refresh_generated_body_constraint_frame(source, relations);
    const auto generated = execute_prepared_generated_body_constraint_frame(
        refreshed.frame);

    PreparedBuiltinSolverFrame frame{};
    frame.matrix.assign(6, std::vector<double>(6, 0.0));
    for (std::size_t row = 0; row < 6; ++row) {
        for (std::size_t column = 0; column < 6; ++column) {
            frame.matrix[row][column] =
                generated.solver_matrix[row * 6 + column];
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

void put_u64_le(
    std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    std::uint64_t value) {
    for (std::size_t byte = 0; byte < 8u; ++byte) {
        bytes[offset + byte] = static_cast<std::uint8_t>(
            (value >> (byte * 8u)) & 0xffu);
    }
}

void put_f64(
    std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    double value) {
    std::uint64_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    put_u64_le(bytes, offset, bits);
}

std::vector<std::uint8_t> make_raw_bodies(
    const std::vector<BodyAccumulatorState>& bodies) {
    std::vector<std::uint8_t> bytes(bodies.size() * kBodyRecordSize, 0u);
    for (std::size_t index = 0; index < bodies.size(); ++index) {
        const std::size_t base = index * kBodyRecordSize;
        std::fill_n(
            bytes.begin() + static_cast<std::ptrdiff_t>(base),
            kBodyRecordSize,
            static_cast<std::uint8_t>(0x31u + index * 0x11u));
        for (std::size_t component = 0; component < 3u; ++component) {
            put_f64(
                bytes,
                base + body_record_offset::kAccumulatorA[component],
                bodies[index].angular[component]);
            put_f64(
                bytes,
                base + body_record_offset::kAccumulatorB[component],
                bodies[index].linear[component]);
        }
    }
    return bytes;
}

bool is_accumulator_byte(std::size_t local_index) {
    for (const auto offset : body_record_offset::kAccumulatorA) {
        if (local_index >= offset && local_index < offset + 8u) {
            return true;
        }
    }
    for (const auto offset : body_record_offset::kAccumulatorB) {
        if (local_index >= offset && local_index < offset + 8u) {
            return true;
        }
    }
    return false;
}

void require_close(double actual, double expected, const char* label) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > 1e-12) {
        throw std::runtime_error(label);
    }
}

void require_same_accumulators(
    const std::vector<BodyAccumulatorState>& actual,
    const std::vector<BodyAccumulatorState>& expected,
    const char* label) {
    if (actual.size() != expected.size()) {
        throw std::runtime_error(label);
    }
    for (std::size_t body = 0; body < actual.size(); ++body) {
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                actual[body].angular[component],
                expected[body].angular[component],
                label);
            require_close(
                actual[body].linear[component],
                expected[body].linear[component],
                label);
        }
    }
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        const auto source = make_frame();
        const auto relations = make_relations();
        const auto projection = make_projection(source, relations);
        const auto solver_topology = make_solver_topology(source, relations);
        const auto reset_state = make_reset_state();

        auto current_bodies = projection.bodies;
        current_bodies[0].angular[1] += 7.0;
        current_bodies[1].linear[0] -= 3.0;
        const auto raw = make_raw_bodies(current_bodies);

        const auto decoded = decode_body_accumulators_from_buffer(raw, 2u);
        require_same_accumulators(
            decoded,
            current_bodies,
            "raw BODY accumulator decode mismatch");

        auto replacement = current_bodies;
        replacement[0].angular[0] += 100.0;
        replacement[1].linear[2] -= 50.0;
        const auto replaced = apply_body_accumulators_to_buffer(raw, replacement);
        for (std::size_t body = 0; body < 2u; ++body) {
            const std::size_t base = body * kBodyRecordSize;
            for (std::size_t local = 0; local < kBodyRecordSize; ++local) {
                if (!is_accumulator_byte(local) &&
                    replaced[base + local] != raw[base + local]) {
                    throw std::runtime_error(
                        "BODY feedback bridge changed unrelated record byte");
                }
            }
        }
        require_same_accumulators(
            decode_body_accumulators_from_buffer(replaced, 2u),
            replacement,
            "raw BODY accumulator write mismatch");

        const auto step = execute_body_state_feedback_raw_step(
            source,
            relations,
            reset_state,
            solver_topology,
            projection,
            raw);
        if (step.reset_call_count != 6u ||
            step.reset_node_count != 6u ||
            step.solved_vector.size() != 6u ||
            step.generated_rhs.size() != 6u ||
            step.max_matrix_anchor_error != 0.0) {
            throw std::runtime_error(
                "raw BODY feedback solver metadata mismatch");
        }
        for (double value : step.solved_vector) {
            require_close(value, 0.0, "all-reset raw BODY solution must be zero");
        }
        require_same_accumulators(
            decode_body_accumulators_from_buffer(step.body_bytes, 2u),
            current_bodies,
            "zero-solution raw BODY feedback changed accumulators");
        for (std::size_t body = 0; body < 2u; ++body) {
            const std::size_t base = body * kBodyRecordSize;
            for (std::size_t local = 0; local < kBodyRecordSize; ++local) {
                if (!is_accumulator_byte(local) &&
                    step.body_bytes[base + local] != raw[base + local]) {
                    throw std::runtime_error(
                        "solver feedback changed unrelated BODY storage");
                }
            }
        }

        bool size_mismatch_rejected = false;
        try {
            (void)decode_body_accumulators_from_buffer(raw, 3u);
        } catch (const std::invalid_argument&) {
            size_mismatch_rejected = true;
        }
        if (!size_mismatch_rejected) {
            throw std::runtime_error("BODY feedback size mismatch accepted");
        }

        bool non_finite_rejected = false;
        try {
            auto bad = raw;
            put_f64(
                bad,
                body_record_offset::kAccumulatorA[0],
                std::numeric_limits<double>::quiet_NaN());
            (void)execute_body_state_feedback_raw_step(
                source,
                relations,
                reset_state,
                solver_topology,
                projection,
                bad);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error("non-finite raw BODY accumulator accepted");
        }

        bool non_finite_writer_rejected = false;
        try {
            auto bad_bodies = current_bodies;
            bad_bodies[1].linear[2] =
                std::numeric_limits<double>::infinity();
            (void)apply_body_accumulators_to_buffer(raw, bad_bodies);
        } catch (const std::invalid_argument&) {
            non_finite_writer_rejected = true;
        }
        if (!non_finite_writer_rejected) {
            throw std::runtime_error("non-finite BODY feedback result accepted");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeBodyFeedbackRecordBridge/1\","
            << "\"ready\":true,"
            << "\"body_record_size\":" << kBodyRecordSize << ","
            << "\"body_count\":2,"
            << "\"accumulator_writer_bytes\":48,"
            << "\"raw_feedback_seed_proven\":true,"
            << "\"post_solve_accumulator_write_proven\":true,"
            << "\"unrelated_bytes_preserved\":true,"
            << "\"size_mismatch_rejected\":true,"
            << "\"non_finite_rejected\":true,"
            << "\"body_integration_scheduled\":false,"
            << "\"runtime_scheduling_proven\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}
