#include "shift_body_solver_export_frame.hpp"

#include "shift_body_solver_export.hpp"

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
constexpr uint32_t kProofContributions = 1u << 0;
constexpr uint32_t kProofBodyOrder = 1u << 1;
constexpr uint32_t kProofDestinationShape = 1u << 2;
constexpr uint32_t kRequiredProofFlags =
    kProofContributions |
    kProofBodyOrder |
    kProofDestinationShape;

#pragma pack(push, 1)
struct ExportFrameHeader {
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
    uint32_t solver_vector_count;
    uint32_t solver_matrix_count;
};
#pragma pack(pop)

static_assert(sizeof(ExportFrameHeader) == 28);
static_assert(sizeof(BodyHead) == 12);

std::vector<uint8_t> read_file(const std::string& path) {
    std::ifstream stream(path, std::ios::binary | std::ios::ate);
    if (!stream) {
        throw std::runtime_error(
            "cannot open BODY solver export packet: " + path);
    }
    const std::streamsize size = stream.tellg();
    if (size <= 0) {
        throw std::runtime_error(
            "BODY solver export packet is empty");
    }
    stream.seekg(0);
    std::vector<uint8_t> data(static_cast<std::size_t>(size));
    if (!stream.read(
            reinterpret_cast<char*>(data.data()),
            size)) {
        throw std::runtime_error(
            "cannot read BODY solver export packet");
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
            std::string("BODY solver export packet truncated at ") +
            label);
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
            std::string("BODY solver export non-finite ") +
            label);
    }
    return value;
}

double max_vector_error(
    const std::vector<double>& actual,
    const std::vector<double>& expected,
    double tolerance,
    const char* label) {

    if (actual.size() != expected.size()) {
        throw std::runtime_error(
            std::string(label) + " oracle cardinality mismatch");
    }
    double max_error = 0.0;
    for (std::size_t index = 0;
         index < actual.size();
         ++index) {
        const double error =
            std::abs(actual[index] - expected[index]);
        max_error = std::max(max_error, error);
        const double limit =
            tolerance *
            std::max(1.0, std::abs(expected[index]));
        if (!std::isfinite(actual[index]) ||
            error > limit) {
            throw std::runtime_error(
                std::string(label) +
                " native/Python oracle mismatch");
        }
    }
    return max_error;
}

}  // namespace

PreparedBodySolverExportFrame load_prepared_body_solver_export_frame(
    const std::string& path) {

    const auto data = read_file(path);
    if (data.size() < sizeof(ExportFrameHeader)) {
        throw std::runtime_error(
            "BODY solver export packet header truncated");
    }

    ExportFrameHeader header{};
    std::memcpy(&header, data.data(), sizeof(header));
    if (std::memcmp(header.magic, "SBEX", 4) != 0 ||
        header.version != kPacketVersion) {
        throw std::runtime_error(
            "unsupported BODY solver export packet");
    }
    if (header.body_count == 0u ||
        header.body_count > 4096u ||
        header.scalar_count == 0u ||
        header.scalar_count > 4096u) {
        throw std::runtime_error(
            "BODY solver export cardinality out of range");
    }
    const uint64_t expected_matrix_count =
        static_cast<uint64_t>(header.scalar_count) *
        static_cast<uint64_t>(header.scalar_count);
    if (expected_matrix_count !=
        header.matrix_double_count) {
        throw std::runtime_error(
            "BODY solver export destination shape mismatch");
    }
    if ((header.proof_flags & kRequiredProofFlags) !=
            kRequiredProofFlags ||
        header.reserved != 0u) {
        throw std::runtime_error(
            "BODY solver export runtime proofs are incomplete");
    }

    PreparedBodySolverExportFrame frame{};
    frame.scalar_count = header.scalar_count;
    frame.matrix_double_count =
        header.matrix_double_count;

    std::size_t offset = sizeof(ExportFrameHeader);
    frame.bodies.reserve(header.body_count);
    for (uint32_t ordinal = 0;
         ordinal < header.body_count;
         ++ordinal) {
        const BodyHead body =
            read_scalar<BodyHead>(
                data, offset, "BODY header");
        if (body.body_index != ordinal) {
            throw std::runtime_error(
                "BODY solver export order mismatch");
        }
        if (body.solver_vector_count >
                header.scalar_count ||
            body.solver_matrix_count >
                header.matrix_double_count) {
            throw std::runtime_error(
                "BODY solver export contribution count out of range");
        }

        PreparedBodySolverContribution row{};
        row.body_index = body.body_index;
        row.solver_vector.reserve(
            body.solver_vector_count);
        row.solver_matrix.reserve(
            body.solver_matrix_count);
        for (uint32_t index = 0;
             index < body.solver_vector_count;
             ++index) {
            row.solver_vector.push_back(
                read_finite_double(
                    data,
                    offset,
                    "BODY solver vector contribution"));
        }
        for (uint32_t index = 0;
             index < body.solver_matrix_count;
             ++index) {
            row.solver_matrix.push_back(
                read_finite_double(
                    data,
                    offset,
                    "BODY solver matrix contribution"));
        }
        frame.bodies.push_back(std::move(row));
    }

    frame.expected_solver_vector.reserve(
        header.scalar_count);
    for (uint32_t index = 0;
         index < header.scalar_count;
         ++index) {
        frame.expected_solver_vector.push_back(
            read_finite_double(
                data,
                offset,
                "expected global solver vector"));
    }

    frame.expected_solver_matrix.reserve(
        header.matrix_double_count);
    for (uint32_t index = 0;
         index < header.matrix_double_count;
         ++index) {
        frame.expected_solver_matrix.push_back(
            read_finite_double(
                data,
                offset,
                "expected global solver matrix"));
    }

    if (offset != data.size()) {
        throw std::runtime_error(
            "BODY solver export packet has trailing bytes");
    }
    return frame;
}

PreparedBodySolverExportFrameResult execute_prepared_body_solver_export_frame(
    const PreparedBodySolverExportFrame& frame,
    double tolerance) {

    if (!std::isfinite(tolerance) ||
        tolerance <= 0.0) {
        throw std::invalid_argument(
            "BODY solver export tolerance must be finite and positive");
    }
    if (frame.scalar_count == 0 ||
        frame.matrix_double_count !=
            frame.scalar_count * frame.scalar_count ||
        frame.expected_solver_vector.size() !=
            frame.scalar_count ||
        frame.expected_solver_matrix.size() !=
            frame.matrix_double_count) {
        throw std::runtime_error(
            "BODY solver export prepared destination shape invalid");
    }

    std::vector<double> solver_vector(
        frame.scalar_count, 0.0);
    std::vector<double> solver_matrix(
        frame.matrix_double_count, 0.0);

    for (std::size_t ordinal = 0;
         ordinal < frame.bodies.size();
         ++ordinal) {
        const auto& body = frame.bodies[ordinal];
        if (body.body_index != ordinal) {
            throw std::runtime_error(
                "BODY solver export prepared order mismatch");
        }
        add_body_solver_contributions(
            body.solver_vector,
            body.solver_matrix,
            solver_vector,
            solver_matrix);
    }

    double max_error = 0.0;
    max_error = std::max(
        max_error,
        max_vector_error(
            solver_vector,
            frame.expected_solver_vector,
            tolerance,
            "BODY solver vector"));
    max_error = std::max(
        max_error,
        max_vector_error(
            solver_matrix,
            frame.expected_solver_matrix,
            tolerance,
            "BODY solver matrix"));

    return {
        std::move(solver_vector),
        std::move(solver_matrix),
        frame.bodies.size(),
        max_error,
    };
}

}  // namespace shift::runtime::physics
