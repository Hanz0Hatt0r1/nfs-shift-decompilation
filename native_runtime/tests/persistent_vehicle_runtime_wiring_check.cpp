#include "runtime_state.hpp"
#include "shift_phase715_persistent_vehicle_runtime_wiring.hpp"

#include <vulkan/vulkan.h>

#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using namespace shift::runtime;
using namespace shift::runtime::physics;
using namespace shift::runtime::render;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void vk_require(VkResult result, const char* message) {
    if (result != VK_SUCCESS) {
        throw std::runtime_error(
            std::string(message) + " VkResult=" +
            std::to_string(static_cast<int>(result)));
    }
}

std::uint32_t host_memory_type(
    VkPhysicalDevice physical,
    std::uint32_t type_bits) {
    VkPhysicalDeviceMemoryProperties properties{};
    vkGetPhysicalDeviceMemoryProperties(physical, &properties);
    const VkMemoryPropertyFlags required =
        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
        VK_MEMORY_PROPERTY_HOST_COHERENT_BIT;
    for (std::uint32_t index = 0u;
         index < properties.memoryTypeCount;
         ++index) {
        if ((type_bits & (1u << index)) != 0u &&
            (properties.memoryTypes[index].propertyFlags & required) == required) {
            return index;
        }
    }
    throw std::runtime_error(
        "no HOST_VISIBLE|HOST_COHERENT Vulkan memory type");
}

struct TestBuffer {
    VkDevice device = VK_NULL_HANDLE;
    VkBuffer buffer = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    std::size_t bytes = 0u;

    void destroy() {
        if (device != VK_NULL_HANDLE) {
            if (buffer != VK_NULL_HANDLE) {
                vkDestroyBuffer(device, buffer, nullptr);
            }
            if (memory != VK_NULL_HANDLE) {
                vkFreeMemory(device, memory, nullptr);
            }
        }
        device = VK_NULL_HANDLE;
        buffer = VK_NULL_HANDLE;
        memory = VK_NULL_HANDLE;
        bytes = 0u;
    }
};

TestBuffer create_buffer(
    VkPhysicalDevice physical,
    VkDevice device,
    const std::vector<std::uint8_t>& initial) {
    TestBuffer out{};
    out.device = device;
    out.bytes = initial.size();

    VkBufferCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    info.size = static_cast<VkDeviceSize>(initial.size());
    info.usage = VK_BUFFER_USAGE_VERTEX_BUFFER_BIT;
    info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    vk_require(
        vkCreateBuffer(device, &info, nullptr, &out.buffer),
        "vkCreateBuffer failed");

    VkMemoryRequirements requirements{};
    vkGetBufferMemoryRequirements(device, out.buffer, &requirements);
    VkMemoryAllocateInfo allocate{};
    allocate.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    allocate.allocationSize = requirements.size;
    allocate.memoryTypeIndex =
        host_memory_type(physical, requirements.memoryTypeBits);
    vk_require(
        vkAllocateMemory(device, &allocate, nullptr, &out.memory),
        "vkAllocateMemory failed");
    vk_require(
        vkBindBufferMemory(device, out.buffer, out.memory, 0),
        "vkBindBufferMemory failed");

    void* mapped = nullptr;
    vk_require(
        vkMapMemory(
            device,
            out.memory,
            0,
            static_cast<VkDeviceSize>(initial.size()),
            0,
            &mapped),
        "initial vkMapMemory failed");
    std::memcpy(mapped, initial.data(), initial.size());
    vkUnmapMemory(device, out.memory);
    return out;
}

std::vector<std::uint8_t> read_buffer(const TestBuffer& buffer) {
    std::vector<std::uint8_t> bytes(buffer.bytes);
    void* mapped = nullptr;
    vk_require(
        vkMapMemory(
            buffer.device,
            buffer.memory,
            0,
            static_cast<VkDeviceSize>(buffer.bytes),
            0,
            &mapped),
        "read vkMapMemory failed");
    std::memcpy(bytes.data(), mapped, bytes.size());
    vkUnmapMemory(buffer.device, buffer.memory);
    return bytes;
}

VehicleObjectGeometry one_vertex_geometry(float x, float y, float z) {
    VehicleObjectGeometry geometry{};
    geometry.stride = 12u;
    geometry.attributes = {{0u, 2u, 0u, 12u, 200u}};
    const float value[3] = {x, y, z};
    const auto* raw = reinterpret_cast<const std::uint8_t*>(value);
    geometry.vertex_bytes.assign(raw, raw + sizeof(value));
    return geometry;
}

VehicleWorldMatrix translation(float x, float y, float z) {
    return {
        1.0f, 0.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f, 0.0f,
        0.0f, 0.0f, 1.0f, 0.0f,
        x, y, z, 1.0f,
    };
}

std::array<float, 3> position(const std::vector<std::uint8_t>& bytes) {
    require(bytes.size() >= sizeof(float) * 3u, "vertex payload truncated");
    std::array<float, 3> result{};
    std::memcpy(result.data(), bytes.data(), sizeof(float) * 3u);
    return result;
}

void require_close(float actual, float expected, const char* label) {
    if (std::fabs(actual - expected) > 1.0e-5f) {
        throw std::runtime_error(
            std::string(label) + " mismatch: " +
            std::to_string(actual) + " vs " + std::to_string(expected));
    }
}

void write_geometry_packet(
    const std::filesystem::path& path,
    const VehicleObjectGeometry& geometry) {
    require(geometry.stride != 0u, "test geometry stride is zero");
    require(
        geometry.vertex_bytes.size() % geometry.stride == 0u,
        "test geometry vertex payload is misaligned");

    phase648_detail::GeometryHeader header{};
    std::memcpy(header.magic, "SVGP", 4u);
    header.version = 3u;
    header.vertex_count = static_cast<std::uint32_t>(
        geometry.vertex_bytes.size() / geometry.stride);
    header.index_count = 1u;
    header.stride = geometry.stride;
    header.attribute_count =
        static_cast<std::uint32_t>(geometry.attributes.size());
    header.first_index = 0u;
    header.scale = 1.0f;

    std::filesystem::create_directories(path.parent_path());
    std::ofstream file(path, std::ios::binary);
    require(static_cast<bool>(file), "cannot create test SVGP packet");
    file.write(reinterpret_cast<const char*>(&header), sizeof(header));
    for (const auto& attribute : geometry.attributes) {
        const phase648_detail::GeometryAttribute raw{
            attribute.location,
            attribute.format,
            attribute.offset,
            attribute.stride,
            attribute.property_id,
        };
        file.write(reinterpret_cast<const char*>(&raw), sizeof(raw));
    }
    file.write(
        reinterpret_cast<const char*>(geometry.vertex_bytes.data()),
        static_cast<std::streamsize>(geometry.vertex_bytes.size()));
    const std::uint32_t index = 0u;
    file.write(reinterpret_cast<const char*>(&index), sizeof(index));
    require(static_cast<bool>(file), "cannot write test SVGP packet");
}

struct FakeVertexBuffer {
    VkDeviceMemory memory = VK_NULL_HANDLE;
};

struct FakeMaterialDraw {
    FakeVertexBuffer vertex_buffer{};
};

struct FakeRenderRuntime {
    VkDevice device = VK_NULL_HANDLE;
    std::vector<VkFence> fences{};
    std::vector<FakeMaterialDraw> material_draws{};
};

PersistentBmwVehicleWorldTransformState make_state(
    const NativeRuntimeState& runtime,
    std::uint64_t commit_generation,
    const VehicleWorldMatrix& matrix) {
    PersistentBmwVehicleWorldTransformState state{};
    state.ready = true;
    state.body_index = 0u;
    state.source_runtime_body_count = runtime.outer_update.body_count;
    state.source_pose_snapshot_generation =
        runtime.outer_update.body_pose_snapshot_generation;
    state.source_explicit_update_count =
        runtime.outer_update.explicit_update_count;
    state.commit_generation = commit_generation;
    state.source_origin = runtime.outer_update.body_pose_snapshots.at(0).origin;
    state.source_basis = runtime.outer_update.body_pose_snapshots.at(0).basis;
    state.vehicle_world_matrix = matrix;
    return state;
}

}  // namespace

int main() {
    VkInstance instance = VK_NULL_HANDLE;
    VkDevice device = VK_NULL_HANDLE;
    std::vector<VkFence> fences(2u, VK_NULL_HANDLE);
    std::vector<TestBuffer> buffers;
    const auto scene_root =
        std::filesystem::temp_directory_path() /
        "shift_phase715_persistent_runtime_wiring_check";

    try {
        std::filesystem::remove_all(scene_root);

        VkApplicationInfo app{};
        app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
        app.pApplicationName = "SHIFT Phase 715 check";
        app.apiVersion = VK_API_VERSION_1_0;
        VkInstanceCreateInfo instance_info{};
        instance_info.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
        instance_info.pApplicationInfo = &app;
        vk_require(
            vkCreateInstance(&instance_info, nullptr, &instance),
            "vkCreateInstance failed");

        std::uint32_t physical_count = 0u;
        vk_require(
            vkEnumeratePhysicalDevices(instance, &physical_count, nullptr),
            "vkEnumeratePhysicalDevices count failed");
        require(physical_count != 0u, "no Vulkan physical device");
        std::vector<VkPhysicalDevice> physical_devices(physical_count);
        vk_require(
            vkEnumeratePhysicalDevices(
                instance, &physical_count, physical_devices.data()),
            "vkEnumeratePhysicalDevices failed");
        const VkPhysicalDevice physical = physical_devices.front();

        std::uint32_t family_count = 0u;
        vkGetPhysicalDeviceQueueFamilyProperties(
            physical, &family_count, nullptr);
        require(family_count != 0u, "no Vulkan queue family");
        std::vector<VkQueueFamilyProperties> families(family_count);
        vkGetPhysicalDeviceQueueFamilyProperties(
            physical, &family_count, families.data());
        std::uint32_t queue_family = family_count;
        for (std::uint32_t index = 0u; index < family_count; ++index) {
            if (families[index].queueCount != 0u) {
                queue_family = index;
                break;
            }
        }
        require(queue_family != family_count, "no usable Vulkan queue family");

        const float priority = 1.0f;
        VkDeviceQueueCreateInfo queue{};
        queue.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
        queue.queueFamilyIndex = queue_family;
        queue.queueCount = 1u;
        queue.pQueuePriorities = &priority;
        VkDeviceCreateInfo device_info{};
        device_info.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
        device_info.queueCreateInfoCount = 1u;
        device_info.pQueueCreateInfos = &queue;
        vk_require(
            vkCreateDevice(physical, &device_info, nullptr, &device),
            "vkCreateDevice failed");

        VkFenceCreateInfo fence_info{};
        fence_info.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
        fence_info.flags = VK_FENCE_CREATE_SIGNALED_BIT;
        for (VkFence& fence : fences) {
            vk_require(
                vkCreateFence(device, &fence_info, nullptr, &fence),
                "vkCreateFence failed");
        }

        const std::vector<VehicleObjectGeometry> immutable = {
            one_vertex_geometry(100.0f, 200.0f, 300.0f),
            one_vertex_geometry(1.0f, 2.0f, 3.0f),
        };
        std::filesystem::create_directories(scene_root);
        {
            std::ofstream groups(scene_root / "bundle_set.groups");
            groups << "track\nvehicle\n";
        }
        {
            std::ofstream paths(scene_root / "bundle_set.paths");
            paths << "draw_0000\ndraw_0001\n";
        }
        write_geometry_packet(
            scene_root / "draw_0000" / "geometry.svpk", immutable[0]);
        write_geometry_packet(
            scene_root / "draw_0001" / "geometry.svpk", immutable[1]);

        buffers.reserve(immutable.size());
        for (const auto& geometry : immutable) {
            buffers.push_back(
                create_buffer(physical, device, geometry.vertex_bytes));
        }
        const auto track_before = read_buffer(buffers[0]);
        const auto vehicle_before = read_buffer(buffers[1]);

        FakeRenderRuntime render_runtime{};
        render_runtime.device = device;
        render_runtime.fences = fences;
        for (const auto& buffer : buffers) {
            render_runtime.material_draws.push_back({{buffer.memory}});
        }

        NativeRuntimeState native_state{};
        native_state.outer_update.initialized = true;
        native_state.outer_update.body_count = 1u;
        native_state.outer_update.body_pose_snapshot_generation = 11u;
        native_state.outer_update.explicit_update_count = 9u;
        PersistentBodyPoseSnapshot body0{};
        body0.body_index = 0u;
        body0.origin = {10.0, 20.0, 30.0};
        body0.basis = {
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };
        native_state.outer_update.body_pose_snapshots = {body0};

        phase715_after_fixed_step(
            render_runtime,
            immutable,
            scene_root.string(),
            true,
            native_state,
            0u);
        require(read_buffer(buffers[0]) == track_before,
                "Phase 715 inert path mutated track memory");
        require(read_buffer(buffers[1]) == vehicle_before,
                "Phase 715 inert path mutated vehicle memory");

        const auto first = make_state(
            native_state, 1u, translation(5.0f, 6.0f, 7.0f));
        publish_persistent_bmw_vehicle_world_transform_for_render(first);
        phase715_after_fixed_step(
            render_runtime,
            immutable,
            scene_root.string(),
            true,
            native_state,
            0u);
        require(read_buffer(buffers[0]) == track_before,
                "Phase 715 first upload mutated track memory");
        auto vehicle = position(read_buffer(buffers[1]));
        require_close(vehicle[0], 6.0f, "first vehicle x");
        require_close(vehicle[1], 8.0f, "first vehicle y");
        require_close(vehicle[2], 10.0f, "first vehicle z");

        const auto first_vehicle_bytes = read_buffer(buffers[1]);
        bool unrefreshed_rejected = false;
        try {
            phase715_after_fixed_step(
                render_runtime,
                immutable,
                scene_root.string(),
                true,
                native_state,
                1u);
        } catch (const std::logic_error&) {
            unrefreshed_rejected = true;
        }
        require(unrefreshed_rejected,
                "Phase 715 accepted an unrefreshed persistent generation");
        require(read_buffer(buffers[1]) == first_vehicle_bytes,
                "Phase 715 unrefreshed rejection mutated vehicle memory");

        native_state.outer_update.body_pose_snapshot_generation = 12u;
        native_state.outer_update.body_pose_snapshots[0].origin[0] = 11.0;
        const auto second = make_state(
            native_state, 2u, translation(8.0f, 9.0f, 10.0f));
        publish_persistent_bmw_vehicle_world_transform_for_render(second);
        phase715_after_fixed_step(
            render_runtime,
            immutable,
            scene_root.string(),
            true,
            native_state,
            1u);
        vehicle = position(read_buffer(buffers[1]));
        require_close(vehicle[0], 9.0f, "second vehicle x");
        require_close(vehicle[1], 11.0f, "second vehicle y");
        require_close(vehicle[2], 13.0f, "second vehicle z");
        require(read_buffer(buffers[0]) == track_before,
                "Phase 715 second upload mutated track memory");

        bool duplicate_publish_rejected = false;
        try {
            publish_persistent_bmw_vehicle_world_transform_for_render(second);
        } catch (const std::logic_error&) {
            duplicate_publish_rejected = true;
        }
        require(duplicate_publish_rejected,
                "Phase 715 accepted duplicate commit generation publication");

        const auto second_vehicle_bytes = read_buffer(buffers[1]);
        const auto third = make_state(
            native_state, 3u, translation(12.0f, 13.0f, 14.0f));
        publish_persistent_bmw_vehicle_world_transform_for_render(third);
        ++native_state.outer_update.body_pose_snapshot_generation;
        bool stale_phase706_rejected = false;
        try {
            phase715_after_fixed_step(
                render_runtime,
                immutable,
                scene_root.string(),
                true,
                native_state,
                2u);
        } catch (const std::logic_error&) {
            stale_phase706_rejected = true;
        }
        require(stale_phase706_rejected,
                "Phase 715 bypassed Phase 706 freshness validation");
        require(read_buffer(buffers[1]) == second_vehicle_bytes,
                "Phase 715 stale Phase 706 rejection mutated vehicle memory");
        --native_state.outer_update.body_pose_snapshot_generation;

        require(
            ::setenv(kRuntimeVehicleWorldTransformScriptEnv, "test-script", 1) == 0,
            "setenv failed");
        bool script_conflict_rejected = false;
        try {
            phase715_after_fixed_step(
                render_runtime,
                immutable,
                scene_root.string(),
                true,
                native_state,
                2u);
        } catch (const std::logic_error&) {
            script_conflict_rejected = true;
        }
        ::unsetenv(kRuntimeVehicleWorldTransformScriptEnv);
        require(script_conflict_rejected,
                "Phase 715 accepted simultaneous persistent and script producers");
        require(read_buffer(buffers[1]) == second_vehicle_bytes,
                "Phase 715 script conflict mutated vehicle memory");

        for (auto& buffer : buffers) buffer.destroy();
        buffers.clear();
        for (VkFence& fence : fences) {
            vkDestroyFence(device, fence, nullptr);
            fence = VK_NULL_HANDLE;
        }
        vkDestroyDevice(device, nullptr);
        device = VK_NULL_HANDLE;
        vkDestroyInstance(instance, nullptr);
        instance = VK_NULL_HANDLE;
        std::filesystem::remove_all(scene_root);

        std::cout
            << "{\"format\":\""
            << kPersistentVehicleRuntimeWiringFormat << "\","
            << "\"phase\":715,"
            << "\"inert_before_publish\":true,"
            << "\"persistent_generation_uploaded\":true,"
            << "\"unrefreshed_generation_rejected\":true,"
            << "\"phase706_freshness_preserved\":true,"
            << "\"script_conflict_rejected_before_gpu\":true,"
            << "\"track_buffers_untouched\":true,"
            << "\"test_motion_script_required\":false,"
            << "\"retail_transform_producer_claimed\":false}\n";
        return 0;
    } catch (const std::exception& error) {
        ::unsetenv(kRuntimeVehicleWorldTransformScriptEnv);
        for (auto& buffer : buffers) buffer.destroy();
        if (device != VK_NULL_HANDLE) {
            for (VkFence& fence : fences) {
                if (fence != VK_NULL_HANDLE) {
                    vkDestroyFence(device, fence, nullptr);
                    fence = VK_NULL_HANDLE;
                }
            }
            vkDestroyDevice(device, nullptr);
        }
        if (instance != VK_NULL_HANDLE) {
            vkDestroyInstance(instance, nullptr);
        }
        std::filesystem::remove_all(scene_root);
        std::cerr
            << "persistent_vehicle_runtime_wiring_check: "
            << error.what() << '\n';
        return 1;
    }
}
