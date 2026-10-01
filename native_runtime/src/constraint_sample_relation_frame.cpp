#include "shift_constraint_sample_relation_frame.hpp"

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
constexpr uint32_t kProofRawSampleValues = 1u << 0;
constexpr uint32_t kProofOwnership = 1u << 1;
constexpr uint32_t kProofSourceOrder = 1u << 2;
constexpr uint32_t kProofProviderAbsent = 1u << 3;
constexpr uint32_t kRequiredProofFlags =
    kProofRawSampleValues |
    kProofOwnership |
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

struct RelationHead {
    uint32_t positive_body_index;
    uint32_t positive_sample_index;
    uint32_t negative_body_index;
    uint32_t negative_sample_index;
};
#pragma pack(pop)

static_assert(sizeof(FrameHeader) == 32);
static_assert(sizeof(RelationHead) == 16);

std::vector<uint8_t> read_file(const std::string& path) {
    std::ifstream stream(path, std::ios::binary | std::ios::ate);
    if (!stream) {
        throw std::runtime_error(
            "cannot open constraint sample relation packet: " + path);
    }
    const std::streamsize size = stream.tellg();
    if (size <= 0) {
        throw std::runtime_error(
            "constraint sample relation packet is empty");
    }
    stream.seekg(0);
    std::vector<uint8_t> data(static_cast<std::size_t>(size));
    if (!stream.read(
            reinterpret_cast<char*>(data.data()),
            size)) {
        throw std::runtime_error(
            "cannot read constraint sample relation packet");
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
                "constraint sample relation packet truncated at ") +
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
            std::string(
                "constraint sample relation non-finite ") +
            label);
    }
    return value;
}

ConstraintRefreshVector3d read_vec3(
    const std::vector<uint8_t>& data,
    std::size_t& offset,
    const char* label) {

    return {
        read_finite_double(data, offset, label),
        read_finite_double(data, offset, label),
        read_finite_double(data, offset, label),
    };
}

ConstraintSampleEndpointRef endpoint_from_head(
    const RelationHead& head,
    bool positive) {

    return positive
        ? ConstraintSampleEndpointRef{
              head.positive_body_index,
              head.positive_sample_index}
        : ConstraintSampleEndpointRef{
              head.negative_body_index,
              head.negative_sample_index};
}

template <typename SampleGetter>
void validate_endpoint(
    const PreparedGeneratedBodyConstraintFrame& frame,
    const ConstraintSampleEndpointRef& ref,
    std::vector<std::vector<bool>>& coverage,
    std::uint8_t expected_side,
    const char* label,
    SampleGetter get_samples) {

    if (ref.body_index >= frame.bodies.size()) {
        throw std::runtime_error(
            std::string(label) + " BODY index out of range");
    }
    const auto& samples =
        get_samples(frame.bodies[ref.body_index].constraints);
    if (ref.sample_index >= samples.size()) {
        throw std::runtime_error(
            std::string(label) + " sample index out of range");
    }
    if (coverage[ref.body_index][ref.sample_index]) {
        throw std::runtime_error(
            std::string(label) + " sample ownership is duplicated");
    }
    if (samples[ref.sample_index].side_flag != expected_side) {
        throw std::runtime_error(
            std::string(label) + " side flag does not match retail endpoint");
    }
    coverage[ref.body_index][ref.sample_index] = true;
}

void require_complete_coverage(
    const std::vector<std::vector<bool>>& coverage,
    const char* label) {

    for (std::size_t body = 0; body < coverage.size(); ++body) {
        for (std::size_t sample = 0;
             sample < coverage[body].size();
             ++sample) {
            if (!coverage[body][sample]) {
                throw std::runtime_error(
                    std::string(label) +
                    " sample ownership is incomplete");
            }
        }
    }
}

template <typename SampleGetter>
std::vector<std::vector<bool>> make_coverage(
    const PreparedGeneratedBodyConstraintFrame& frame,
    SampleGetter get_samples) {

    std::vector<std::vector<bool>> result;
    result.reserve(frame.bodies.size());
    for (const auto& body : frame.bodies) {
        result.emplace_back(
            get_samples(body.constraints).size(),
            false);
    }
    return result;
}

}  // namespace

PreparedConstraintSampleRelationFrame
load_prepared_constraint_sample_relation_frame(
    const std::string& path) {

    const auto data = read_file(path);
    if (data.size() < sizeof(FrameHeader)) {
        throw std::runtime_error(
            "constraint sample relation header truncated");
    }

    FrameHeader header{};
    std::memcpy(&header, data.data(), sizeof(header));
    if (std::memcmp(header.magic, "CSRF", 4) != 0 ||
        header.version != kPacketVersion) {
        throw std::runtime_error(
            "unsupported constraint sample relation packet");
    }
    if (header.body_count == 0u ||
        header.body_count > 4096u ||
        header.joint_relation_count > 4096u ||
        header.hinge_relation_count > 4096u ||
        header.bar_relation_count > 4096u) {
        throw std::runtime_error(
            "constraint sample relation cardinality out of range");
    }
    if (header.joint_relation_count == 0u &&
        header.hinge_relation_count == 0u &&
        header.bar_relation_count == 0u) {
        throw std::runtime_error(
            "constraint sample relation packet has no relations");
    }
    if ((header.proof_flags & kRequiredProofFlags) !=
            kRequiredProofFlags ||
        header.reserved != 0u) {
        throw std::runtime_error(
            "constraint sample relation runtime proofs are incomplete");
    }

    PreparedConstraintSampleRelationFrame frame{};
    frame.body_count = header.body_count;
    frame.joints.reserve(header.joint_relation_count);
    frame.hinges.reserve(header.hinge_relation_count);
    frame.bars.reserve(header.bar_relation_count);

    std::size_t offset = sizeof(FrameHeader);
    for (uint32_t index = 0;
         index < header.joint_relation_count;
         ++index) {
        const auto head =
            read_scalar<RelationHead>(
                data, offset, "JOINT relation header");
        PreparedJointConstraintRelation row{};
        row.positive = endpoint_from_head(head, true);
        row.negative = endpoint_from_head(head, false);
        row.positive_local_position =
            read_vec3(data, offset, "JOINT positive local");
        row.negative_local_position =
            read_vec3(data, offset, "JOINT negative local");
        frame.joints.push_back(row);
    }

    for (uint32_t index = 0;
         index < header.hinge_relation_count;
         ++index) {
        const auto head =
            read_scalar<RelationHead>(
                data, offset, "HINGE relation header");
        PreparedHingeConstraintRelation row{};
        row.positive = endpoint_from_head(head, true);
        row.negative = endpoint_from_head(head, false);
        row.positive_angular_local =
            read_vec3(data, offset, "HINGE positive angular local");
        row.positive_linear_local =
            read_vec3(data, offset, "HINGE positive linear local");
        frame.hinges.push_back(row);
    }

    for (uint32_t index = 0;
         index < header.bar_relation_count;
         ++index) {
        const auto head =
            read_scalar<RelationHead>(
                data, offset, "BAR relation header");
        PreparedBarConstraintRelation row{};
        row.positive = endpoint_from_head(head, true);
        row.negative = endpoint_from_head(head, false);
        row.positive_local_point =
            read_vec3(data, offset, "BAR positive local");
        row.negative_local_point =
            read_vec3(data, offset, "BAR negative local");
        frame.bars.push_back(row);
    }

    if (offset != data.size()) {
        throw std::runtime_error(
            "constraint sample relation packet has trailing bytes");
    }
    return frame;
}

RefreshedGeneratedBodyConstraintFrame
refresh_generated_body_constraint_frame(
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations) {

    if (source.bodies.empty() ||
        source.bodies.size() != relations.body_count) {
        throw std::runtime_error(
            "constraint relation BODY count does not match GBCF");
    }

    RefreshedGeneratedBodyConstraintFrame result{};
    result.frame = source;
    result.joint_relation_count = relations.joints.size();
    result.hinge_relation_count = relations.hinges.size();
    result.bar_relation_count = relations.bars.size();

    auto joint_coverage = make_coverage(
        source,
        [](const BodyConstraintAssemblyInput& body)
            -> const std::vector<PreparedJointSample>& {
            return body.joints;
        });
    auto hinge_coverage = make_coverage(
        source,
        [](const BodyConstraintAssemblyInput& body)
            -> const std::vector<PreparedHingeSample>& {
            return body.hinges;
        });
    auto bar_coverage = make_coverage(
        source,
        [](const BodyConstraintAssemblyInput& body)
            -> const std::vector<PreparedBarSample>& {
            return body.bars;
        });

    for (const auto& relation : relations.joints) {
        validate_endpoint(
            source,
            relation.positive,
            joint_coverage,
            1u,
            "JOINT positive",
            [](const BodyConstraintAssemblyInput& body)
                -> const std::vector<PreparedJointSample>& {
                return body.joints;
            });
        validate_endpoint(
            source,
            relation.negative,
            joint_coverage,
            0u,
            "JOINT negative",
            [](const BodyConstraintAssemblyInput& body)
                -> const std::vector<PreparedJointSample>& {
                return body.joints;
            });

        const auto& positive_body =
            source.bodies[relation.positive.body_index].constraints;
        const auto& negative_body =
            source.bodies[relation.negative.body_index].constraints;
        const auto& positive_sample =
            positive_body.joints[relation.positive.sample_index];
        const auto& negative_sample =
            negative_body.joints[relation.negative.sample_index];
        if (positive_sample.scalar_base !=
            negative_sample.scalar_base) {
            throw std::runtime_error(
                "JOINT endpoint scalar bases do not match");
        }

        JointConstraintRefreshInput input{};
        input.positive_body_frame =
            positive_body.preprojection.body_frame;
        input.negative_body_frame =
            negative_body.preprojection.body_frame;
        input.positive_local_position =
            relation.positive_local_position;
        input.negative_local_position =
            relation.negative_local_position;
        const auto refreshed =
            refresh_fun_007b2da0_joint(input);

        result.frame
            .bodies[relation.positive.body_index]
            .constraints.joints[relation.positive.sample_index]
            .position = refreshed.positive_position;
        result.frame
            .bodies[relation.negative.body_index]
            .constraints.joints[relation.negative.sample_index]
            .position = refreshed.negative_position;
        result.refreshed_joint_sample_count += 2u;
    }

    for (const auto& relation : relations.hinges) {
        validate_endpoint(
            source,
            relation.positive,
            hinge_coverage,
            1u,
            "HINGE positive",
            [](const BodyConstraintAssemblyInput& body)
                -> const std::vector<PreparedHingeSample>& {
                return body.hinges;
            });
        validate_endpoint(
            source,
            relation.negative,
            hinge_coverage,
            0u,
            "HINGE negative",
            [](const BodyConstraintAssemblyInput& body)
                -> const std::vector<PreparedHingeSample>& {
                return body.hinges;
            });

        const auto& positive_body =
            source.bodies[relation.positive.body_index].constraints;
        const auto& negative_body =
            source.bodies[relation.negative.body_index].constraints;
        const auto& positive_sample =
            positive_body.hinges[relation.positive.sample_index];
        const auto& negative_sample =
            negative_body.hinges[relation.negative.sample_index];
        if (positive_sample.scalar_base !=
            negative_sample.scalar_base) {
            throw std::runtime_error(
                "HINGE endpoint scalar bases do not match");
        }

        HingeConstraintRefreshInput input{};
        input.positive_body_frame =
            positive_body.preprojection.body_frame;
        input.negative_body_frame =
            negative_body.preprojection.body_frame;
        input.positive_angular_local =
            relation.positive_angular_local;
        input.positive_linear_local =
            relation.positive_linear_local;
        input.negative_primary_local =
            negative_sample.position;
        const auto refreshed =
            refresh_fun_007b2de0_hinge(input);

        auto& positive_output =
            result.frame
                .bodies[relation.positive.body_index]
                .constraints.hinges[relation.positive.sample_index];
        auto& negative_output =
            result.frame
                .bodies[relation.negative.body_index]
                .constraints.hinges[relation.negative.sample_index];
        positive_output.angular = refreshed.positive_angular;
        positive_output.linear = refreshed.positive_linear;
        negative_output.angular = refreshed.negative_angular;
        negative_output.linear = refreshed.negative_linear;
        result.refreshed_hinge_sample_count += 2u;
    }

    for (const auto& relation : relations.bars) {
        validate_endpoint(
            source,
            relation.positive,
            bar_coverage,
            1u,
            "BAR positive",
            [](const BodyConstraintAssemblyInput& body)
                -> const std::vector<PreparedBarSample>& {
                return body.bars;
            });
        validate_endpoint(
            source,
            relation.negative,
            bar_coverage,
            0u,
            "BAR negative",
            [](const BodyConstraintAssemblyInput& body)
                -> const std::vector<PreparedBarSample>& {
                return body.bars;
            });

        const auto& positive_body =
            source.bodies[relation.positive.body_index].constraints;
        const auto& negative_body =
            source.bodies[relation.negative.body_index].constraints;
        const auto& positive_sample =
            positive_body.bars[relation.positive.sample_index];
        const auto& negative_sample =
            negative_body.bars[relation.negative.sample_index];
        if (positive_sample.scalar_base !=
            negative_sample.scalar_base) {
            throw std::runtime_error(
                "BAR endpoint scalar bases do not match");
        }
        if (positive_sample.side_bias !=
            negative_sample.side_bias) {
            throw std::runtime_error(
                "BAR endpoint side biases do not match");
        }

        BarConstraintRefreshInput input{};
        input.positive_body_frame =
            positive_body.preprojection.body_frame;
        input.negative_body_frame =
            negative_body.preprojection.body_frame;
        input.positive_body_position =
            positive_body.body_position;
        input.negative_body_position =
            negative_body.body_position;
        input.positive_local_point =
            relation.positive_local_point;
        input.negative_local_point =
            relation.negative_local_point;
        const auto refreshed =
            refresh_fun_007b2f70_bar(input);

        auto& positive_output =
            result.frame
                .bodies[relation.positive.body_index]
                .constraints.bars[relation.positive.sample_index];
        auto& negative_output =
            result.frame
                .bodies[relation.negative.body_index]
                .constraints.bars[relation.negative.sample_index];
        positive_output.point = refreshed.positive_point;
        negative_output.point = refreshed.negative_point;
        positive_output.direction = refreshed.direction;
        negative_output.direction = refreshed.direction;
        result.refreshed_bar_sample_count += 2u;
    }

    require_complete_coverage(
        joint_coverage,
        "JOINT");
    require_complete_coverage(
        hinge_coverage,
        "HINGE");
    require_complete_coverage(
        bar_coverage,
        "BAR");

    return result;
}

}  // namespace shift::runtime::physics
