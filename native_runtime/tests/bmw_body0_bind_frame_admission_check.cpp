#include "shift_bmw_body0_bind_frame_admission.hpp"

#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

namespace {

using shift::runtime::physics::BmwBody0BindFrameProofHandoff;
using shift::runtime::physics::admit_bmw_body0_bind_frame_proof;
using shift::runtime::physics::kBmwBody0BindFrameProofFormat;
using shift::runtime::physics::kNativeBmwBody0BindFrameAdmissionFormat;
using shift::runtime::render::VehicleWorldMatrix;

const char* kSourceTargets[] = {
    "FUN_007b3670",
    "FUN_007bba90",
    "FUN_007bbb10",
    "FUN_007bbb60",
};

VehicleWorldMatrix source_backed_matrix_fixture() {
    return VehicleWorldMatrix{
        1.0f, 0.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f, 0.0f,
        0.0f, 0.0f, 1.0f, 0.0f,
        1.25f, -0.5f, 2.0f, 1.0f,
    };
}

BmwBody0BindFrameProofHandoff positive_fixture() {
    BmwBody0BindFrameProofHandoff proof{};
    proof.format = kBmwBody0BindFrameProofFormat;
    proof.ready = true;
    proof.status = "ready";
    proof.evidence_state = "proven-static";
    proof.body_index = 0u;
    proof.body_name = "body";
    proof.frame_relation = "BODY0-local-to-VHF-vehicle-root";
    proof.matrix_convention = "row-major D3D row-vector affine";
    proof.source_targets = kSourceTargets;
    proof.source_target_count = sizeof(kSourceTargets) / sizeof(kSourceTargets[0]);
    proof.identity_matrix_assumed = false;
    proof.original_game_executed = false;
    proof.new_runtime_capture_used = false;
    proof.body0_local_to_vhf_vehicle_root_row_matrix = source_backed_matrix_fixture();
    return proof;
}

template <typename Mutator>
void require_rejected(const char* label, Mutator mutator) {
    auto proof = positive_fixture();
    mutator(proof);
    try {
        (void)admit_bmw_body0_bind_frame_proof(proof);
    } catch (const std::invalid_argument&) {
        return;
    }
    throw std::runtime_error(std::string("admission unexpectedly accepted ") + label);
}

}  // namespace

int main() {
    const auto admitted = admit_bmw_body0_bind_frame_proof(positive_fixture());
    if (!admitted.ready || !admitted.evidence_proven_static ||
        admitted.body_index != 0u || admitted.identity_matrix_assumed) {
        throw std::runtime_error("positive proof did not materialize strict BODY0 admission");
    }
    if (admitted.body0_local_to_vhf_vehicle_root != source_backed_matrix_fixture()) {
        throw std::runtime_error("admission changed the source-backed bind matrix");
    }

    require_rejected("wrong format", [](auto& proof) {
        proof.format = "SHIFT.BMWBody0BindFrameProof/0";
    });
    require_rejected("not-ready proof", [](auto& proof) {
        proof.ready = false;
    });
    require_rejected("wrong status", [](auto& proof) {
        proof.status = "blocked";
    });
    require_rejected("non-static evidence", [](auto& proof) {
        proof.evidence_state = "inferred";
    });
    require_rejected("wrong BODY index", [](auto& proof) {
        proof.body_index = 1u;
    });
    require_rejected("wrong BODY name", [](auto& proof) {
        proof.body_name = "wheel";
    });
    require_rejected("wrong frame relation", [](auto& proof) {
        proof.frame_relation = "BODY0-local-to-MEB-object";
    });
    require_rejected("wrong matrix convention", [](auto& proof) {
        proof.matrix_convention = "column-major";
    });
    require_rejected("missing static provenance", [](auto& proof) {
        proof.source_targets = nullptr;
        proof.source_target_count = 0u;
    });
    require_rejected("identity assumption", [](auto& proof) {
        proof.identity_matrix_assumed = true;
    });
    require_rejected("original-game dependency", [](auto& proof) {
        proof.original_game_executed = true;
    });
    require_rejected("new runtime capture dependency", [](auto& proof) {
        proof.new_runtime_capture_used = true;
    });
    require_rejected("non-affine matrix", [](auto& proof) {
        proof.body0_local_to_vhf_vehicle_root_row_matrix[3] = 1.0f;
    });
    require_rejected("singular matrix", [](auto& proof) {
        proof.body0_local_to_vhf_vehicle_root_row_matrix[0] = 0.0f;
    });
    require_rejected("non-finite matrix", [](auto& proof) {
        proof.body0_local_to_vhf_vehicle_root_row_matrix[12] =
            std::numeric_limits<float>::infinity();
    });

    std::cout
        << "{\"format\":\"" << kNativeBmwBody0BindFrameAdmissionFormat << "\","
        << "\"upstream_contract\":\"" << kBmwBody0BindFrameProofFormat << "\","
        << "\"retail_BODY_index\":0,"
        << "\"required_status\":\"ready\","
        << "\"required_evidence_state\":\"proven-static\","
        << "\"source_targets_required\":true,"
        << "\"identity_bind_assumption_allowed\":false,"
        << "\"typed_admission_bridge_ready\":true,"
        << "\"current_retail_proof_present\":false,"
        << "\"current_retail_world_transform_ready\":false}"
        << '\n';

    return 0;
}
