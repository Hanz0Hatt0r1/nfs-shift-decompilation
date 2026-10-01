#include "shift_constraint_reset_state_frame.hpp"

#include <algorithm>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace shift::runtime::physics {
namespace {

constexpr uint32_t kPacketVersion = 1u;
constexpr uint32_t kProofRuntimeFlags = 1u << 0;
constexpr uint32_t kProofSourceOrder = 1u << 1;
constexpr uint32_t kProofProviderAbsent = 1u << 2;
constexpr uint32_t kRequiredProofFlags =
    kProofRuntimeFlags |
    kProofSourceOrder |
    kProofProviderAbsent;

#pragma pack(push, 1)
struct FrameHeader {
    char magic[4];
    uint32_t version;
    uint32_t body_count;
    uint32_t joint_relation_count;
    uint32_t hinge_relation_count;
    uint32_t bar_relation_count;
    uint32_t proof_flags;
    uint32_t reserved;
};
#pragma pack(pop)

static_assert(sizeof(FrameHeader) == 32);

std::vector<uint8_t> read_file(const std::string& path) {
    std::ifstream stream(path, std::ios::binary | std::ios::ate);
    if (!stream) {
        throw std::runtime_error(
            "cannot open constraint reset-state packet: " + path);
    }
    const std::streamsize size = stream.tellg();
    if (size <= 0) {
        throw std::runtime_error(
            "constraint reset-state packet is empty");
    }
    stream.seekg(0);
    std::vector<uint8_t> data(static_cast<std::size_t>(size));
    if (!stream.read(
            reinterpret_cast<char*>(data.data()),
            size)) {
        throw std::runtime_error(
            "cannot read constraint reset-state packet");
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
                "constraint reset-state packet truncated at ") +
            label);
    }
    T value{};
    std::memcpy(&value, data.data() + offset, sizeof(T));
    offset += sizeof(T);
    return value;
}

template <typename SampleGetter>
std::size_t validate_endpoint_pair(
    const PreparedGeneratedBodyConstraintFrame& frame,
    const ConstraintSampleEndpointRef& positive,
    const ConstraintSampleEndpointRef& negative,
    const char* label,
    SampleGetter get_samples) {

    if (positive.body_index >= frame.bodies.size() ||
        negative.body_index >= frame.bodies.size()) {
        throw std::runtime_error(
            std::string(label) +
            " reset endpoint BODY index out of range");
    }

    const auto& positive_samples =
        get_samples(
            frame.bodies[positive.body_index].constraints);
    const auto& negative_samples =
        get_samples(
            frame.bodies[negative.body_index].constraints);
    if (positive.sample_index >= positive_samples.size() ||
        negative.sample_index >= negative_samples.size()) {
        throw std::runtime_error(
            std::string(label) +
            " reset endpoint sample index out of range");
    }

    const auto& positive_sample =
        positive_samples[positive.sample_index];
    const auto& negative_sample =
        negative_samples[negative.sample_index];
    if (positive_sample.side_flag != 1u ||
        negative_sample.side_flag != 0u) {
        throw std::runtime_error(
            std::string(label) +
            " reset endpoint side identity mismatch");
    }
    if (positive_sample.scalar_base !=
        negative_sample.scalar_base) {
        throw std::runtime_error(
            std::string(label) +
            " reset endpoint scalar bases do not match");
    }
    return positive_sample.scalar_base;
}

void append_reset_block(
    ConstraintResetSelectionResult& result,
    std::vector<bool>& used,
    std::size_t base,
    std::size_t width,
    std::size_t scalar_count,
    const char* label) {

    if (base > scalar_count ||
        width > scalar_count - base) {
        throw std::runtime_error(
            std::string(label) +
            " reset scalar block is outside solver domain");
    }
    for (std::size_t lane = 0; lane < width; ++lane) {
        const std::size_t node = base + lane;
        if (used[node]) {
            throw std::runtime_error(
                "constraint reset scalar blocks overlap");
        }
        used[node] = true;
        result.ordered_reset_nodes.push_back(node);
    }
}

}  // namespace

PreparedConstraintResetStateFrame
load_prepared_constraint_reset_state_frame(
    const std::string& path) {

    const auto data = read_file(path);
    if (data.size() < sizeof(FrameHeader)) {
        throw std::runtime_error(
            "constraint reset-state header truncated");
    }

    FrameHeader header{};
    std::memcpy(&header, data.data(), sizeof(header));
    if (std::memcmp(header.magic, "CRST", 4) != 0 ||
        header.version != kPacketVersion) {
        throw std::runtime_error(
            "unsupported constraint reset-state packet");
    }
    if (header.body_count == 0u ||
        header.body_count > 4096u ||
        header.joint_relation_count > 4096u ||
        header.hinge_relation_count > 4096u ||
        header.bar_relation_count > 4096u) {
        throw std::runtime_error(
            "constraint reset-state cardinality out of range");
    }
    if (header.joint_relation_count == 0u &&
        header.hinge_relation_count == 0u &&
        header.bar_relation_count == 0u) {
        throw std::runtime_error(
            "constraint reset-state packet has no relations");
    }
    if ((header.proof_flags & kRequiredProofFlags) !=
            kRequiredProofFlags ||
        header.reserved != 0u) {
        throw std::runtime_error(
            "constraint reset-state runtime proofs are incomplete");
    }

    PreparedConstraintResetStateFrame frame{};
    frame.body_count = header.body_count;
    frame.joint_runtime_flags.reserve(
        header.joint_relation_count);
    frame.hinge_runtime_flags.reserve(
        header.hinge_relation_count);
    frame.bar_runtime_flags.reserve(
        header.bar_relation_count);

    std::size_t offset = sizeof(FrameHeader);
    for (uint32_t index = 0;
         index < header.joint_relation_count;
         ++index) {
        frame.joint_runtime_flags.push_back(
            read_scalar<uint32_t>(
                data,
                offset,
                "JOINT runtime flag"));
    }
    for (uint32_t index = 0;
         index < header.hinge_relation_count;
         ++index) {
        frame.hinge_runtime_flags.push_back(
            read_scalar<uint32_t>(
                data,
                offset,
                "HINGE runtime flag"));
    }
    for (uint32_t index = 0;
         index < header.bar_relation_count;
         ++index) {
        frame.bar_runtime_flags.push_back(
            read_scalar<uint32_t>(
                data,
                offset,
                "BAR runtime flag"));
    }

    if (offset != data.size()) {
        throw std::runtime_error(
            "constraint reset-state packet has trailing bytes");
    }
    return frame;
}

ConstraintResetSelectionResult
derive_fun_007b2210_reset_nodes(
    const PreparedGeneratedBodyConstraintFrame& frame,
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintResetStateFrame& reset_state) {

    if (frame.scalar_count == 0u ||
        frame.bodies.empty()) {
        throw std::runtime_error(
            "constraint reset selection requires a non-empty GBCF");
    }
    if (relations.body_count != frame.bodies.size() ||
        reset_state.body_count != frame.bodies.size()) {
        throw std::runtime_error(
            "constraint reset BODY count does not match GBCF");
    }
    if (reset_state.joint_runtime_flags.size() !=
            relations.joints.size() ||
        reset_state.hinge_runtime_flags.size() !=
            relations.hinges.size() ||
        reset_state.bar_runtime_flags.size() !=
            relations.bars.size()) {
        throw std::runtime_error(
            "constraint reset relation counts do not match CSRF");
    }

    ConstraintResetSelectionResult result{};
    result.joint_relation_count = relations.joints.size();
    result.hinge_relation_count = relations.hinges.size();
    result.bar_relation_count = relations.bars.size();
    std::vector<bool> used(frame.scalar_count, false);

    for (std::size_t index = 0;
         index < relations.joints.size();
         ++index) {
        const auto& relation = relations.joints[index];
        const std::size_t base =
            validate_endpoint_pair(
                frame,
                relation.positive,
                relation.negative,
                "JOINT",
                [](const BodyConstraintAssemblyInput& body)
                    -> const std::vector<PreparedJointSample>& {
                    return body.joints;
                });
        if ((reset_state.joint_runtime_flags[index] & 1u) != 0u) {
            append_reset_block(
                result,
                used,
                base,
                3u,
                frame.scalar_count,
                "JOINT");
            ++result.selected_joint_relation_count;
        }
    }

    for (std::size_t index = 0;
         index < relations.hinges.size();
         ++index) {
        const auto& relation = relations.hinges[index];
        const std::size_t base =
            validate_endpoint_pair(
                frame,
                relation.positive,
                relation.negative,
                "HINGE",
                [](const BodyConstraintAssemblyInput& body)
                    -> const std::vector<PreparedHingeSample>& {
                    return body.hinges;
                });
        if ((reset_state.hinge_runtime_flags[index] & 1u) != 0u) {
            append_reset_block(
                result,
                used,
                base,
                2u,
                frame.scalar_count,
                "HINGE");
            ++result.selected_hinge_relation_count;
        }
    }

    for (std::size_t index = 0;
         index < relations.bars.size();
         ++index) {
        const auto& relation = relations.bars[index];
        const std::size_t base =
            validate_endpoint_pair(
                frame,
                relation.positive,
                relation.negative,
                "BAR",
                [](const BodyConstraintAssemblyInput& body)
                    -> const std::vector<PreparedBarSample>& {
                    return body.bars;
                });
        if ((reset_state.bar_runtime_flags[index] & 1u) != 0u) {
            append_reset_block(
                result,
                used,
                base,
                1u,
                frame.scalar_count,
                "BAR");
            ++result.selected_bar_relation_count;
        }
    }

    result.reset_nodes = result.ordered_reset_nodes;
    std::sort(
        result.reset_nodes.begin(),
        result.reset_nodes.end());
    return result;
}

}  // namespace shift::runtime::physics
