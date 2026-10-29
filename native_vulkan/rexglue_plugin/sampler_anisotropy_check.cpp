#include <algorithm>
#include <iostream>

#include <rex/ui/flags.h>
#include <rex/ui/vulkan/provider.h>

extern "C" __attribute__((visibility("default"))) int
rexgpu_shift_native_check_sampler_anisotropy() {
  REXCVAR_SET(vulkan_validation_enabled, true);
  auto provider =
      rex::ui::vulkan::VulkanProvider::Create(false, false, false, false, true);
  if (!provider || !provider->vulkan_device()) {
    std::cerr << "Vulkan provider could not create a device with optional sampler anisotropy\n";
    return 1;
  }

  const auto& device = *provider->vulkan_device();
  const auto& properties = device.properties();
  VkPhysicalDeviceFeatures supported{};
  device.vulkan_instance()->functions().vkGetPhysicalDeviceFeatures(device.physical_device(),
                                                                   &supported);
  const bool expected_anisotropy = supported.samplerAnisotropy == VK_TRUE;
  if (properties.samplerAnisotropy != expected_anisotropy ||
      properties.robustBufferAccess || properties.fullDrawIndexUint32 ||
      properties.independentBlend || properties.geometryShader ||
      properties.tessellationShader || properties.sampleRateShading ||
      properties.depthClamp || properties.fillModeNonSolid ||
      properties.occlusionQueryPrecise || properties.fragmentStoresAndAtomics ||
      properties.vertexPipelineStoresAndAtomics || properties.shaderClipDistance ||
      properties.shaderCullDistance || properties.sparseBinding ||
      properties.sparseResidencyBuffer) {
    std::cerr << "sampler anisotropy request did not stay independent of GPU-emulation features\n";
    return 1;
  }
  if (properties.samplerAnisotropy && properties.maxSamplerAnisotropy <= 1.0f) {
    std::cerr << "enabled sampler anisotropy has an invalid maximum ratio\n";
    return 1;
  }

  if (properties.samplerAnisotropy) {
    VkSamplerCreateInfo sampler_info{};
    sampler_info.sType = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO;
    sampler_info.magFilter = VK_FILTER_LINEAR;
    sampler_info.minFilter = VK_FILTER_LINEAR;
    sampler_info.mipmapMode = VK_SAMPLER_MIPMAP_MODE_NEAREST;
    sampler_info.addressModeU = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    sampler_info.addressModeV = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    sampler_info.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    sampler_info.maxLod = 0.0f;
    sampler_info.maxAnisotropy = std::min(4.0f, properties.maxSamplerAnisotropy);
    sampler_info.anisotropyEnable = VK_TRUE;
    VkSampler sampler = VK_NULL_HANDLE;
    if (device.functions().vkCreateSampler(device.device(), &sampler_info, nullptr, &sampler) !=
            VK_SUCCESS ||
        sampler == VK_NULL_HANDLE) {
      std::cerr << "Vulkan rejected a captured 4:1 sampler request\n";
      return 1;
    }
    device.functions().vkDestroySampler(device.device(), sampler, nullptr);
  }

  std::cout << "device=" << properties.deviceName
            << " samplerAnisotropy=" << properties.samplerAnisotropy
            << " max=" << properties.maxSamplerAnisotropy
            << " GPU-emulation features=disabled\n";
  return 0;
}
