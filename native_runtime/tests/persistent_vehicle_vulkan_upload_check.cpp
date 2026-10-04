#include "runtime_state.hpp"
#include "shift_persistent_vehicle_vulkan_upload.hpp"

#include <vulkan/vulkan.h>

#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
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

}  // namespace

int main() {
    VkInstance instance = VK_NULL_HANDLE;
    VkDevice device = VK_NULL_HANDLE;
    std::array<VkFence, 2> fences{VK_NULL_HANDLE, VK_NULL_HANDLE};
    std::vector<TestBuffer> buffers;

    try {
        VkApplicationInfo app{};
        app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
        app.pApplicationName = "SHIFT Phase 649 check";
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
        const std::vector<std::string> groups = {"track", "vehicle"};
        buffers.reserve(immutable.size());
        for (const auto& geometry : immutable) {
            buffers.push_back(
                create_buffer(physical, device, geometry.vertex_bytes));
        }
        std::vector<LiveVehicleVertexBufferTarget> targets;
        for (const auto& buffer : buffers) {
            targets.push_back({device, buffer.memory, buffer.bytes});
        }

        const auto track_before = read_buffer(buffers[0]);

        NativeRuntimeState runtime{};
        runtime.outer_update.initialized = true;
        runtime.outer_update.body_count = 1u;
        runtime.outer_update.body_pose_snapshot_generation = 11u;
        runtime.outer_update.explicit_update_count = 9u;
        PersistentBodyPoseSnapshot body0{};
        body0.body_index = 0u;
        body0.origin = {10.0, 20.0, 30.0};
        body0.basis = {
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };
        runtime.outer_update.body_pose_snapshots = {body0};

        PersistentBmwVehicleWorldTransformState state{};
        state.ready = true;
        state.body_index = 0u;
        state.source_runtime_body_count = 1u;
        state.source_pose_snapshot_generation = 11u;
        state.source_explicit_update_count = 9u;
        state.commit_generation = 4u;
        state.source_origin = body0.origin;
        state.source_basis = body0.basis;
        state.vehicle_world_matrix = translation(5.0f, 6.0f, 7.0f);

        const auto uploaded =
            upload_current_bmw_vehicle_world_transform_to_vulkan(
                device,
                fences.data(),
                fences.size(),
                groups,
                immutable,
                targets,
                state,
                runtime);
        require(uploaded.all_frame_fences_waited,
                "Phase 649 did not wait all frame fences");
        require(uploaded.snapshot.commit_generation == 4u,
                "Phase 649 lost Phase 706 commit generation");
        require(uploaded.upload.vehicle_draw_indices ==
                    std::vector<std::size_t>{1u},
                "Phase 649 updated non-vehicle draw");
        require(read_buffer(buffers[0]) == track_before,
                "Phase 649 mutated track Vulkan memory");
        auto vehicle = position(read_buffer(buffers[1]));
        require_close(vehicle[0], 6.0f, "vehicle x");
        require_close(vehicle[1], 8.0f, "vehicle y");
        require_close(vehicle[2], 10.0f, "vehicle z");

        const auto committed_vehicle_bytes = read_buffer(buffers[1]);
        ++runtime.outer_update.body_pose_snapshot_generation;
        bool stale_generation_rejected = false;
        try {
            (void)upload_current_bmw_vehicle_world_transform_to_vulkan(
                device,
                fences.data(),
                fences.size(),
                groups,
                immutable,
                targets,
                state,
                runtime);
        } catch (const std::logic_error&) {
            stale_generation_rejected = true;
        }
        require(stale_generation_rejected,
                "Phase 649 accepted stale Phase 706 generation");
        require(read_buffer(buffers[1]) == committed_vehicle_bytes,
                "Phase 649 stale-generation rejection mutated Vulkan memory");
        --runtime.outer_update.body_pose_snapshot_generation;

        runtime.outer_update.body_pose_snapshots[0].origin[0] += 1.0;
        bool changed_pose_rejected = false;
        try {
            (void)upload_current_bmw_vehicle_world_transform_to_vulkan(
                device,
                fences.data(),
                fences.size(),
                groups,
                immutable,
                targets,
                state,
                runtime);
        } catch (const std::logic_error&) {
            changed_pose_rejected = true;
        }
        require(changed_pose_rejected,
                "Phase 649 accepted changed BODY0 pose with reused generations");
        require(read_buffer(buffers[1]) == committed_vehicle_bytes,
                "Phase 649 changed-pose rejection mutated Vulkan memory");
        runtime.outer_update.body_pose_snapshots[0].origin = body0.origin;

        bool missing_fences_rejected = false;
        try {
            (void)upload_current_bmw_vehicle_world_transform_to_vulkan(
                device,
                nullptr,
                0u,
                groups,
                immutable,
                targets,
                state,
                runtime);
        } catch (const std::invalid_argument&) {
            missing_fences_rejected = true;
        }
        require(missing_fences_rejected,
                "Phase 649 accepted missing frame fences");
        require(read_buffer(buffers[1]) == committed_vehicle_bytes,
                "Phase 649 missing-fence rejection mutated Vulkan memory");

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

        std::cout
            << "{\"format\":\""
            << kPersistentVehicleVulkanUploadFormat << "\","
            << "\"phase\":649,"
            << "\"phase706_freshness_before_gpu_write\":true,"
            << "\"phase647_upload_reused\":true,"
            << "\"all_frame_fences_waited\":true,"
            << "\"track_buffers_untouched\":true,"
            << "\"stale_generation_no_gpu_mutation\":true,"
            << "\"changed_pose_no_gpu_mutation\":true,"
            << "\"real_vulkan_memory_upload\":true}\n";
        return 0;
    } catch (const std::exception& error) {
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
        std::cerr
            << "persistent_vehicle_vulkan_upload_check: "
            << error.what() << '\n';
        return 1;
    }
}
