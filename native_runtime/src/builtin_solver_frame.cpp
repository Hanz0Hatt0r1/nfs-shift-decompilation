#include "shift_builtin_solver_frame.hpp"

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
constexpr uint32_t kProofProviderAbsent = 1u << 0;
constexpr uint32_t kProofMatrixRhs = 1u << 1;
constexpr uint32_t kProofResetSelection = 1u << 2;
constexpr uint32_t kProofSparseGraph = 1u << 3;
constexpr uint32_t kRequiredProofFlags =
    kProofProviderAbsent |
    kProofMatrixRhs |
    kProofResetSelection |
    kProofSparseGraph;

#pragma pack(push, 1)
struct SolverFrameHeader {
    char magic[4];
    uint32_t version;
    uint32_t scalar_count;
    uint32_t reset_count;
    uint32_t forward_record_count;
    uint32_t reverse_record_count;
    uint32_t proof_flags;
    uint32_t reserved;
};
#pragma pack(pop)

static_assert(sizeof(SolverFrameHeader) == 32);

std::vector<uint8_t> read_file(const std::string& path) {
    std::ifstream stream(path, std::ios::binary | std::ios::ate);
    if (!stream) {
        throw std::runtime_error(
            "cannot open builtin solver-frame packet: " + path);
    }
    const std::streamsize size = stream.tellg();
    if (size <= 0) {
        throw std::runtime_error(
            "builtin solver-frame packet is empty");
    }
    stream.seekg(0);
    std::vector<uint8_t> bytes(static_cast<std::size_t>(size));
    if (!stream.read(
            reinterpret_cast<char*>(bytes.data()),
            size)) {
        throw std::runtime_error(
            "cannot read builtin solver-frame packet");
    }
    return bytes;
}

template <typename T>
T read_scalar(
    const std::vector<uint8_t>& data,
    std::size_t& offset,
    const char* label) {

    if (offset > data.size() ||
        data.size() - offset < sizeof(T)) {
        throw std::runtime_error(
            std::string("builtin solver-frame truncated at ") +
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
            std::string("builtin solver-frame non-finite ") +
            label);
    }
    return value;
}

SparseForwardItem read_forward_item(
    const std::vector<uint8_t>& data,
    std::size_t& offset,
    std::size_t scalar_count) {

    const uint32_t node =
        read_scalar<uint32_t>(data, offset, "forward node");
    const uint32_t dependency_count =
        read_scalar<uint32_t>(
            data, offset, "forward dependency count");
    if (node >= scalar_count ||
        dependency_count > scalar_count) {
        throw std::runtime_error(
            "builtin solver-frame forward item out of range");
    }

    SparseForwardItem item{};
    item.node = node;
    item.dependencies.reserve(dependency_count);
    for (uint32_t i = 0; i < dependency_count; ++i) {
        const uint32_t dependency =
            read_scalar<uint32_t>(
                data, offset, "forward dependency");
        if (dependency >= scalar_count) {
            throw std::runtime_error(
                "builtin solver-frame forward dependency out of range");
        }
        item.dependencies.push_back(dependency);
    }
    return item;
}

SparseReverseRecord read_reverse_record(
    const std::vector<uint8_t>& data,
    std::size_t& offset,
    std::size_t scalar_count) {

    const uint32_t node =
        read_scalar<uint32_t>(data, offset, "reverse node");
    const uint32_t dependency_count =
        read_scalar<uint32_t>(
            data, offset, "reverse dependency count");
    if (node >= scalar_count ||
        dependency_count > scalar_count) {
        throw std::runtime_error(
            "builtin solver-frame reverse record out of range");
    }

    SparseReverseRecord record{};
    record.node = node;
    record.dependencies.reserve(dependency_count);
    for (uint32_t i = 0; i < dependency_count; ++i) {
        const uint32_t dependency =
            read_scalar<uint32_t>(
                data, offset, "reverse dependency");
        if (dependency >= scalar_count) {
            throw std::runtime_error(
                "builtin solver-frame reverse dependency out of range");
        }
        record.dependencies.push_back(dependency);
    }
    return record;
}

}  // namespace

PreparedBuiltinSolverFrame load_prepared_builtin_solver_frame(
    const std::string& path) {

    const std::vector<uint8_t> data = read_file(path);
    if (data.size() < sizeof(SolverFrameHeader)) {
        throw std::runtime_error(
            "builtin solver-frame packet header truncated");
    }

    SolverFrameHeader header{};
    std::memcpy(&header, data.data(), sizeof(header));
    if (std::memcmp(header.magic, "SBFR", 4) != 0 ||
        header.version != kPacketVersion) {
        throw std::runtime_error(
            "unsupported builtin solver-frame packet");
    }
    if (header.scalar_count == 0u ||
        header.scalar_count > 4096u) {
        throw std::runtime_error(
            "builtin solver-frame scalar count out of range");
    }
    if (header.reset_count > header.scalar_count ||
        header.forward_record_count !=
            header.scalar_count + 1u ||
        header.reverse_record_count !=
            header.scalar_count) {
        throw std::runtime_error(
            "builtin solver-frame cardinality mismatch");
    }
    if ((header.proof_flags & kRequiredProofFlags) !=
            kRequiredProofFlags ||
        header.reserved != 0u) {
        throw std::runtime_error(
            "builtin solver-frame runtime proofs are incomplete");
    }

    const std::size_t n = header.scalar_count;
    std::size_t offset = sizeof(SolverFrameHeader);

    PreparedBuiltinSolverFrame frame{};
    frame.matrix.assign(
        n,
        std::vector<double>(n, 0.0));
    for (std::size_t row = 0; row < n; ++row) {
        for (std::size_t column = 0;
             column < n;
             ++column) {
            frame.matrix[row][column] =
                read_finite_double(
                    data, offset, "matrix coefficient");
        }
    }

    frame.rhs.reserve(n);
    for (std::size_t row = 0; row < n; ++row) {
        frame.rhs.push_back(
            read_finite_double(data, offset, "rhs"));
    }

    frame.reset_nodes.reserve(header.reset_count);
    for (uint32_t i = 0; i < header.reset_count; ++i) {
        const uint32_t node =
            read_scalar<uint32_t>(
                data, offset, "reset node");
        if (node >= n) {
            throw std::runtime_error(
                "builtin solver-frame reset node out of range");
        }
        frame.reset_nodes.push_back(node);
    }

    frame.forward_records.reserve(
        header.forward_record_count);
    for (uint32_t record_index = 0;
         record_index < header.forward_record_count;
         ++record_index) {
        const uint32_t item_count =
            read_scalar<uint32_t>(
                data, offset, "forward item count");
        if (item_count > n) {
            throw std::runtime_error(
                "builtin solver-frame forward item count out of range");
        }
        SparseForwardRecord record{};
        record.items.reserve(item_count);
        for (uint32_t item_index = 0;
             item_index < item_count;
             ++item_index) {
            record.items.push_back(
                read_forward_item(data, offset, n));
        }
        frame.forward_records.push_back(std::move(record));
    }

    frame.reverse_records.reserve(
        header.reverse_record_count);
    for (uint32_t record_index = 0;
         record_index < header.reverse_record_count;
         ++record_index) {
        frame.reverse_records.push_back(
            read_reverse_record(data, offset, n));
    }

    frame.expected_solution.reserve(n);
    for (std::size_t row = 0; row < n; ++row) {
        frame.expected_solution.push_back(
            read_finite_double(
                data, offset, "expected solution"));
    }

    if (offset != data.size()) {
        throw std::runtime_error(
            "builtin solver-frame packet has trailing bytes");
    }
    return frame;
}

PreparedBuiltinSolverFrameResult
execute_prepared_builtin_solver_frame_with_reset_nodes(
    const PreparedBuiltinSolverFrame& frame,
    const std::vector<std::size_t>& reset_nodes,
    double tolerance) {

    if (!std::isfinite(tolerance) ||
        tolerance <= 0.0) {
        throw std::invalid_argument(
            "solver-frame tolerance must be finite and positive");
    }

    const auto reset = apply_builtin_diagonal_reset(
        frame.matrix,
        frame.rhs,
        reset_nodes);
    const auto solved = solve_builtin_sparse(
        reset.matrix,
        reset.rhs,
        frame.forward_records,
        frame.reverse_records);

    if (solved.solution.size() !=
        frame.expected_solution.size()) {
        throw std::runtime_error(
            "builtin solver-frame oracle cardinality mismatch");
    }

    double max_error = 0.0;
    for (std::size_t i = 0;
         i < solved.solution.size();
         ++i) {
        const double expected =
            frame.expected_solution[i];
        const double actual =
            solved.solution[i];
        const double error =
            std::abs(actual - expected);
        max_error = std::max(max_error, error);
        const double limit =
            tolerance * std::max(1.0, std::abs(expected));
        if (!std::isfinite(actual) ||
            error > limit) {
            throw std::runtime_error(
                "builtin solver-frame native/Python oracle mismatch");
        }
    }

    return {
        reset.nodes,
        solved.factorized_matrix,
        solved.solution,
        max_error,
    };
}

PreparedBuiltinSolverFrameResult execute_prepared_builtin_solver_frame(
    const PreparedBuiltinSolverFrame& frame,
    double tolerance) {

    return execute_prepared_builtin_solver_frame_with_reset_nodes(
        frame,
        frame.reset_nodes,
        tolerance);
}

}  // namespace shift::runtime::physics
