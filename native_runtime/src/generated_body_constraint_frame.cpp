#include "shift_generated_body_constraint_frame.hpp"

#include "shift_body_solver_export.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace shift::runtime::physics {
namespace {

constexpr uint32_t kPacketVersion = 1u;
constexpr uint32_t kProofSampleValues = 1u << 0;
constexpr uint32_t kProofBodyOrder = 1u << 1;
constexpr uint32_t kProofRowLayout = 1u << 2;
constexpr uint32_t kProofProviderAbsent = 1u << 3;
constexpr uint32_t kRequiredProofFlags =
    kProofSampleValues |
    kProofBodyOrder |
    kProofRowLayout |
    kProofProviderAbsent;

#pragma pack(push, 1)
struct FrameHeader {
    char magic[4];
    uint32_t version;
    uint32_t body_count;
    uint32_t scalar_count;
    uint32_t matrix_double_count;
    uint32_t proof_flags;
    uint32_t reserved;
};

struct BodyHead {
    uint32_t body_index;
    uint32_t joint_count;
    uint32_t hinge_count;
    uint32_t bar_count;
    uint32_t row_index_count;
    uint32_t reserved;
};
#pragma pack(pop)

static_assert(sizeof(FrameHeader) == 28);
static_assert(sizeof(BodyHead) == 24);

std::vector<uint8_t> read_file(const std::string& path) {
    std::ifstream stream(path, std::ios::binary | std::ios::ate);
    if (!stream) {
        throw std::runtime_error(
            "cannot open generated BODY constraint packet: " + path);
    }
    const std::streamsize size = stream.tellg();
    if (size <= 0) {
        throw std::runtime_error(
            "generated BODY constraint packet is empty");
    }
    stream.seekg(0);
    std::vector<uint8_t> data(static_cast<std::size_t>(size));
    if (!stream.read(
            reinterpret_cast<char*>(data.data()),
            size)) {
        throw std::runtime_error(
            "cannot read generated BODY constraint packet");
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
            std::string(
                "generated BODY constraint packet truncated at ") +
            label);
    }
    T value{};
    std::memcpy(
        &value,
        data.data() + offset,
        sizeof(T));
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
            std::string(
                "generated BODY constraint non-finite ") +
            label);
    }
    return value;
}

float read_finite_float(
    const std::vector<uint8_t>& data,
    std::size_t& offset,
    const char* label) {

    const float value =
        read_scalar<float>(data, offset, label);
    if (!std::isfinite(value)) {
        throw std::runtime_error(
            std::string(
                "generated BODY constraint non-finite ") +
            label);
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

std::uint8_t read_side_flag(
    const std::vector<uint8_t>& data,
    std::size_t& offset,
    const char* label) {

    const std::uint8_t flag =
        read_scalar<std::uint8_t>(
            data, offset, label);
    if (flag > 1u) {
        throw std::runtime_error(
            std::string(label) +
            " must be 0 or 1");
    }
    for (int index = 0; index < 3; ++index) {
        const std::uint8_t padding =
            read_scalar<std::uint8_t>(
                data, offset, "sample padding");
        if (padding != 0u) {
            throw std::runtime_error(
                "generated BODY sample padding must be zero");
        }
    }
    return flag;
}

double compare_join_value(
    double actual,
    double expected,
    double tolerance,
    const char* label) {

    if (!std::isfinite(actual) ||
        !std::isfinite(expected)) {
        throw std::runtime_error(
            std::string(label) + " contains non-finite value");
    }
    const double error = std::abs(actual - expected);
    const double limit =
        tolerance * std::max(1.0, std::abs(expected));
    if (error > limit) {
        throw std::runtime_error(
            std::string(label) + " join mismatch");
    }
    return error;
}

}  // namespace

PreparedGeneratedBodyConstraintFrame
load_prepared_generated_body_constraint_frame(
    const std::string& path) {

    const auto data = read_file(path);
    if (data.size() < sizeof(FrameHeader)) {
        throw std::runtime_error(
            "generated BODY constraint header truncated");
    }

    FrameHeader header{};
    std::memcpy(
        &header,
        data.data(),
        sizeof(header));
    if (std::memcmp(header.magic, "GBCF", 4) != 0 ||
        header.version != kPacketVersion) {
        throw std::runtime_error(
            "unsupported generated BODY constraint packet");
    }
    if (header.body_count == 0u ||
        header.body_count > 4096u ||
        header.scalar_count == 0u ||
        header.scalar_count > 4096u) {
        throw std::runtime_error(
            "generated BODY constraint cardinality out of range");
    }
    const uint64_t matrix_count =
        static_cast<uint64_t>(header.scalar_count) *
        static_cast<uint64_t>(header.scalar_count);
    if (matrix_count != header.matrix_double_count) {
        throw std::runtime_error(
            "generated BODY constraint matrix count is not N squared");
    }
    if ((header.proof_flags & kRequiredProofFlags) !=
            kRequiredProofFlags ||
        header.reserved != 0u) {
        throw std::runtime_error(
            "generated BODY constraint runtime proofs are incomplete");
    }

    PreparedGeneratedBodyConstraintFrame frame{};
    frame.scalar_count = header.scalar_count;
    frame.matrix_double_count =
        header.matrix_double_count;
    frame.bodies.reserve(header.body_count);

    std::size_t offset = sizeof(FrameHeader);
    for (uint32_t ordinal = 0;
         ordinal < header.body_count;
         ++ordinal) {
        const BodyHead head =
            read_scalar<BodyHead>(
                data, offset, "BODY header");
        if (head.body_index != ordinal ||
            head.row_index_count != header.scalar_count ||
            head.reserved != 0u) {
            throw std::runtime_error(
                "generated BODY constraint order/layout mismatch");
        }
        if (head.joint_count > 4096u ||
            head.hinge_count > 4096u ||
            head.bar_count > 4096u) {
            throw std::runtime_error(
                "generated BODY sample count out of range");
        }

        GeneratedBodySolverExportInput row{};
        row.body_index = ordinal;
        row.constraints.scalar_count =
            header.scalar_count;
        row.matrix_double_count =
            header.matrix_double_count;
        row.provider_present = false;

        row.constraints.body_position =
            read_vec3(data, offset, "BODY position");
        row.constraints.preprojection.body_correction =
            read_vec3(data, offset, "BODY correction");
        row.constraints.preprojection.body_axis =
            read_vec3(data, offset, "BODY axis");
        row.constraints.preprojection.angular_state =
            read_vec3(data, offset, "BODY angular state");
        row.constraints.preprojection.linear_state =
            read_vec3(data, offset, "BODY linear state");
        row.constraints.preprojection.inverse_scalar =
            read_finite_double(
                data, offset, "BODY inverse scalar");
        for (float& value :
             row.constraints.preprojection.body_frame) {
            value = read_finite_float(
                data, offset, "BODY frame");
        }
        for (auto& tensor_row :
             row.constraints.body_tensor) {
            for (double& value : tensor_row) {
                value = read_finite_double(
                    data, offset, "BODY tensor");
            }
        }
        row.constraints.scales.linear_scale =
            read_finite_double(
                data, offset, "BODY linear scale");
        row.constraints.scales.quadratic_scale =
            read_finite_double(
                data, offset, "BODY quadratic scale");

        row.row_indices.reserve(header.scalar_count);
        for (uint32_t index = 0;
             index < header.scalar_count;
             ++index) {
            row.row_indices.push_back(
                read_scalar<uint32_t>(
                    data, offset, "BODY row index"));
        }

        row.constraints.joints.reserve(head.joint_count);
        for (uint32_t index = 0;
             index < head.joint_count;
             ++index) {
            PreparedJointSample sample{};
            sample.position =
                read_vec3(data, offset, "JOINT position");
            sample.scalar_base =
                read_scalar<uint32_t>(
                    data, offset, "JOINT scalar base");
            sample.side_flag =
                read_side_flag(
                    data, offset, "JOINT side flag");
            row.constraints.joints.push_back(sample);
        }

        row.constraints.hinges.reserve(head.hinge_count);
        for (uint32_t index = 0;
             index < head.hinge_count;
             ++index) {
            PreparedHingeSample sample{};
            sample.angular =
                read_vec3(data, offset, "HINGE angular");
            sample.linear =
                read_vec3(data, offset, "HINGE linear");
            sample.position =
                read_vec3(data, offset, "HINGE position");
            sample.frame_offset =
                read_vec3(data, offset, "HINGE frame offset");
            sample.scalar_base =
                read_scalar<uint32_t>(
                    data, offset, "HINGE scalar base");
            sample.side_flag =
                read_side_flag(
                    data, offset, "HINGE side flag");
            row.constraints.hinges.push_back(sample);
        }

        row.constraints.bars.reserve(head.bar_count);
        for (uint32_t index = 0;
             index < head.bar_count;
             ++index) {
            PreparedBarSample sample{};
            sample.point =
                read_vec3(data, offset, "BAR point");
            sample.direction =
                read_vec3(data, offset, "BAR direction");
            sample.side_bias =
                read_finite_double(
                    data, offset, "BAR side bias");
            sample.scalar_base =
                read_scalar<uint32_t>(
                    data, offset, "BAR scalar base");
            sample.side_flag =
                read_side_flag(
                    data, offset, "BAR side flag");
            row.constraints.bars.push_back(sample);
        }

        frame.bodies.push_back(std::move(row));
    }

    if (offset != data.size()) {
        throw std::runtime_error(
            "generated BODY constraint packet has trailing bytes");
    }
    return frame;
}

GeneratedBodyConstraintFrameResult
execute_prepared_generated_body_constraint_frame(
    const PreparedGeneratedBodyConstraintFrame& frame) {

    if (frame.scalar_count == 0 ||
        frame.matrix_double_count !=
            frame.scalar_count * frame.scalar_count ||
        frame.bodies.empty()) {
        throw std::runtime_error(
            "generated BODY constraint frame shape is invalid");
    }

    GeneratedBodyConstraintFrameResult result{};
    result.solver_vector.assign(
        frame.scalar_count,
        0.0);
    result.solver_matrix.assign(
        frame.matrix_double_count,
        0.0);

    for (std::size_t ordinal = 0;
         ordinal < frame.bodies.size();
         ++ordinal) {
        const auto& body = frame.bodies[ordinal];
        if (body.body_index != ordinal) {
            throw std::runtime_error(
                "generated BODY constraint frame order mismatch");
        }
        const auto generated =
            generate_and_export_fun_007bc680_body(body);
        add_body_solver_contributions(
            generated.contribution.solver_vector,
            generated.contribution.solver_matrix,
            result.solver_vector,
            result.solver_matrix);
        result.joint_sample_count +=
            body.constraints.joints.size();
        result.hinge_sample_count +=
            body.constraints.hinges.size();
        result.bar_sample_count +=
            body.constraints.bars.size();
    }
    result.body_count = frame.bodies.size();
    return result;
}

GeneratedBodySolverFrameJoinResult
verify_generated_body_constraint_frame_matches_builtin_solver_frame(
    const PreparedGeneratedBodyConstraintFrame& generated_frame,
    const PreparedBuiltinSolverFrame& solver_frame,
    double tolerance) {

    if (!std::isfinite(tolerance) ||
        tolerance <= 0.0) {
        throw std::invalid_argument(
            "generated BODY/SBFR join tolerance must be finite and positive");
    }

    const auto generated =
        execute_prepared_generated_body_constraint_frame(
            generated_frame);
    const std::size_t n = generated_frame.scalar_count;
    if (n == 0 ||
        solver_frame.rhs.size() != n ||
        solver_frame.matrix.size() != n) {
        throw std::runtime_error(
            "generated BODY/SBFR scalar cardinality mismatch");
    }
    if (generated.solver_vector.size() != n ||
        generated.solver_matrix.size() != n * n) {
        throw std::runtime_error(
            "generated BODY global destination shape mismatch");
    }
    for (const auto& row : solver_frame.matrix) {
        if (row.size() != n) {
            throw std::runtime_error(
                "builtin solver-frame matrix is not square");
        }
    }

    double max_rhs_error = 0.0;
    for (std::size_t index = 0; index < n; ++index) {
        max_rhs_error = std::max(
            max_rhs_error,
            compare_join_value(
                generated.solver_vector[index],
                solver_frame.rhs[index],
                tolerance,
                "generated BODY/RHS"));
    }

    double max_matrix_error = 0.0;
    for (std::size_t row = 0; row < n; ++row) {
        for (std::size_t column = 0;
             column < n;
             ++column) {
            const std::size_t offset =
                row * n + column;
            max_matrix_error = std::max(
                max_matrix_error,
                compare_join_value(
                    generated.solver_matrix[offset],
                    solver_frame.matrix[row][column],
                    tolerance,
                    "generated BODY/matrix"));
        }
    }

    return {
        n,
        n * n,
        generated.body_count,
        generated.joint_sample_count,
        generated.hinge_sample_count,
        generated.bar_sample_count,
        max_rhs_error,
        max_matrix_error,
    };
}

}  // namespace shift::runtime::physics
