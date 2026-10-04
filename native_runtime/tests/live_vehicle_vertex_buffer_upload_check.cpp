#include "shift_live_vehicle_vertex_buffer_upload.hpp"

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
        buffer = VK_NULL_HANDLE;
        memory = VK_NULL_HANDLE;
        device = VK_NULL_HANDLE;
        bytes = 0u;
    }
};

TestBuffer create_test_buffer(
    VkPhysicalDevice physical,
    VkDevice device,
    const std::vector<std::uint8_t>& initial) {
    TestBuffer out{};
    out.device = device;
    out.bytes = initial.size();

    VkBufferCreateInfo buffer_info{};
    buffer_info.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    buffer_info.size = static_cast<VkDeviceSize>(initial.size());
    buffer_info.usage = VK_BUFFER_USAGE_VERTEX_BUFFER_BIT;
    buffer_info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    vk_require(
        vkCreateBuffer(device, &buffer_info, nullptr, &out.buffer),
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

std::vector<std::uint8_t> read_test_buffer(const TestBuffer& buffer) {
    std::vector<std::uint8_t> result(buffer.bytes);
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
    std::memcpy(result.data(), mapped, result.size());
    vkUnmapMemory(buffer.device, buffer.memory);
    return result;
}

void append_float3(
    std::vector<std::uint8_t>& bytes,
    float x,
    float y,
    float z) {
    const float values[3] = {x, y, z};
    const auto* raw = reinterpret_cast<const std::uint8_t*>(values);
    bytes.insert(bytes.end(), raw, raw + sizeof(values));
}

VehicleObjectGeometry geometry(
    float x0,
    float y0,
    float z0,
    float x1,
    float y1,
    float z1) {
    VehicleObjectGeometry out{};
    out.stride = 12u;
    out.attributes = {{0u, 2u, 0u, 12u, 200u}};
    append_float3(out.vertex_bytes, x0, y0, z0);
    append_float3(out.vertex_bytes, x1, y1, z1);
    return out;
}

VehicleWorldMatrix translation(float x, float y, float z) {
    return {
        1.0f, 0.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f, 0.0f,
        0.0f, 0.0f, 1.0f, 0.0f,
        x, y, z, 1.0f,
    };
}

std::array<float, 3> first_position(
    const std::vector<std::uint8_t>& bytes) {
    require(bytes.size() >= 12u, "vertex payload too small");
    std::array<float, 3> value{};
    std::memcpy(value.data(), bytes.data(), sizeof(value));
    return value;
}

void require_close(float actual, float expected, const char* label) {
    if (std::fabs(actual - expected) > 1.0e-5f) {
        throw std::runtime_error(
            std::string(label) + " mismatch " +
            std::to_string(actual) + " vs " +
            std::to_string(expected));
    }
}

}  // namespace

int main() {
    VkInstance instance = VK_NULL_HANDLE;
    VkDevice device = VK_NULL_HANDLE;
    std::vector<TestBuffer> buffers;

    try {
        VkApplicationInfo application{};
        application.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
        application.pApplicationName = "SHIFT Phase 647 check";
        application.apiVersion = VK_API_VERSION_1_0;
        VkInstanceCreateInfo instance_info{};
        instance_info.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
        instance_info.pApplicationInfo = &application;
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
                instance,
                &physical_count,
                physical_devices.data()),
            "vkEnumeratePhysicalDevices failed");
        const VkPhysicalDevice physical = physical_devices.front();

        std::uint32_t family_count = 0u;
        vkGetPhysicalDeviceQueueFamilyProperties(
            physical, &family_count, nullptr);
        require(family_count != 0u, "physical device exposes no queue family");
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
        VkDeviceQueueCreateInfo queue_info{};
        queue_info.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
        queue_info.queueFamilyIndex = queue_family;
        queue_info.queueCount = 1u;
        queue_info.pQueuePriorities = &priority;
        VkDeviceCreateInfo device_info{};
        device_info.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
        device_info.queueCreateInfoCount = 1u;
        device_info.pQueueCreateInfos = &queue_info;
        vk_require(
            vkCreateDevice(physical, &device_info, nullptr, &device),
            "vkCreateDevice failed");

        const std::vector<VehicleObjectGeometry> immutable = {
            geometry(100.0f, 200.0f, 300.0f, 101.0f, 201.0f, 301.0f),
            geometry(1.0f, 2.0f, 3.0f, 4.0f, 5.0f, 6.0f),
            geometry(-100.0f, -200.0f, -300.0f, -101.0f, -201.0f, -301.0f),
        };
        const std::vector<std::string> groups = {
            "track", "vehicle", "track"
        };

        buffers.reserve(immutable.size());
        for (const auto& draw : immutable) {
            buffers.push_back(
                create_test_buffer(physical, device, draw.vertex_bytes));
        }
        std::vector<LiveVehicleVertexBufferTarget> targets;
        for (const auto& buffer : buffers) {
            targets.push_back({device, buffer.memory, buffer.bytes});
        }

        const auto track0_before = read_test_buffer(buffers[0]);
        const auto track2_before = read_test_buffer(buffers[2]);

        const auto first = upload_live_vehicle_vertex_buffers(
            groups,
            immutable,
            targets,
            translation(10.0f, 20.0f, 30.0f));
        require(first.vehicle_draw_indices == std::vector<std::size_t>{1u},
                "Phase 647 updated a non-vehicle draw");
        require(first.uploaded_bytes == immutable[1].vertex_bytes.size(),
                "Phase 647 uploaded byte count mismatch");
        require(read_test_buffer(buffers[0]) == track0_before,
                "Phase 647 mutated first track buffer");
        require(read_test_buffer(buffers[2]) == track2_before,
                "Phase 647 mutated second track buffer");

        auto vehicle_bytes = read_test_buffer(buffers[1]);
        auto position = first_position(vehicle_bytes);
        require_close(position[0], 11.0f, "first vehicle x");
        require_close(position[1], 22.0f, "first vehicle y");
        require_close(position[2], 33.0f, "first vehicle z");

        // A second update must reapply from Phase 646 immutable object-space
        // geometry, never from bytes uploaded by the previous frame.
        const auto second = upload_live_vehicle_vertex_buffers(
            groups,
            immutable,
            targets,
            translation(-4.0f, 5.0f, 0.5f));
        require(second.vehicle_draw_indices == first.vehicle_draw_indices,
                "Phase 647 vehicle draw identity drifted between frames");
        vehicle_bytes = read_test_buffer(buffers[1]);
        position = first_position(vehicle_bytes);
        require_close(position[0], -3.0f, "second vehicle x");
        require_close(position[1], 7.0f, "second vehicle y");
        require_close(position[2], 3.5f, "second vehicle z");

        const auto before_bad_size = read_test_buffer(buffers[1]);
        auto bad_targets = targets;
        --bad_targets[1].vertex_payload_bytes;
        bool bad_size_rejected = false;
        try {
            (void)upload_live_vehicle_vertex_buffers(
                groups,
                immutable,
                bad_targets,
                translation(1.0f, 2.0f, 3.0f));
        } catch (const std::invalid_argument&) {
            bad_size_rejected = true;
        }
        require(bad_size_rejected,
                "Phase 647 accepted a mismatched Vulkan payload size");
        require(read_test_buffer(buffers[1]) == before_bad_size,
                "Phase 647 size validation partially mutated vehicle memory");

        bool no_vehicle_rejected = false;
        try {
            (void)upload_live_vehicle_vertex_buffers(
                {"track", "track", "track"},
                immutable,
                targets,
                translation(0.0f, 0.0f, 0.0f));
        } catch (const std::invalid_argument&) {
            no_vehicle_rejected = true;
        }
        require(no_vehicle_rejected,
                "Phase 647 accepted a scene without vehicle draw identity");

        bool alias_rejected = false;
        try {
            std::vector<VehicleObjectGeometry> two_geometry = {
                immutable[1], immutable[1]
            };
            std::vector<LiveVehicleVertexBufferTarget> aliases = {
                targets[1], targets[1]
            };
            (void)upload_live_vehicle_vertex_buffers(
                {"vehicle", "vehicle"},
                two_geometry,
                aliases,
                translation(0.0f, 0.0f, 0.0f));
        } catch (const std::invalid_argument&) {
            alias_rejected = true;
        }
        require(alias_rejected,
                "Phase 647 accepted aliased vehicle Vulkan memory");

        bool singular_rejected = false;
        try {
            auto singular = translation(0.0f, 0.0f, 0.0f);
            singular[0] = 0.0f;
            (void)upload_live_vehicle_vertex_buffers(
                groups, immutable, targets, singular);
        } catch (const std::runtime_error&) {
            singular_rejected = true;
        }
        require(singular_rejected,
                "Phase 647 accepted singular vehicle world matrix");

        for (auto& buffer : buffers) buffer.destroy();
        buffers.clear();
        vkDestroyDevice(device, nullptr);
        device = VK_NULL_HANDLE;
        vkDestroyInstance(instance, nullptr);
        instance = VK_NULL_HANDLE;

        std::cout
            << "{\"format\":\""
            << kLiveVehicleVertexBufferUploadFormat << "\","
            << "\"ready\":true,"
            << "\"vehicle_draw_count\":1,"
            << "\"track_buffers_untouched\":true,"
            << "\"non_cumulative_reapply\":true,"
            << "\"real_vulkan_memory_upload\":true}\n";
        return 0;
    } catch (const std::exception& error) {
        for (auto& buffer : buffers) buffer.destroy();
        if (device != VK_NULL_HANDLE) vkDestroyDevice(device, nullptr);
        if (instance != VK_NULL_HANDLE) vkDestroyInstance(instance, nullptr);
        std::cerr
            << "live_vehicle_vertex_buffer_upload_check: "
            << error.what() << '\n';
        return 1;
    }
}
