#include "shift_vulkan_d3d9_managed_texture_capability.hpp"
#include "shift_vulkan_d3d9_packet_capture.hpp"

#include <cstdlib>
#include <iostream>
#include <string>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "live managed DXT3 capability check failed: "
                  << message << '\n';
        std::exit(1);
    }
}

}  // namespace

int main() {
    shift::runtime::RecompiledGuestD3d9AdapterInfo adapter{};
    int runtime_context = 0;
    adapter.backend_context = &runtime_context;

    // Simulate the ordinary live adapter before the optional packet-capture
    // wrapper is installed. The P1 managed-texture gate needs this capability
    // even if capture is disabled.
    require(!adapter.supports_dxt3_texture,
            "D3D9 adapter contract starts without DXT3 support");
    shift::vulkan::enable_guest_managed_dxt3_capability(adapter);
    require(adapter.supports_dxt3_texture,
            "ordinary adapter accepts CPU-backed managed DXT3");
    require(!adapter.supports_dxt5_texture,
            "this change must not silently enable unrelated DXT5 support");
    require(adapter.backend_context == &runtime_context,
            "the capability must not replace the live backend context");
    require(adapter.draw_indexed_primitive == nullptr,
            "a managed format capability must not fabricate a draw consumer");

    // Installing packet capture remains optional and still wraps the adapter
    // callbacks without destroying the live managed-DXT3 capability.
    const auto capture_path =
        "unused-process2-live-managed-dxt3-regression-capture";
    shift::vulkan::D3d9PacketCaptureAdapter capture(capture_path);
    std::string error;
    require(capture.install(adapter, error),
            "optional packet capture installs over the live adapter");
    require(adapter.supports_dxt3_texture,
            "capture installation preserves managed DXT3 capability");
    require(adapter.backend_context != &runtime_context,
            "capture adapter retains its callback wrapping");
    require(adapter.draw_indexed_primitive != nullptr,
            "capture adapter continues to install the packet callback");

    std::cout << "live managed DXT3 capability check passed\n";
    return 0;
}
