#include "shift_bmw_persistent_world_transform_runtime_wiring.hpp"

#include <array>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

using shift::runtime::physics::bmw_persistent_world_transform_runtime_detail::SvwtHeader;
using shift::runtime::physics::resolve_authoritative_vehicle_vhf_bind;
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

}  // namespace

int main() {
    try {
        const auto base =
            std::filesystem::temp_directory_path() /
            "shift_s4_bmw_persistent_world_transform_runtime_wiring";
        std::filesystem::remove_all(base);

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

        std::filesystem::remove_all(base);
        std::cout
            << "{\"format\":\"SHIFT.BMWPersistentWorldTransformRuntimeWiring/1\","
            << "\"ready\":true,"
            << "\"authoritative_vehicle_svwt_ready\":true,"
            << "\"multi_submesh_matrix_consensus_required\":true,"
            << "\"disagreement_rejected\":true,"
            << "\"svwt_abi_drift_rejected\":true,"
            << "\"arbitrary_vehicle_draw_selection\":false,"
            << "\"retail_scheduler_claimed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr
            << "bmw_persistent_world_transform_runtime_wiring_check: "
            << exc.what() << '\n';
        return 1;
    }
}
