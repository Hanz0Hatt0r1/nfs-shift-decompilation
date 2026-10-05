#include "shift_bmw_body0_bind_frame_admission.hpp"

#include <cmath>
#include <stdexcept>
#include <string_view>

namespace shift::runtime::physics {
namespace {

using shift::runtime::render::VehicleWorldMatrix;

constexpr std::uint32_t kRetailBmwChassisBodyIndex = 0u;
constexpr std::string_view kRetailBmwChassisBodyName = "body";
constexpr std::string_view kExpectedStatus = "ready";
constexpr std::string_view kExpectedEvidenceState = "proven-static";
constexpr std::string_view kExpectedFrameRelation =
    "BODY0-local-to-VHF-vehicle-root";
constexpr std::string_view kExpectedMatrixConvention =
    "row-major D3D row-vector affine";
constexpr float kAffineTolerance = 1.0e-6f;
constexpr double kSingularTolerance = 1.0e-12;

bool equals(const char* actual, std::string_view expected) {
    return actual != nullptr && std::string_view(actual) == expected;
}

double determinant3(const VehicleWorldMatrix& matrix) {
    const double a = matrix[0], b = matrix[1], c = matrix[2];
    const double d = matrix[4], e = matrix[5], f = matrix[6];
    const double g = matrix[8], h = matrix[9], i = matrix[10];
    return a * (e * i - f * h) -
           b * (d * i - f * g) +
           c * (d * h - e * g);
}

void validate_matrix(const VehicleWorldMatrix& matrix) {
    for (float value : matrix) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "BODY0 bind-frame proof matrix contains non-finite value");
        }
    }
    if (std::fabs(matrix[3]) > kAffineTolerance ||
        std::fabs(matrix[7]) > kAffineTolerance ||
        std::fabs(matrix[11]) > kAffineTolerance ||
        std::fabs(matrix[15] - 1.0f) > kAffineTolerance) {
        throw std::invalid_argument(
            "BODY0 bind-frame proof matrix is not D3D row-vector affine");
    }
    const double determinant = determinant3(matrix);
    if (!std::isfinite(determinant) ||
        std::fabs(determinant) <= kSingularTolerance) {
        throw std::invalid_argument(
            "BODY0 bind-frame proof matrix linear block is singular");
    }
}

void validate_source_targets(const BmwBody0BindFrameProofHandoff& proof) {
    if (proof.source_targets == nullptr || proof.source_target_count == 0u) {
        throw std::invalid_argument(
            "BODY0 bind-frame proof requires static source targets");
    }
    for (std::size_t index = 0u; index < proof.source_target_count; ++index) {
        const char* target = proof.source_targets[index];
        if (target == nullptr || target[0] == '\0') {
            throw std::invalid_argument(
                "BODY0 bind-frame proof contains empty static source target");
        }
    }
}

}  // namespace

ProvenBmwBody0BindFrame admit_bmw_body0_bind_frame_proof(
    const BmwBody0BindFrameProofHandoff& proof) {

    if (!equals(proof.format, kBmwBody0BindFrameProofFormat)) {
        throw std::invalid_argument(
            "BODY0 bind-frame handoff has wrong contract format");
    }
    if (!proof.ready || !equals(proof.status, kExpectedStatus)) {
        throw std::invalid_argument("BODY0 bind-frame proof is not ready");
    }
    if (!equals(proof.evidence_state, kExpectedEvidenceState)) {
        throw std::invalid_argument(
            "BODY0 bind-frame proof is not proven-static");
    }
    if (proof.body_index != kRetailBmwChassisBodyIndex) {
        throw std::invalid_argument(
            "BODY0 bind-frame proof does not identify retail BMW chassis BODY 0");
    }
    if (!equals(proof.body_name, kRetailBmwChassisBodyName)) {
        throw std::invalid_argument(
            "BODY0 bind-frame proof chassis BODY name drift");
    }
    if (!equals(proof.frame_relation, kExpectedFrameRelation)) {
        throw std::invalid_argument(
            "BODY0 bind-frame proof frame relation drift");
    }
    if (!equals(proof.matrix_convention, kExpectedMatrixConvention)) {
        throw std::invalid_argument(
            "BODY0 bind-frame proof matrix convention drift");
    }

    validate_source_targets(proof);

    if (proof.identity_matrix_assumed) {
        throw std::invalid_argument(
            "BODY0 bind-frame proof was produced by identity-matrix assumption");
    }
    if (proof.original_game_executed) {
        throw std::invalid_argument(
            "BODY0 bind-frame proof unexpectedly depends on original-game execution");
    }
    if (proof.new_runtime_capture_used) {
        throw std::invalid_argument(
            "BODY0 bind-frame proof unexpectedly depends on new runtime capture");
    }

    validate_matrix(proof.body0_local_to_vhf_vehicle_root_row_matrix);

    return ProvenBmwBody0BindFrame{
        true,
        true,
        kRetailBmwChassisBodyIndex,
        false,
        proof.body0_local_to_vhf_vehicle_root_row_matrix,
    };
}

}  // namespace shift::runtime::physics
