#include <iostream>

#include <rex/ui/flags.h>
#include <rex/ui/vulkan/provider.h>

int main() {
  REXCVAR_SET(vulkan_validation_enabled, true);
  auto provider =
      rex::ui::vulkan::VulkanProvider::Create(false, false, false, true);
  if (!provider || !provider->vulkan_device()) {
    std::cerr << "Vulkan provider could not create a device\n";
    return 1;
  }

  const auto &device = *provider->vulkan_device();
  const auto &extensions = device.extensions();
  const auto &properties = device.properties();
  const bool renderpass2_enabled = extensions.ext_1_2_KHR_create_renderpass2;
  const bool depth_resolve_enabled =
      extensions.ext_1_2_KHR_depth_stencil_resolve;
  if (renderpass2_enabled != depth_resolve_enabled ||
      (properties.depthStencilResolveSampleZero && !renderpass2_enabled)) {
    std::cerr
        << "depth/stencil resolve extensions were not enabled atomically\n";
    return 1;
  }
  if (properties.robustBufferAccess || properties.fullDrawIndexUint32 ||
      properties.independentBlend || properties.geometryShader ||
      properties.fragmentStoresAndAtomics ||
      properties.vertexPipelineStoresAndAtomics) {
    std::cerr
        << "depth/stencil resolve request enabled GPU-emulation features\n";
    return 1;
  }

  std::cout << "device=" << properties.deviceName
            << " Vulkan=" << VK_API_VERSION_MAJOR(properties.apiVersion) << "."
            << VK_API_VERSION_MINOR(properties.apiVersion)
            << " provider depth/stencil resolve pair=" << renderpass2_enabled
            << " SAMPLE_ZERO=" << properties.depthStencilResolveSampleZero
            << " GPU-emulation features=disabled\n";
  return 0;
}
