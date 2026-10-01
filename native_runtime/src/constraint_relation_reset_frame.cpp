#include "shift_constraint_relation_reset_frame.hpp"

#include <cstdint>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace shift::runtime::physics {
namespace {

constexpr std::uint32_t kPacketVersion = 1u;
constexpr std::uint32_t kProofRelationStateBit0 = 1u << 0;
constexpr std::uint32_t kProofSourceOrder = 1u << 1;
constexpr std::uint32_t kProofProviderAbsent = 1u << 2;
constexpr std::uint32_t kRequiredProofFlags =
    kProofRelationStateBit0 |
    kProofSourceOrder |
    kProofProviderAbsent;

#pragma pack(push, 1)
struct FrameHeader {
    char magic[4];
    std::uint32_t version;
    std::uint32_t joint_relation_count;
    std::uint32_t hinge_relation_count;
    std::uint32_t bar_relation_count;
    std::uint32_t proof_flags;
    std::uint32_t reserved;
};
#pragma pack(pop)

static_assert(sizeof(FrameHeader) == 28);

std::vector<std::uint8_t> read_file(const std::string& path) {
    std::ifstream stream(path, std::ios::binary | std::ios::ate);
    if (!stream) {
        throw std::runtime_error(
            "cannot open constraint relation reset packet: " + path);
    }
    const std::streamsize size = stream.tellg();
    if (size <= 0) {
        throw std::runtime_error(
            "constraint relation reset packet is empty");
    }
    stream.seekg(0);
    std::vector<std::uint8_t> data(
        static_cast<std::size_t>(size));
    if (!stream.read(
            reinterpret_cast<char*>(data.data()),
            size)) {
        throw std::runtime_error(
            "cannot read constraint relation reset packet");
    }
    return data;
}

std::uint8_t read_state_bit(
    const std::vector<std::uint8_t>& data,
    std::size_t& offset,
    const char* label) {

    if (offset >= data.size()) {
        throw std::runtime_error(
            std::string(
                "constraint relation reset packet truncated at ") +
            label);
    }
    const std::uint8_t value = data[offset++];
    if (value > 1u) {
        throw std::runtime_error(
            std::string(label) + " must be 0 or 1");
    }
    return value;
}

template <typename Range>
void read_state_range(
    const std::vector<std::uint8_t>& data,
    std::size_t& offset,
    std::size_t count,
    const char* label,
    Range& output) {

    output.reserve(count);
    for (std::size_t index = 0; index < count; ++index) {
        output.push_back(
            read_state_bit(data, offset, label));
    }
}

template <typename Relation, typename SampleGetter>
std::size_t validate_relation_scalar_span(
    const PreparedGeneratedBodyConstraintFrame& frame,
    const Relation& relation,
    std::size_t width,
    std::vector<std::uint8_t>& scalar_coverage,
    const char* label,
    SampleGetter get_samples) {

    if (relation.positive.body_index >= frame.bodies.size() ||
        relation.negative.body_index >= frame.bodies.size()) {
        throw std::runtime_error(
            std::string(label) +
            " reset endpoint BODY index out of range");
    }

    const auto& positive_samples =
        get_samples(
            frame.bodies[relation.positive.body_index]
                .constraints);
    const auto& negative_samples =
        get_samples(
            frame.bodies[relation.negative.body_index]
                .constraints);
    if (relation.positive.sample_index >= positive_samples.size() ||
        relation.negative.sample_index >= negative_samples.size()) {
        throw std::runtime_error(
            std::string(label) +
            " reset endpoint sample index out of range");
    }

    const auto& positive =
        positive_samples[relation.positive.sample_index];
    const auto& negative =
        negative_samples[relation.negative.sample_index];
    if (positive.side_flag != 1u ||
        negative.side_flag != 0u) {
        throw std::runtime_error(
            std::string(label) +
            " reset endpoint side identity mismatch");
    }
    if (positive.scalar_base != negative.scalar_base) {
        throw std::runtime_error(
            std::string(label) +
            " reset endpoint scalar bases do not match");
    }

    const std::size_t base = positive.scalar_base;
    if (base > frame.scalar_count ||
        width > frame.scalar_count - base) {
        throw std::runtime_error(
            std::string(label) +
            " reset scalar span is outside solver domain");
    }

    for (std::size_t lane = 0; lane < width; ++lane) {
        const std::size_t node = base + lane;
        if (scalar_coverage[node] != 0u) {
            throw std::runtime_error(
                std::string(label) +
                " reset scalar layout overlaps another relation");
        }
        scalar_coverage[node] = 1u;
    }
    return base;
}

void require_complete_scalar_coverage(
    const std::vector<std::uint8_t>& coverage) {

    for (const std::uint8_t covered : coverage) {
        if (covered == 0u) {
            throw std::runtime_error(
                "constraint relation reset scalar layout is incomplete");
        }
    }
}

void append_selected_span(
    std::vector<std::size_t>& reset_nodes,
    std::size_t base,
    std::size_t width,
    std::uint8_t state_bit0,
    std::size_t& selected_relation_count,
    const char* label) {

    if (state_bit0 > 1u) {
        throw std::runtime_error(
            std::string(label) +
            " relation state bit0 must be 0 or 1");
    }
    if (state_bit0 == 0u) {
        return;
    }

    ++selected_relation_count;
    for (std::size_t lane = 0; lane < width; ++lane) {
        reset_nodes.push_back(base + lane);
    }
}

}  // namespace

PreparedConstraintRelationResetFrame
load_prepared_constraint_relation_reset_frame(
    const std::string& path) {

    const auto data = read_file(path);
    if (data.size() < sizeof(FrameHeader)) {
        throw std::runtime_error(
            "constraint relation reset header truncated");
    }

    FrameHeader header{};
    std::memcpy(
        &header,
        data.data(),
        sizeof(header));

    if (std::memcmp(header.magic, "CRRF", 4) != 0 ||
        header.version != kPacketVersion) {
        throw std::runtime_error(
            "unsupported constraint relation reset packet");
    }
    if (header.joint_relation_count > 4096u ||
        header.hinge_relation_count > 4096u ||
        header.bar_relation_count > 4096u) {
        throw std::runtime_error(
            "constraint relation reset cardinality out of range");
    }
    if (header.joint_relation_count == 0u &&
        header.hinge_relation_count == 0u &&
        header.bar_relation_count == 0u) {
        throw std::runtime_error(
            "constraint relation reset packet has no relations");
    }
    if ((header.proof_flags & kRequiredProofFlags) !=
            kRequiredProofFlags ||
        header.reserved != 0u) {
        throw std::runtime_error(
            "constraint relation reset runtime proofs are incomplete");
    }

    PreparedConstraintRelationResetFrame frame{};
    std::size_t offset = sizeof(FrameHeader);
    read_state_range(
        data,
        offset,
        header.joint_relation_count,
        "JOINT relation state bit0",
        frame.joint_state_bit0);
    read_state_range(
        data,
        offset,
        header.hinge_relation_count,
        "HINGE relation state bit0",
        frame.hinge_state_bit0);
    read_state_range(
        data,
        offset,
        header.bar_relation_count,
        "BAR relation state bit0",
        frame.bar_state_bit0);

    if (offset != data.size()) {
        throw std::runtime_error(
            "constraint relation reset packet has trailing bytes");
    }
    return frame;
}

ConstraintRelationResetSelectionResult
select_fun_007b3f40_reset_nodes(
    const PreparedGeneratedBodyConstraintFrame& frame,
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& reset_state) {

    if (frame.scalar_count == 0u ||
        frame.bodies.empty()) {
        throw std::runtime_error(
            "constraint relation reset requires a non-empty GBCF");
    }
    if (relations.body_count != frame.bodies.size()) {
        throw std::runtime_error(
            "constraint relation reset BODY count mismatch");
    }
    if (reset_state.joint_state_bit0.size() !=
            relations.joints.size() ||
        reset_state.hinge_state_bit0.size() !=
            relations.hinges.size() ||
        reset_state.bar_state_bit0.size() !=
            relations.bars.size()) {
        throw std::runtime_error(
            "constraint relation reset state cardinality mismatch");
    }

    ConstraintRelationResetSelectionResult result{};
    result.scalar_count = frame.scalar_count;
    result.joint_relation_count = relations.joints.size();
    result.hinge_relation_count = relations.hinges.size();
    result.bar_relation_count = relations.bars.size();

    std::vector<std::uint8_t> scalar_coverage(
        frame.scalar_count,
        0u);

    for (std::size_t index = 0;
         index < relations.joints.size();
         ++index) {
        const std::size_t base =
            validate_relation_scalar_span(
                frame,
                relations.joints[index],
                3u,
                scalar_coverage,
                "JOINT",
                [](const auto& constraints)
                    -> decltype(auto) {
                    return (constraints.joints);
                });
        append_selected_span(
            result.reset_nodes,
            base,
            3u,
            reset_state.joint_state_bit0[index],
            result.selected_joint_relation_count,
            "JOINT");
    }

    for (std::size_t index = 0;
         index < relations.hinges.size();
         ++index) {
        const std::size_t base =
            validate_relation_scalar_span(
                frame,
                relations.hinges[index],
                2u,
                scalar_coverage,
                "HINGE",
                [](const auto& constraints)
                    -> decltype(auto) {
                    return (constraints.hinges);
                });
        append_selected_span(
            result.reset_nodes,
            base,
            2u,
            reset_state.hinge_state_bit0[index],
            result.selected_hinge_relation_count,
            "HINGE");
    }

    for (std::size_t index = 0;
         index < relations.bars.size();
         ++index) {
        const std::size_t base =
            validate_relation_scalar_span(
                frame,
                relations.bars[index],
                1u,
                scalar_coverage,
                "BAR",
                [](const auto& constraints)
                    -> decltype(auto) {
                    return (constraints.bars);
                });
        append_selected_span(
            result.reset_nodes,
            base,
            1u,
            reset_state.bar_state_bit0[index],
            result.selected_bar_relation_count,
            "BAR");
    }

    require_complete_scalar_coverage(
        scalar_coverage);
    return result;
}

}  // namespace shift::runtime::physics
