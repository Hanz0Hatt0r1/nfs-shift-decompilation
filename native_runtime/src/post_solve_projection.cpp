#include "shift_post_solve_projection.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace shift::runtime::physics {
namespace {

constexpr uint32_t kPacketVersion = 1u;
constexpr uint32_t kProofSolvedVector = 1u << 0;
constexpr uint32_t kProofBodyState = 1u << 1;
constexpr uint32_t kProofConstraintRows = 1u << 2;
constexpr uint32_t kRequiredProofFlags =
    kProofSolvedVector | kProofBodyState | kProofConstraintRows;

#pragma pack(push, 1)
struct ProjectionHeader {
    char magic[4];
    uint32_t version;
    uint32_t body_count;
    uint32_t scalar_count;
    uint32_t joint_count;
    uint32_t hinge_count;
    uint32_t bar_count;
    uint32_t proof_flags;
    uint32_t reserved;
};
struct RecordHead {
    uint32_t positive_body;
    uint32_t negative_body;
    uint32_t scalar_base;
};
#pragma pack(pop)

static_assert(sizeof(ProjectionHeader) == 36);
static_assert(sizeof(RecordHead) == 12);

std::vector<uint8_t> read_file(const std::string& path) {
    std::ifstream stream(path, std::ios::binary | std::ios::ate);
    if (!stream) {
        throw std::runtime_error(
            "cannot open post-solve projection packet: " + path);
    }
    const std::streamsize size = stream.tellg();
    if (size <= 0) {
        throw std::runtime_error(
            "post-solve projection packet is empty");
    }
    stream.seekg(0);
    std::vector<uint8_t> data(static_cast<std::size_t>(size));
    if (!stream.read(
            reinterpret_cast<char*>(data.data()),
            size)) {
        throw std::runtime_error(
            "cannot read post-solve projection packet");
    }
    return data;
}

template <typename T>
T read_scalar(
    const std::vector<uint8_t>& data,
    std::size_t& offset,
    const char* label) {

    if (offset > data.size() ||
        data.size() - offset < sizeof(T)) {
        throw std::runtime_error(
            std::string("post-solve projection truncated at ") + label);
    }
    T value{};
    std::memcpy(&value, data.data() + offset, sizeof(T));
    offset += sizeof(T);
    return value;
}

double read_finite_double(
    const std::vector<uint8_t>& data,
    std::size_t& offset,
    const char* label) {

    const double value =
        read_scalar<double>(data, offset, label);
    if (!std::isfinite(value)) {
        throw std::runtime_error(
            std::string("post-solve projection non-finite ") + label);
    }
    return value;
}

std::array<double, 3> read_vec3(
    const std::vector<uint8_t>& data,
    std::size_t& offset,
    const char* label) {

    return {
        read_finite_double(data, offset, label),
        read_finite_double(data, offset, label),
        read_finite_double(data, offset, label),
    };
}

BodyAccumulatorState read_body(
    const std::vector<uint8_t>& data,
    std::size_t& offset) {

    return {
        read_vec3(data, offset, "body angular"),
        read_vec3(data, offset, "body linear"),
    };
}

void validate_head(
    const RecordHead& head,
    std::size_t body_count,
    std::size_t scalar_count,
    std::size_t width,
    const char* label) {

    if (head.positive_body >= body_count ||
        head.negative_body >= body_count) {
        throw std::runtime_error(
            std::string(label) + " body index out of range");
    }
    if (head.scalar_base >= scalar_count ||
        width > scalar_count - head.scalar_base) {
        throw std::runtime_error(
            std::string(label) + " scalar range out of range");
    }
}

std::array<double, 3> cross(
    const std::array<double, 3>& a,
    const std::array<double, 3>& b) {

    return {
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    };
}

void apply_body_delta(
    BodyAccumulatorState& body,
    const std::array<double, 3>& lever,
    const std::array<double, 3>& contribution,
    double sign) {

    const auto angular = cross(lever, contribution);
    for (std::size_t i = 0; i < 3; ++i) {
        body.linear[i] += sign * contribution[i];
        body.angular[i] += sign * angular[i];
    }
}

}  // namespace

PreparedPostSolveBodyProjection load_prepared_post_solve_body_projection(
    const std::string& path) {

    const auto data = read_file(path);
    if (data.size() < sizeof(ProjectionHeader)) {
        throw std::runtime_error(
            "post-solve projection packet header truncated");
    }

    ProjectionHeader header{};
    std::memcpy(&header, data.data(), sizeof(header));
    if (std::memcmp(header.magic, "SBPS", 4) != 0 ||
        header.version != kPacketVersion) {
        throw std::runtime_error(
            "unsupported post-solve projection packet");
    }
    if (header.body_count == 0u ||
        header.body_count > 4096u ||
        header.scalar_count == 0u ||
        header.scalar_count > 4096u) {
        throw std::runtime_error(
            "post-solve projection cardinality out of range");
    }
    if ((header.proof_flags & kRequiredProofFlags) !=
            kRequiredProofFlags ||
        header.reserved != 0u) {
        throw std::runtime_error(
            "post-solve projection runtime proofs are incomplete");
    }

    PreparedPostSolveBodyProjection out{};
    std::size_t offset = sizeof(ProjectionHeader);

    out.bodies.reserve(header.body_count);
    for (uint32_t i = 0; i < header.body_count; ++i) {
        out.bodies.push_back(read_body(data, offset));
    }

    out.solver_vector.reserve(header.scalar_count);
    for (uint32_t i = 0; i < header.scalar_count; ++i) {
        out.solver_vector.push_back(
            read_finite_double(data, offset, "solver scalar"));
    }

    out.joints.reserve(header.joint_count);
    for (uint32_t i = 0; i < header.joint_count; ++i) {
        const RecordHead head =
            read_scalar<RecordHead>(data, offset, "joint head");
        validate_head(
            head, header.body_count, header.scalar_count, 3u, "joint");
        out.joints.push_back({
            head.positive_body,
            head.negative_body,
            head.scalar_base,
            read_vec3(data, offset, "joint positive lever"),
            read_vec3(data, offset, "joint negative lever"),
        });
    }

    out.hinges.reserve(header.hinge_count);
    for (uint32_t i = 0; i < header.hinge_count; ++i) {
        const RecordHead head =
            read_scalar<RecordHead>(data, offset, "hinge head");
        validate_head(
            head, header.body_count, header.scalar_count, 2u, "hinge");
        out.hinges.push_back({
            head.positive_body,
            head.negative_body,
            head.scalar_base,
            read_vec3(data, offset, "hinge positive angular row"),
            read_vec3(data, offset, "hinge positive linear row"),
            read_vec3(data, offset, "hinge negative angular row"),
            read_vec3(data, offset, "hinge negative linear row"),
        });
    }

    out.bars.reserve(header.bar_count);
    for (uint32_t i = 0; i < header.bar_count; ++i) {
        const RecordHead head =
            read_scalar<RecordHead>(data, offset, "bar head");
        validate_head(
            head, header.body_count, header.scalar_count, 1u, "bar");
        out.bars.push_back({
            head.positive_body,
            head.negative_body,
            head.scalar_base,
            read_vec3(data, offset, "bar positive lever"),
            read_vec3(data, offset, "bar negative lever"),
            read_vec3(data, offset, "bar direction"),
        });
    }

    out.expected_bodies.reserve(header.body_count);
    for (uint32_t i = 0; i < header.body_count; ++i) {
        out.expected_bodies.push_back(read_body(data, offset));
    }

    if (offset != data.size()) {
        throw std::runtime_error(
            "post-solve projection packet has trailing bytes");
    }
    return out;
}

PostSolveBodyProjectionResult execute_post_solve_body_projection_with_state(
    const PreparedPostSolveBodyProjection& projection,
    const std::vector<double>& solver_vector,
    const std::vector<BodyAccumulatorState>& initial_bodies,
    double tolerance) {

    if (!std::isfinite(tolerance) || tolerance <= 0.0) {
        throw std::invalid_argument(
            "post-solve projection tolerance must be finite and positive");
    }
    if (projection.bodies.size() != projection.expected_bodies.size()) {
        throw std::runtime_error(
            "post-solve projection body/oracle cardinality mismatch");
    }
    if (solver_vector.size() != projection.solver_vector.size()) {
        throw std::runtime_error(
            "post-solve solved-vector cardinality mismatch");
    }
    if (initial_bodies.size() != projection.bodies.size()) {
        throw std::runtime_error(
            "post-solve persistent BODY cardinality mismatch");
    }
    for (const auto& body : initial_bodies) {
        for (double value : body.angular) {
            if (!std::isfinite(value)) {
                throw std::runtime_error(
                    "post-solve persistent BODY contains non-finite angular value");
            }
        }
        for (double value : body.linear) {
            if (!std::isfinite(value)) {
                throw std::runtime_error(
                    "post-solve persistent BODY contains non-finite linear value");
            }
        }
    }

    double max_join_error = 0.0;
    for (std::size_t i = 0; i < solver_vector.size(); ++i) {
        const double actual = solver_vector[i];
        const double expected = projection.solver_vector[i];
        if (!std::isfinite(actual)) {
            throw std::runtime_error(
                "post-solve solved-vector contains non-finite value");
        }
        const double error = std::abs(actual - expected);
        max_join_error = std::max(max_join_error, error);
        const double limit =
            tolerance * std::max(1.0, std::abs(expected));
        if (error > limit) {
            throw std::runtime_error(
                "post-solve solved-vector join mismatch");
        }
    }

    std::vector<BodyAccumulatorState> bodies = initial_bodies;

    for (const auto& row : projection.joints) {
        const std::array<double, 3> solution = {
            solver_vector[row.scalar_base + 0u],
            solver_vector[row.scalar_base + 1u],
            solver_vector[row.scalar_base + 2u],
        };
        apply_body_delta(
            bodies[row.positive_body],
            row.positive_lever_arm,
            solution,
            1.0);
        apply_body_delta(
            bodies[row.negative_body],
            row.negative_lever_arm,
            solution,
            -1.0);
    }

    for (const auto& row : projection.hinges) {
        const double s0 =
            solver_vector[row.scalar_base + 0u];
        const double s1 =
            solver_vector[row.scalar_base + 1u];
        for (std::size_t component = 0; component < 3; ++component) {
            bodies[row.positive_body].angular[component] +=
                row.positive_angular_row[component] * s0 +
                row.positive_linear_row[component] * s1;
            bodies[row.negative_body].angular[component] -=
                row.negative_angular_row[component] * s0 +
                row.negative_linear_row[component] * s1;
        }
    }

    for (const auto& row : projection.bars) {
        const double scalar =
            solver_vector[row.scalar_base];
        const std::array<double, 3> contribution = {
            row.direction[0] * scalar,
            row.direction[1] * scalar,
            row.direction[2] * scalar,
        };
        apply_body_delta(
            bodies[row.positive_body],
            row.positive_lever_arm,
            contribution,
            1.0);
        apply_body_delta(
            bodies[row.negative_body],
            row.negative_lever_arm,
            contribution,
            -1.0);
    }

    double max_error = 0.0;
    double max_delta_error = 0.0;
    for (std::size_t body = 0; body < bodies.size(); ++body) {
        for (std::size_t component = 0; component < 3; ++component) {
            for (int channel = 0; channel < 2; ++channel) {
                const double actual =
                    channel == 0
                        ? bodies[body].angular[component]
                        : bodies[body].linear[component];
                const double initial =
                    channel == 0
                        ? initial_bodies[body].angular[component]
                        : initial_bodies[body].linear[component];
                const double prepared_initial =
                    channel == 0
                        ? projection.bodies[body].angular[component]
                        : projection.bodies[body].linear[component];
                const double prepared_expected =
                    channel == 0
                        ? projection.expected_bodies[body].angular[component]
                        : projection.expected_bodies[body].linear[component];
                const double expected_delta =
                    prepared_expected - prepared_initial;
                const double actual_delta = actual - initial;
                const double delta_error =
                    std::abs(actual_delta - expected_delta);
                const double expected = initial + expected_delta;
                const double error = std::abs(actual - expected);
                max_error = std::max(max_error, error);
                max_delta_error =
                    std::max(max_delta_error, delta_error);
                const double limit =
                    tolerance * std::max(1.0, std::abs(expected_delta));
                if (!std::isfinite(actual) ||
                    delta_error > limit ||
                    error > tolerance * std::max(1.0, std::abs(expected))) {
                    throw std::runtime_error(
                        "post-solve projection persistent delta/oracle mismatch");
                }
            }
        }
    }

    return {
        std::move(bodies),
        max_error,
        max_join_error,
        max_delta_error,
    };
}

PostSolveBodyProjectionResult execute_post_solve_body_projection_with_solution(
    const PreparedPostSolveBodyProjection& projection,
    const std::vector<double>& solver_vector,
    double tolerance) {

    return execute_post_solve_body_projection_with_state(
        projection,
        solver_vector,
        projection.bodies,
        tolerance);
}

PostSolveBodyProjectionResult execute_prepared_post_solve_body_projection(
    const PreparedPostSolveBodyProjection& projection,
    double tolerance) {

    return execute_post_solve_body_projection_with_solution(
        projection,
        projection.solver_vector,
        tolerance);
}

}  // namespace shift::runtime::physics
