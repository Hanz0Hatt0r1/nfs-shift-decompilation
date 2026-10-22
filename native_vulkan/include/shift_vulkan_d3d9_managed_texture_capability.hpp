#pragma once

#include "shift_recompiled_pcode_module.hpp"

namespace shift::vulkan {

// Retail D3D9 managed DXT3 (usage=0, D3DPOOL_MANAGED) is allocated and
// populated in guest CPU memory by the P-code module. Accepting that managed
// format does not require a Vulkan BC2 image or an installed capture adapter.
//
// This is *not* an assertion of live Vulkan BC2 upload/sampling or translated
// guest DrawIndexedPrimitive support. Those are independent renderer features.
inline void enable_guest_managed_dxt3_capability(
    runtime::RecompiledGuestD3d9AdapterInfo& adapter) noexcept {
    adapter.supports_dxt3_texture = true;
}

}  // namespace shift::vulkan
