#pragma once

#include <vulkan/vulkan.h>

#include <atomic>
#include <cstdio>
#include <stdexcept>
#include <vector>

namespace shift::vulkan {

// Keep this object alive until the instance has been destroyed: both the
// persistent messenger and instance creation/destruction callbacks use it.
class Validation {
public:
    bool enabled = false;

    uint32_t error_count() const { return errors_.load(); }

    void create_instance(VkInstanceCreateInfo info,
                         std::vector<const char*> extensions,
                         VkInstance& instance) {
        const char* layer = "VK_LAYER_KHRONOS_validation";
        VkDebugUtilsMessengerCreateInfoEXT debug{};
        debug.sType = VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT;
        debug.messageSeverity = VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT |
                                VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT;
        debug.messageType = VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT |
                            VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT |
                            VK_DEBUG_UTILS_MESSAGE_TYPE_PERFORMANCE_BIT_EXT;
        debug.pfnUserCallback = callback;
        debug.pUserData = this;
        if (enabled) {
            extensions.push_back(VK_EXT_DEBUG_UTILS_EXTENSION_NAME);
            info.enabledLayerCount = 1;
            info.ppEnabledLayerNames = &layer;
            info.pNext = &debug;
        }
        info.enabledExtensionCount = static_cast<uint32_t>(extensions.size());
        info.ppEnabledExtensionNames = extensions.data();
        if (vkCreateInstance(&info, nullptr, &instance) != VK_SUCCESS) {
            throw std::runtime_error(enabled ?
                "vkCreateInstance failed: --validation requires VK_LAYER_KHRONOS_validation and VK_EXT_debug_utils" :
                "vkCreateInstance failed");
        }
        if (enabled) {
            auto create = reinterpret_cast<PFN_vkCreateDebugUtilsMessengerEXT>(
                vkGetInstanceProcAddr(instance, "vkCreateDebugUtilsMessengerEXT"));
            if (!create || create(instance, &debug, nullptr, &messenger_) != VK_SUCCESS) {
                throw std::runtime_error("validation debug messenger creation failed");
            }
        }
    }

    void detach(VkInstance instance) {
        if (messenger_) {
            auto destroy = reinterpret_cast<PFN_vkDestroyDebugUtilsMessengerEXT>(
                vkGetInstanceProcAddr(instance, "vkDestroyDebugUtilsMessengerEXT"));
            if (destroy) destroy(instance, messenger_, nullptr);
            messenger_ = VK_NULL_HANDLE;
        }
    }

private:
    std::atomic<uint32_t> errors_{0};
    VkDebugUtilsMessengerEXT messenger_ = VK_NULL_HANDLE;

    static VKAPI_ATTR VkBool32 VKAPI_CALL callback(
        VkDebugUtilsMessageSeverityFlagBitsEXT severity,
        VkDebugUtilsMessageTypeFlagsEXT,
        const VkDebugUtilsMessengerCallbackDataEXT* data, void* user) {
        auto& state = *static_cast<Validation*>(user);
        if (severity & VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT) {
            ++state.errors_;
        }
        std::fprintf(stderr, "Vulkan validation: %s\n", data->pMessage);
        return VK_FALSE;
    }
};

}  // namespace shift::vulkan
