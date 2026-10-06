#include "runtime_state.hpp"
#include "shift_bmw_persistent_world_transform_runtime_wiring.hpp"
#include "fun_00770e80_outer_update_fixture.hpp"

#include <array>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using namespace shift::runtime;
using namespace shift::runtime::physics;
using namespace shift::runtime::test_fixture;
using shift::runtime::physics::bmw_persistent_world_transform_runtime_detail::SvwtHeader;
using shift::runtime::physics::bmw_persistent_world_transform_runtime_detail::resolve_authoritative_vehicle_vhf_bind;
using shift::runtime::render::VehicleWorldMatrix;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

VehicleWorldMatrix matrix(float tx, float ty, float tz) {
    return {
        1.0f, 0.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f, 0.0f,
        0.0f, 0.0f, 1.0f, 0.0f,
        tx, ty, tz, 1.0f,
    };
}

void write_svwt(
    const std::filesystem::path& path,
    const VehicleWorldMatrix& value,
    std::uint32_t version = 1u) {
    std::filesystem::create_directories(path.parent_path());
    std::ofstream file(path, std::ios::binary | std::ios::trunc);
    if (!file) {
        throw std::runtime_error("could not create S4 SVWT fixture");
    }
    SvwtHeader header{{'S', 'V', 'W', 'T'}, version, 1u, 64u};
    file.write(reinterpret_cast<const char*>(&header), sizeof(header));
    file.write(
        reinterpret_cast<const char*>(value.data()),
        static_cast<std::streamsize>(value.size() * sizeof(float)));
}

std::filesystem::path make_scene(
    const std::filesystem::path& root,
    const VehicleWorldMatrix& first,
    const VehicleWorldMatrix& second) {
    std::filesystem::create_directories(root / "draw_0000");
    std::filesystem::create_directories(root / "draw_0001");
    std::filesystem::create_directories(root / "draw_0002");
    {
        std::ofstream groups(root / "bundle_set.groups");
        groups << "track\nvehicle\nvehicle\n";
    }
    {
        std::ofstream paths(root / "bundle_set.paths");
        paths << "draw_0000\ndraw_0001\ndraw_0002\n";
    }
    write_svwt(root / "draw_0001" / "world_transform.svwt", first);
    write_svwt(root / "draw_0002" / "world_transform.svwt", second);
    return root;
}

#pragma pack(push, 1)
struct BbfpHeader {
    char magic[4];
    std::uint32_t version;
    std::uint32_t body_index;
    std::uint32_t source_target_count;
    std::uint32_t source_target_blob_bytes;
    float matrix[16];
};
#pragma pack(pop)

static_assert(sizeof(BbfpHeader) == 84u);

void write_bbfp(const std::filesystem::path& path) {
    const std::string source_target = "FUN_007633b0";
    const std::uint32_t source_bytes =
        static_cast<std::uint32_t>(source_target.size());
    const std::uint32_t blob_bytes =
        static_cast<std::uint32_t>(sizeof(std::uint32_t)) + source_bytes;
    const VehicleWorldMatrix body0_bind = {
        1.0f, 0.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f, 0.0f,
        0.0f, 0.0f, 1.0f, 0.0f,
        0.0f, -0.004956085581085581f, -0.01147086247086247f, 1.0f,
    };

    BbfpHeader header{};
    std::memcpy(header.magic, "BBFP", 4u);
    header.version = 1u;
    header.body_index = 0u;
    header.source_target_count = 1u;
    header.source_target_blob_bytes = blob_bytes;
    std::copy(body0_bind.begin(), body0_bind.end(), std::begin(header.matrix));

    std::ofstream file(path, std::ios::binary | std::ios::trunc);
    if (!file) {
        throw std::runtime_error("could not create S4 BBFP fixture");
    }
    file.write(reinterpret_cast<const char*>(&header), sizeof(header));
    file.write(reinterpret_cast<const char*>(&source_bytes), sizeof(source_bytes));
    file.write(
        source_target.data(),
        static_cast<std::streamsize>(source_target.size()));
}

NativeRuntimeState current_runtime_fixture() {
    NativeRuntimeState runtime{};
    runtime.physics.workspace.configure(2u, 1u, 1u);
    runtime.physics.participant_ready = true;
    runtime.physics.participant_identity_join_proven = true;
    const auto source = make_frame();
    const auto relations = make_relations();
    const auto projection = make_projection(source, relations);
    runtime.initialize_explicit_outer_update_body_state(
        make_raw_bodies(projection.bodies));
    return runtime;
}

}  // namespace

int main() {
    try {
        const auto base =
            std::filesystem::temp_directory_path() /
            "shift_s4_bmw_persistent_world_transform_runtime_wiring";
        std::filesystem::remove_all(base);
        std::filesystem::create_directories(base);

        const auto expected = matrix(4.0f, 5.0f, 6.0f);
        const auto same_scene = make_scene(base / "same", expected, expected);
        std::vector<std::size_t> indices;
        const auto bind = resolve_authoritative_vehicle_vhf_bind(
            same_scene.string(), 3u, &indices);
        require(bind.proven,
                "S4 did not mark authoritative vehicle VHF bind proven");
        require(bind.body_meb_to_vhf_vehicle_root == expected,
                "S4 changed authoritative vehicle SVWT matrix");
        require(indices.size() == 2u && indices[0] == 1u && indices[1] == 2u,
                "S4 lost explicit vehicle draw-group selection");

        const auto disagree_scene = make_scene(
            base / "disagree", expected, matrix(7.0f, 8.0f, 9.0f));
        bool disagreement_rejected = false;
        try {
            (void)resolve_authoritative_vehicle_vhf_bind(
                disagree_scene.string(), 3u);
        } catch (const std::runtime_error& exc) {
            disagreement_rejected =
                std::string(exc.what()).find("disagree") != std::string::npos;
        }
        require(disagreement_rejected,
                "S4 selected an arbitrary matrix from disagreeing vehicle draws");

        const auto bad_abi_scene = make_scene(
            base / "bad_abi", expected, expected);
        write_svwt(
            bad_abi_scene / "draw_0001" / "world_transform.svwt",
            expected,
            2u);
        bool bad_abi_rejected = false;
        try {
            (void)resolve_authoritative_vehicle_vhf_bind(
                bad_abi_scene.string(), 3u);
        } catch (const std::runtime_error& exc) {
            bad_abi_rejected =
                std::string(exc.what()).find("ABI") != std::string::npos;
        }
        require(bad_abi_rejected,
                "S4 accepted a non-SVWT-v1 vehicle bind packet");

        const auto missing_vehicle = base / "missing_vehicle";
        std::filesystem::create_directories(missing_vehicle / "draw_0000");
        {
            std::ofstream groups(missing_vehicle / "bundle_set.groups");
            groups << "track\n";
        }
        {
            std::ofstream paths(missing_vehicle / "bundle_set.paths");
            paths << "draw_0000\n";
        }
        bool missing_vehicle_rejected = false;
        try {
            (void)resolve_authoritative_vehicle_vhf_bind(
                missing_vehicle.string(), 1u);
        } catch (const std::runtime_error&) {
            missing_vehicle_rejected = true;
        }
        require(missing_vehicle_rejected,
                "S4 accepted a scene without a vehicle draw");

        // Full production-shaped continuation: no BBFP admission is inert;
        // after a positive BBFP admission the same post-step hook must commit a
        // current Phase 706 transform and publish it for Phase 715.
        auto runtime = current_runtime_fixture();
        require(
            !commit_and_publish_admitted_bmw_world_transform_after_fixed_step(
                runtime, same_scene.string(), true, 3u),
            "S4 moved vehicle without a positive BODY0 bind admission");
        require(!current_admitted_bmw_persistent_world_transform().ready,
                "S4 persistent state became ready without bind admission");

        const auto packet = base / "body0_bind.bbfp";
        write_bbfp(packet);
        if (::setenv(
                kBmwBody0BindFrameProofPacketEnv,
                packet.string().c_str(),
                1) != 0) {
            throw std::runtime_error("could not set S4 BBFP fixture environment");
        }
        const auto& admission =
            admit_bmw_body0_bind_frame_from_environment_once();
        require(admission.admitted && admission.bind_frame.ready,
                "S4 BBFP fixture was not positively admitted");

        const bool published =
            commit_and_publish_admitted_bmw_world_transform_after_fixed_step(
                runtime, same_scene.string(), true, 3u);
        require(published,
                "S4 positive bind admission did not publish persistent transform");
        const auto& persistent =
            current_admitted_bmw_persistent_world_transform();
        require(persistent.ready && persistent.body_index == 0u,
                "S4 published state does not identify current BMW BODY0");
        require(persistent.commit_generation == 1u,
                "S4 first post-step commit generation mismatch");
        require(
            persistent.source_pose_snapshot_generation ==
                runtime.outer_update.body_pose_snapshot_generation &&
            persistent.source_explicit_update_count ==
                runtime.outer_update.explicit_update_count,
            "S4 published transform lost current BODY0 freshness provenance");
        const auto current =
            read_current_bmw_vehicle_world_transform(persistent, runtime);
        require(current.commit_generation == persistent.commit_generation,
                "S4 published transform is not readable as current");

        std::filesystem::remove_all(base);
        std::cout
            << "{\"format\":\"SHIFT.BMWPersistentWorldTransformRuntimeWiring/1\","
            << "\"ready\":true,"
            << "\"authoritative_vehicle_svwt_ready\":true,"
            << "\"multi_submesh_matrix_consensus_required\":true,"
            << "\"disagreement_rejected\":true,"
            << "\"svwt_abi_drift_rejected\":true,"
            << "\"arbitrary_vehicle_draw_selection\":false,"
            << "\"positive_bbfp_required\":true,"
            << "\"post_step_persistent_commit_ready\":true,"
            << "\"phase715_publication_ready\":true,"
            << "\"freshness_provenance_retained\":true,"
            << "\"retail_scheduler_claimed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr
            << "bmw_persistent_world_transform_runtime_wiring_check: "
            << exc.what() << '\n';
        return 1;
    }
}
