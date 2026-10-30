#include "shift_xbox_live_vulkan_renderer.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <fstream>
#include <functional>
#include <initializer_list>
#include <limits>
#include <sstream>
#include <unordered_map>
#include <utility>

namespace shift::xbox {
namespace {

struct BufferResource {
    VkBuffer buffer = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    VkMemoryPropertyFlags memory_flags = 0;
    void* mapped = nullptr;
    VkDeviceSize buffer_size = 0;
    VkDeviceSize allocation_size = 0;
    VkBufferUsageFlags usage = 0;
    bool owns_resources = true;
};

struct ImageResource {
  VkImage image = VK_NULL_HANDLE;
  VkDeviceMemory memory = VK_NULL_HANDLE;
  VkImageView view = VK_NULL_HANDLE;
  VkDeviceSize allocation_size = 0;
  bool borrowed = false;
};

void destroy_image_resource(VkDevice device, ImageResource& resource) {
  if (resource.borrowed) {
    resource = {};
    return;
  }
  if (resource.view) vkDestroyImageView(device, resource.view, nullptr);
  if (resource.image) vkDestroyImage(device, resource.image, nullptr);
  if (resource.memory) vkFreeMemory(device, resource.memory, nullptr);
  resource = {};
}

struct CachedGraphicsPipeline;

struct DrawTextureResources {
  uint32_t fetch_constant_index = 0;
  uint32_t width = 0;
  uint32_t height = 0;
  BufferResource upload;
  ImageResource image;
  VkSampler sampler = VK_NULL_HANDLE;
  VkImageLayout upload_old_layout = VK_IMAGE_LAYOUT_UNDEFINED;
  bool cached = false;
  bool cached_sampler = false;
  bool guest_copy_source = false;
  bool external_image = false;
};

struct DrawResources {
  BufferResource vertices;
  BufferResource indices;
  BufferResource vertex_constants;
  BufferResource pixel_constants;
  std::vector<DrawTextureResources> textures;
  VkShaderModule vertex_shader = VK_NULL_HANDLE;
  VkShaderModule geometry_shader = VK_NULL_HANDLE;
  VkShaderModule pixel_shader = VK_NULL_HANDLE;
  VkDescriptorSetLayout descriptor_layouts[2]{};
  VkDescriptorPool descriptor_pool = VK_NULL_HANDLE;
  VkDescriptorSet descriptor_sets[2]{};
  VkPipelineLayout pipeline_layout = VK_NULL_HANDLE;
  VkPipeline pipeline = VK_NULL_HANDLE;
  CachedGraphicsPipeline *cached_pipeline_entry = nullptr;
  bool cached_descriptor_layouts = false;
};

struct TextureCacheKey {
  size_t draw_index = 0;
  uint32_t fetch_constant_index = 0;
  uint32_t width = 0;
  uint32_t height = 0;

  bool operator==(const TextureCacheKey &other) const {
    return draw_index == other.draw_index &&
           fetch_constant_index == other.fetch_constant_index &&
           width == other.width && height == other.height;
  }
};

struct TextureCacheKeyHash {
  size_t operator()(const TextureCacheKey &key) const {
    size_t hash = key.draw_index;
    hash = hash * 16777619u ^ key.fetch_constant_index;
    hash = hash * 16777619u ^ key.width;
    return hash * 16777619u ^ key.height;
  }
};

constexpr uint32_t kFramesInFlight = 2;

struct CachedDrawBuffers {
  std::array<BufferResource, kFramesInFlight> vertices;
  std::array<BufferResource, kFramesInFlight> indices;
  std::array<BufferResource, kFramesInFlight> vertex_constants;
  std::array<BufferResource, kFramesInFlight> pixel_constants;
  uint64_t last_used_frame = 0;
};

struct CachedR8Texture {
  std::array<BufferResource, kFramesInFlight> uploads;
  ImageResource image;
  uint64_t estimated_bytes = 0;
  uint64_t last_used_frame = 0;
  bool initialized = false;
};

struct GuestCopyImageKey {
  std::array<uint32_t, 14> values{};

  bool operator==(const GuestCopyImageKey& other) const noexcept {
    return values == other.values;
  }
};

struct GuestCopyImageKeyHash {
  size_t operator()(const GuestCopyImageKey& key) const noexcept {
    uint64_t hash = 14695981039346656037ull;
    for (uint32_t value : key.values) {
      hash ^= value;
      hash *= 1099511628211ull;
    }
    return static_cast<size_t>(hash);
  }
};

GuestCopyImageKey make_guest_copy_image_key(const CapturedCopyState& state) {
  return {{{state.destination_base,
            state.destination_pitch,
            state.destination_height,
            state.destination_format,
            state.destination_number_format,
            static_cast<uint32_t>(state.destination_exp_bias),
            state.destination_endian,
            state.sample_select,
            state.destination_swap_red_blue,
            state.destination_array,
            state.destination_slice,
            state.source_select,
            static_cast<uint32_t>(state.command),
            state.source_gamma}}};
}

struct CachedGuestCopyImage {
  ImageResource image;
  VkImageView sampled_view = VK_NULL_HANDLE;
  uint64_t estimated_bytes = 0;
  uint64_t last_used_frame = 0;
  bool initialized = false;
};

void destroy_cached_guest_copy_image(VkDevice device,
                                     CachedGuestCopyImage& resource) {
  if (resource.sampled_view) {
    vkDestroyImageView(device, resource.sampled_view, nullptr);
  }
  destroy_image_resource(device, resource.image);
  resource = {};
}

struct EdramTargetKey {
  std::array<uint32_t, 10> values{};

  bool operator==(const EdramTargetKey& other) const noexcept {
    return values == other.values;
  }
};

struct EdramTargetKeyHash {
  size_t operator()(const EdramTargetKey& key) const noexcept {
    uint64_t hash = 14695981039346656037ull;
    for (uint32_t value : key.values) {
      hash ^= value;
      hash *= 1099511628211ull;
    }
    return static_cast<size_t>(hash);
  }
};

// Guest render-target codes 3 (k_2_10_10_10_FLOAT) and 12
// (k_2_10_10_10_FLOAT_AS_16_16_16_16) describe one stored surface; they differ
// only in blending precision, and xenos.h::GetStorageColorFormat maps 12 to 3.
// Neither is 64bpp, so EDRAM tile addressing is identical. The cache key must
// use the storage format, or the same surface is cached twice under two keys
// and a lookup can miss a target that exists.
uint32_t edram_storage_guest_color_format(uint32_t guest_color_format) {
  return guest_color_format == 12u ? 3u : guest_color_format;
}

// Rounds a captured target extent up to whole EDRAM tiles (80x16 samples per
// tile). The hardware surface is tile-granular, so a 320x243 draw and a
// 320x248 resolve over the same rows are the same 4x16-tile surface. Using the
// rounded extent for both the cache key and the allocated image makes those two
// descriptions share one target instead of missing each other, and keeps the
// image large enough for either caller.
CapturedRasterState edram_tile_granular_layout(const CapturedRasterState& raster) {
  CapturedEdramTileFootprint footprint{};
  if (!captured_xenos_edram_tile_footprint(raster, false, &footprint, nullptr)) {
    return raster;
  }
  constexpr uint32_t kTileWidthSamples = 80;
  constexpr uint32_t kTileHeightSamples = 16;
  const uint32_t sample_width = raster.sample_count == 4 ? 2u : 1u;
  CapturedRasterState rounded = raster;
  // The physical extent is expressed in samples along both axes, matching how
  // the layout was decoded, so restore the sample factor after rounding.
  rounded.width = footprint.pitch_tiles * kTileWidthSamples;
  rounded.height = footprint.tile_rows * kTileHeightSamples;
  (void)sample_width;
  return rounded;
}

EdramTargetKey make_edram_target_key(const CapturedRasterState& raster,
                                    VkFormat color_format) {
  const CapturedRasterState granular = edram_tile_granular_layout(raster);
  return {{{raster.color_base_tiles,
            raster.depth_base_tiles,
            granular.width,
            granular.height,
            raster.surface_pitch,
            edram_storage_guest_color_format(raster.guest_color_format),
            static_cast<uint32_t>(color_format),
            raster.sample_count,
            static_cast<uint32_t>(raster.depth_format),
            raster.depth_only}}};
}

struct CachedEdramTarget {
  ImageResource color;
  ImageResource depth;
  uint64_t estimated_bytes = 0;
  uint64_t last_used_frame = 0;
  uint64_t last_depth_used_frame = 0;
  bool color_initialized = false;
  bool depth_initialized = false;
};

constexpr uint64_t kR8TextureCacheBudgetBytes = 16u * 1024u * 1024u;
constexpr uint64_t kR8TextureCacheLifetimeFrames = 120;
constexpr uint64_t kGuestCopyImageCacheBudgetBytes = 32u * 1024u * 1024u;
constexpr uint64_t kGuestCopyImageCacheLifetimeFrames = 120;
constexpr uint64_t kEdramTargetCacheBudgetBytes = 192u * 1024u * 1024u;
constexpr uint64_t kEdramTargetCacheLifetimeFrames = 120;
constexpr uint64_t kDrawBufferCacheBudgetBytes = 16u * 1024u * 1024u;
constexpr size_t kDrawBufferCacheEntryLimit = 128;
constexpr size_t kGraphicsPipelineCacheEntryLimit = 128;
constexpr size_t kSamplerCacheEntryLimit = 64;
constexpr size_t kDescriptorLayoutCacheEntryLimit = 128;

struct SamplerCacheKey {
  std::array<uint32_t, 9> values{};

  bool operator==(const SamplerCacheKey& other) const {
    return values == other.values;
  }
};

struct SamplerCacheKeyHash {
  size_t operator()(const SamplerCacheKey& key) const noexcept {
    size_t hash = 2166136261u;
    for (uint32_t value : key.values) hash = hash * 16777619u ^ value;
    return hash;
  }
};

SamplerCacheKey make_sampler_cache_key(const VkSamplerCreateInfo& info) {
  SamplerCacheKey key{};
  std::memcpy(&key.values[7], &info.maxAnisotropy, sizeof(info.maxAnisotropy));
  key.values[0] = static_cast<uint32_t>(info.magFilter);
  key.values[1] = static_cast<uint32_t>(info.minFilter);
  key.values[2] = static_cast<uint32_t>(info.mipmapMode);
  key.values[3] = static_cast<uint32_t>(info.addressModeU);
  key.values[4] = static_cast<uint32_t>(info.addressModeV);
  key.values[5] = static_cast<uint32_t>(info.addressModeW);
  key.values[6] = info.anisotropyEnable;
  key.values[8] = static_cast<uint32_t>(info.borderColor);
  return key;
}

struct CachedGraphicsPipeline {
  VkPipeline pipeline = VK_NULL_HANDLE;
  uint64_t last_used_frame = 0;
};

using GraphicsPipelineKey = std::vector<uint64_t>;

using DescriptorLayoutKey = std::vector<uint32_t>;

struct DescriptorLayoutKeyHash {
  size_t operator()(const DescriptorLayoutKey& key) const noexcept {
    uint64_t hash = 14695981039346656037ull;
    for (uint32_t binding : key) {
      hash ^= binding;
      hash *= 1099511628211ull;
    }
    return static_cast<size_t>(hash);
  }
};

struct CachedDescriptorLayouts {
  VkDescriptorSetLayout constants = VK_NULL_HANDLE;
  VkDescriptorSetLayout textures = VK_NULL_HANDLE;
  VkPipelineLayout pipeline = VK_NULL_HANDLE;
};

struct GraphicsPipelineKeyHash {
  size_t operator()(const GraphicsPipelineKey &key) const noexcept {
    uint64_t hash = 14695981039346656037ull;
    for (uint64_t value : key) {
      hash ^= value;
      hash *= 1099511628211ull;
    }
    return static_cast<size_t>(hash);
  }
};

struct FrameResources {
  VkDevice device = VK_NULL_HANDLE;
  VkQueue queue = VK_NULL_HANDLE;
  VkRenderPass render_pass = VK_NULL_HANDLE;
  VkFramebuffer framebuffer = VK_NULL_HANDLE;
  VkRenderPass edram_clear_render_pass = VK_NULL_HANDLE;
  VkFramebuffer edram_clear_framebuffer = VK_NULL_HANDLE;
  VkRenderPass copy_render_pass = VK_NULL_HANDLE;
  VkFramebuffer copy_framebuffer = VK_NULL_HANDLE;
  ImageResource multisample_color;
  ImageResource depth;
  VkRenderPass mixed_msaa_render_pass = VK_NULL_HANDLE;
  VkFramebuffer mixed_msaa_framebuffer = VK_NULL_HANDLE;
  VkRenderPass mixed_single_render_pass = VK_NULL_HANDLE;
  VkFramebuffer mixed_single_framebuffer = VK_NULL_HANDLE;
  VkRenderPass mixed_copy_render_pass = VK_NULL_HANDLE;
  VkFramebuffer mixed_copy_framebuffer = VK_NULL_HANDLE;
  ImageResource mixed_color;
  ImageResource mixed_msaa_color;
  ImageResource mixed_msaa_depth;
  ImageResource mixed_single_depth;
  BufferResource output_readback;
  ImageResource source_resolve;
  BufferResource source_readback;
  VkDeviceSize source_readback_size = 0;
  VkQueryPool draw_visibility_query_pool = VK_NULL_HANDLE;
  std::vector<uint32_t> draw_visibility_query_indices;
  VkCommandPool command_pool = VK_NULL_HANDLE;
  VkFence completion_fence = VK_NULL_HANDLE;
  uint32_t upload_slot = 0;
  std::vector<DrawResources> draws;
  DrawResources copy_draw;
  DrawResources edram_alias_draw;
  DrawResources edram_clear_draw;
  bool submitted = false;

  ~FrameResources() {
    if (submitted) {
      if (completion_fence) {
        vkWaitForFences(device, 1, &completion_fence, VK_TRUE, UINT64_MAX);
      } else if (queue) {
        vkQueueWaitIdle(queue);
      }
    }
    if (draw_visibility_query_pool)
      vkDestroyQueryPool(device, draw_visibility_query_pool, nullptr);
    const auto destroy_draw = [this](DrawResources &draw) {
      if (draw.pipeline && !draw.cached_pipeline_entry) {
        vkDestroyPipeline(device, draw.pipeline, nullptr);
      }
      if (draw.pipeline_layout && !draw.cached_descriptor_layouts) {
        vkDestroyPipelineLayout(device, draw.pipeline_layout, nullptr);
      }
      if (draw.descriptor_pool)
        vkDestroyDescriptorPool(device, draw.descriptor_pool, nullptr);
      if (!draw.cached_descriptor_layouts) {
        for (VkDescriptorSetLayout layout : draw.descriptor_layouts) {
          if (layout)
            vkDestroyDescriptorSetLayout(device, layout, nullptr);
        }
      }
      if (draw.vertex_shader)
        vkDestroyShaderModule(device, draw.vertex_shader, nullptr);
      if (draw.geometry_shader)
        vkDestroyShaderModule(device, draw.geometry_shader, nullptr);
      if (draw.pixel_shader)
        vkDestroyShaderModule(device, draw.pixel_shader, nullptr);
      for (DrawTextureResources &texture : draw.textures) {
        if (texture.sampler && !texture.cached_sampler)
          vkDestroySampler(device, texture.sampler, nullptr);
        if (!texture.cached) {
          destroy_image(texture.image);
          destroy_buffer(texture.upload);
        }
      }
      destroy_buffer(draw.pixel_constants);
      destroy_buffer(draw.vertex_constants);
      destroy_buffer(draw.indices);
      destroy_buffer(draw.vertices);
    };
    destroy_draw(copy_draw);
    destroy_draw(edram_alias_draw);
    destroy_draw(edram_clear_draw);
    for (auto it = draws.rbegin(); it != draws.rend(); ++it)
      destroy_draw(*it);
    if (edram_clear_framebuffer)
      vkDestroyFramebuffer(device, edram_clear_framebuffer, nullptr);
    if (copy_framebuffer)
      vkDestroyFramebuffer(device, copy_framebuffer, nullptr);
    if (framebuffer)
      vkDestroyFramebuffer(device, framebuffer, nullptr);
    destroy_image(multisample_color);
    destroy_image(depth);
    if (mixed_msaa_framebuffer)
      vkDestroyFramebuffer(device, mixed_msaa_framebuffer, nullptr);
    if (mixed_single_framebuffer)
      vkDestroyFramebuffer(device, mixed_single_framebuffer, nullptr);
    if (mixed_copy_framebuffer)
      vkDestroyFramebuffer(device, mixed_copy_framebuffer, nullptr);
    destroy_image(mixed_color);
    destroy_image(mixed_msaa_color);
    destroy_image(mixed_msaa_depth);
    destroy_image(mixed_single_depth);
    destroy_buffer(output_readback);
    destroy_image(source_resolve);
    destroy_buffer(source_readback);
    if (copy_render_pass)
      vkDestroyRenderPass(device, copy_render_pass, nullptr);
    if (edram_clear_render_pass)
      vkDestroyRenderPass(device, edram_clear_render_pass, nullptr);
    if (render_pass)
      vkDestroyRenderPass(device, render_pass, nullptr);
    if (mixed_msaa_render_pass)
      vkDestroyRenderPass(device, mixed_msaa_render_pass, nullptr);
    if (mixed_single_render_pass)
      vkDestroyRenderPass(device, mixed_single_render_pass, nullptr);
    if (mixed_copy_render_pass)
      vkDestroyRenderPass(device, mixed_copy_render_pass, nullptr);
    if (command_pool)
      vkDestroyCommandPool(device, command_pool, nullptr);
    if (completion_fence)
      vkDestroyFence(device, completion_fence, nullptr);
  }

  void destroy_buffer(BufferResource &resource) const {
    if (!resource.owns_resources) {
      resource = {};
      return;
    }
    if (resource.mapped && resource.memory) {
      vkUnmapMemory(device, resource.memory);
    }
    if (resource.buffer)
      vkDestroyBuffer(device, resource.buffer, nullptr);
    if (resource.memory)
      vkFreeMemory(device, resource.memory, nullptr);
    resource = {};
  }

  void destroy_image(ImageResource &resource) const {
    destroy_image_resource(device, resource);
  }
};

struct TextureCacheState {
  VkDevice device = VK_NULL_HANDLE;
  uint64_t frame = 0;
  uint64_t estimated_bytes = 0;
  uint64_t draw_buffers_bytes = 0;
  uint32_t upload_slot = 0;
  std::unordered_map<size_t, CachedDrawBuffers> draw_buffers;
  std::unordered_map<TextureCacheKey, CachedR8Texture, TextureCacheKeyHash>
      textures;
  std::unordered_map<GuestCopyImageKey, CachedGuestCopyImage,
                     GuestCopyImageKeyHash> guest_copy_images;
  uint64_t guest_copy_image_bytes = 0;
  std::unordered_map<EdramTargetKey, CachedEdramTarget,
                     EdramTargetKeyHash> edram_targets;
  uint64_t edram_target_bytes = 0;
  std::unordered_map<GraphicsPipelineKey, CachedGraphicsPipeline,
                     GraphicsPipelineKeyHash>
      graphics_pipelines;
  std::unordered_map<DescriptorLayoutKey, CachedDescriptorLayouts,
                     DescriptorLayoutKeyHash>
      descriptor_layouts;
  std::unordered_map<SamplerCacheKey, VkSampler, SamplerCacheKeyHash> samplers;
  size_t descriptor_layout_cache_hits = 0;
  std::deque<std::unique_ptr<FrameResources>> in_flight;
  std::atomic<size_t> in_flight_frame_count{0};
};

bool fail(const char* message, std::string* error) {
    if (error) *error = message;
    return false;
}

bool fail(const std::string& message, std::string* error) {
    if (error) *error = message;
    return false;
}

bool validate_captured_operation_stream(
    const std::vector<CapturedVulkanOperation>& operations,
    size_t draw_count,
    std::string* error) {
    std::vector<bool> referenced_draws(draw_count, false);
    uint32_t previous_draw_index = 0;
    bool have_previous_draw = false;
    // Diagnostic escape hatch: a single prepared draw that the shader/raster
    // path cannot handle currently costs the entire frame, which hides every
    // otherwise-correct draw behind it. Opting in drops just that packet and
    // still presents the rest, so partially-correct frames become visible and
    // measurable. The default stays strict so correctness regressions are not
    // masked.
    bool tolerate_unresolved_draws = false;
    if (const char* raw = std::getenv("SHIFT_NATIVE_VULKAN_TOLERATE_UNRESOLVED_DRAWS");
        raw && *raw && std::strcmp(raw, "0") != 0) {
        tolerate_unresolved_draws = true;
    }
    for (const CapturedVulkanOperation& operation : operations) {
        if (operation.type == CapturedVulkanOperation::Type::UnresolvedDraw) {
            if (tolerate_unresolved_draws) continue;
            std::ostringstream message;
            message << "captured operation stream contains unresolved draw packet "
                    << operation.packet_index;
            return fail(message.str(), error);
        }
        if (operation.type == CapturedVulkanOperation::Type::UnresolvedCopy) {
            std::ostringstream message;
            message << "captured operation stream contains unresolved Copy/Convert packet "
                    << operation.packet_index;
            return fail(message.str(), error);
        }
        if (operation.type == CapturedVulkanOperation::Type::CopyConvert) {
            if (operation.source_width == 0 || operation.source_height == 0 ||
                operation.copy_state.destination_base == 0 ||
                operation.copy_state.destination_pitch == 0 ||
                operation.copy_state.destination_height == 0) {
                std::ostringstream message;
                message << "captured Copy/Convert packet " << operation.packet_index
                        << " has incomplete source or destination extent";
                return fail(message.str(), error);
            }
            const bool has_pixel_shader =
                !operation.copy.pixel_shader_spirv.empty() ||
                !operation.copy.single_sample_pixel_shader_spirv.empty() ||
                !operation.copy.gamma_pixel_shader_spirv.empty() ||
                !operation.copy.gamma_single_sample_pixel_shader_spirv.empty();
            if (!operation.copy_shaders_ready ||
                operation.copy.vertex_shader_spirv.empty() || !has_pixel_shader) {
                std::ostringstream message;
                message << "captured Copy/Convert packet " << operation.packet_index
                        << " has no prepared Vulkan shader payload";
                return fail(message.str(), error);
            }
            continue;
        }
        if (operation.draw_index >= draw_count) {
            std::ostringstream message;
            message << "captured operation stream references draw "
                    << operation.draw_index << " outside draw list of "
                    << draw_count;
            return fail(message.str(), error);
        }
        if (referenced_draws[operation.draw_index] ||
            (have_previous_draw && operation.draw_index <= previous_draw_index)) {
            std::ostringstream message;
            message << "captured operation stream has duplicate or reordered draw "
                    << operation.draw_index;
            return fail(message.str(), error);
        }
        referenced_draws[operation.draw_index] = true;
        previous_draw_index = operation.draw_index;
        have_previous_draw = true;
    }
    for (size_t draw_index = 0; draw_index < referenced_draws.size(); ++draw_index) {
        if (!referenced_draws[draw_index]) {
            std::ostringstream message;
            message << "captured operation stream omits draw " << draw_index;
            return fail(message.str(), error);
        }
    }
    uint32_t previous_packet_index = 0;
    bool have_previous_packet = false;
    for (const CapturedVulkanOperation& operation : operations) {
        if (operation.packet_index == std::numeric_limits<uint32_t>::max() ||
            (have_previous_packet && operation.packet_index <= previous_packet_index)) {
            return fail("captured operation stream has missing or reordered packet ordinal",
                        error);
        }
        previous_packet_index = operation.packet_index;
        have_previous_packet = true;
    }
    if (error) error->clear();
    return true;
}

void append_captured_operation_stream(
    std::string* error,
    const std::vector<CapturedVulkanOperation>* operations) {
    if (error && operations && !operations->empty()) {
        *error += "; ordered operations=" +
                  describe_captured_vulkan_operations(*operations);
    }
}

bool vk_fail(const char* operation, VkResult result, std::string* error) {
    if (error) {
        std::ostringstream stream;
        stream << operation << " failed with VkResult " << result;
        *error = stream.str();
    }
    return false;
}

uint32_t find_memory_type(
    const VkPhysicalDeviceMemoryProperties& properties,
    uint32_t type_bits,
    VkMemoryPropertyFlags required,
    VkMemoryPropertyFlags preferred) {
    uint32_t fallback = UINT32_MAX;
    for (uint32_t i = 0; i < properties.memoryTypeCount; ++i) {
        if ((type_bits & (1u << i)) == 0) continue;
        const VkMemoryPropertyFlags flags = properties.memoryTypes[i].propertyFlags;
        if ((flags & required) != required) continue;
        if ((flags & preferred) == preferred) return i;
        if (fallback == UINT32_MAX) fallback = i;
    }
    return fallback;
}

bool create_buffer(
    VkPhysicalDeviceMemoryProperties const& memory_properties,
    VkDevice device,
    VkDeviceSize size,
    VkBufferUsageFlags usage,
    const void* data,
    BufferResource* output,
    std::string* error) {
    VkBufferCreateInfo create_info{};
    create_info.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    create_info.size = size;
    create_info.usage = usage;
    create_info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    VkResult result = vkCreateBuffer(device, &create_info, nullptr, &output->buffer);
    if (result != VK_SUCCESS) return vk_fail("vkCreateBuffer", result, error);
    output->buffer_size = size;
    output->usage = usage;

    VkMemoryRequirements requirements{};
    vkGetBufferMemoryRequirements(device, output->buffer, &requirements);
    output->allocation_size = requirements.size;
    const uint32_t memory_type = find_memory_type(
        memory_properties, requirements.memoryTypeBits,
        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT,
        VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
    if (memory_type == UINT32_MAX) return fail("no host-visible Vulkan buffer memory type", error);

    VkMemoryAllocateInfo allocate_info{};
    allocate_info.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    allocate_info.allocationSize = requirements.size;
    allocate_info.memoryTypeIndex = memory_type;
    result = vkAllocateMemory(device, &allocate_info, nullptr, &output->memory);
    if (result != VK_SUCCESS) return vk_fail("vkAllocateMemory(buffer)", result, error);
    output->memory_flags = memory_properties.memoryTypes[memory_type].propertyFlags;
    result = vkBindBufferMemory(device, output->buffer, output->memory, 0);
    if (result != VK_SUCCESS) return vk_fail("vkBindBufferMemory", result, error);

    if (data) {
        void* mapped = nullptr;
        result = vkMapMemory(device, output->memory, 0, VK_WHOLE_SIZE, 0, &mapped);
        if (result != VK_SUCCESS) return vk_fail("vkMapMemory(buffer)", result, error);
        std::memcpy(mapped, data, static_cast<size_t>(size));
        if ((memory_properties.memoryTypes[memory_type].propertyFlags &
             VK_MEMORY_PROPERTY_HOST_COHERENT_BIT) == 0) {
            VkMappedMemoryRange range{};
            range.sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE;
            range.memory = output->memory;
            range.offset = 0;
            range.size = VK_WHOLE_SIZE;
            result = vkFlushMappedMemoryRanges(device, 1, &range);
            if (result != VK_SUCCESS) return vk_fail("vkFlushMappedMemoryRanges", result, error);
        }
        vkUnmapMemory(device, output->memory);
    }
    return true;
}

void destroy_cached_buffer(VkDevice device, BufferResource& buffer) {
    if (buffer.mapped && buffer.memory) vkUnmapMemory(device, buffer.memory);
    if (buffer.buffer) vkDestroyBuffer(device, buffer.buffer, nullptr);
    if (buffer.memory) vkFreeMemory(device, buffer.memory, nullptr);
    buffer = {};
}

void destroy_cached_draw_buffers(VkDevice device, CachedDrawBuffers& buffers,
                                 uint64_t* total_bytes) {
    for (auto* slots : {&buffers.vertices, &buffers.indices,
                        &buffers.vertex_constants, &buffers.pixel_constants}) {
        for (BufferResource& buffer : *slots) {
            if (total_bytes && buffer.allocation_size <= *total_bytes) {
                *total_bytes -= buffer.allocation_size;
            }
            destroy_cached_buffer(device, buffer);
        }
    }
    buffers = {};
}

bool upload_draw_buffer(
    const VkPhysicalDeviceMemoryProperties& memory_properties,
    VkDevice device, VkDeviceSize size, VkBufferUsageFlags usage,
    const void* data, TextureCacheState* cache,
    std::array<BufferResource, kFramesInFlight>* cached_slots,
    BufferResource* output, std::string* error) {
    if (!cache || !cached_slots) {
        return create_buffer(memory_properties, device, size, usage, data,
                             output, error);
    }

    BufferResource& buffer = (*cached_slots)[cache->upload_slot];
    if (buffer.buffer &&
        (buffer.buffer_size < size || buffer.usage != usage)) {
        if (buffer.allocation_size <= cache->draw_buffers_bytes) {
            cache->draw_buffers_bytes -= buffer.allocation_size;
        }
        destroy_cached_buffer(device, buffer);
    }
    if (!buffer.buffer) {
        if (cache->draw_buffers_bytes >= kDrawBufferCacheBudgetBytes ||
            size > kDrawBufferCacheBudgetBytes - cache->draw_buffers_bytes) {
            return create_buffer(memory_properties, device, size, usage, data,
                                 output, error);
        }
        BufferResource created{};
        if (!create_buffer(memory_properties, device, size, usage, nullptr,
                           &created, error)) {
            destroy_cached_buffer(device, created);
            return false;
        }
        if (cache->draw_buffers_bytes >= kDrawBufferCacheBudgetBytes ||
            created.allocation_size >
            kDrawBufferCacheBudgetBytes - cache->draw_buffers_bytes) {
            destroy_cached_buffer(device, created);
            return create_buffer(memory_properties, device, size, usage, data,
                                 output, error);
        }
        const VkResult result = vkMapMemory(
            device, created.memory, 0, VK_WHOLE_SIZE, 0, &created.mapped);
        if (result != VK_SUCCESS) {
            destroy_cached_buffer(device, created);
            return vk_fail("vkMapMemory(cached draw buffer)", result, error);
        }
        cache->draw_buffers_bytes += created.allocation_size;
        buffer = created;
    }

    std::memcpy(buffer.mapped, data, static_cast<size_t>(size));
    if ((buffer.memory_flags & VK_MEMORY_PROPERTY_HOST_COHERENT_BIT) == 0) {
        VkMappedMemoryRange range{};
        range.sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE;
        range.memory = buffer.memory;
        range.size = VK_WHOLE_SIZE;
        const VkResult result = vkFlushMappedMemoryRanges(device, 1, &range);
        if (result != VK_SUCCESS) {
            return vk_fail("vkFlushMappedMemoryRanges(cached draw buffer)",
                           result, error);
        }
    }
    *output = buffer;
    output->owns_resources = false;
    return true;
}

bool create_texture_image(
    VkPhysicalDeviceMemoryProperties const& memory_properties,
    VkDevice device,
    uint32_t width,
    uint32_t height,
    VkFormat format,
    ImageResource* output,
    std::string* error) {
    VkImageCreateInfo image_info{};
    image_info.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
    image_info.imageType = VK_IMAGE_TYPE_2D;
    // Xenos TextureSign::Gamma is applied after sampling in the guest shader.
    image_info.format = format;
    image_info.extent = {width, height, 1};
    image_info.mipLevels = 1;
    image_info.arrayLayers = 1;
    image_info.samples = VK_SAMPLE_COUNT_1_BIT;
    image_info.tiling = VK_IMAGE_TILING_OPTIMAL;
    image_info.usage = VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT;
    image_info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    image_info.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    VkResult result = vkCreateImage(device, &image_info, nullptr, &output->image);
    if (result != VK_SUCCESS) return vk_fail("vkCreateImage(texture)", result, error);

    VkMemoryRequirements requirements{};
    vkGetImageMemoryRequirements(device, output->image, &requirements);
    output->allocation_size = requirements.size;
    const uint32_t memory_type = find_memory_type(
        memory_properties, requirements.memoryTypeBits, 0, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    if (memory_type == UINT32_MAX) return fail("no compatible Vulkan texture memory type", error);
    VkMemoryAllocateInfo allocate_info{};
    allocate_info.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    allocate_info.allocationSize = requirements.size;
    allocate_info.memoryTypeIndex = memory_type;
    result = vkAllocateMemory(device, &allocate_info, nullptr, &output->memory);
    if (result != VK_SUCCESS) return vk_fail("vkAllocateMemory(texture)", result, error);
    result = vkBindImageMemory(device, output->image, output->memory, 0);
    if (result != VK_SUCCESS) return vk_fail("vkBindImageMemory(texture)", result, error);

    VkImageViewCreateInfo view_info{};
    view_info.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
    view_info.image = output->image;
    view_info.viewType = VK_IMAGE_VIEW_TYPE_2D;
    view_info.format = format;
    view_info.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    view_info.subresourceRange.levelCount = 1;
    view_info.subresourceRange.layerCount = 1;
    result = vkCreateImageView(device, &view_info, nullptr, &output->view);
    if (result != VK_SUCCESS) return vk_fail("vkCreateImageView(texture)", result, error);
    return true;
}

void destroy_cached_r8_texture(VkDevice device, CachedR8Texture& texture) {
    for (BufferResource& upload : texture.uploads) {
        if (upload.mapped && upload.memory) vkUnmapMemory(device, upload.memory);
        if (upload.buffer) vkDestroyBuffer(device, upload.buffer, nullptr);
        if (upload.memory) vkFreeMemory(device, upload.memory, nullptr);
    }
    if (texture.image.view) vkDestroyImageView(device, texture.image.view, nullptr);
    if (texture.image.image) vkDestroyImage(device, texture.image.image, nullptr);
    if (texture.image.memory) vkFreeMemory(device, texture.image.memory, nullptr);
    texture = {};
}

bool wait_for_frame(FrameResources& frame, std::string* error) {
    if (!frame.submitted) return true;
    if (!frame.completion_fence) {
        return fail("submitted Vulkan frame has no completion fence", error);
    }
    const VkResult result = vkWaitForFences(
        frame.device, 1, &frame.completion_fence, VK_TRUE, UINT64_MAX);
    if (result != VK_SUCCESS) return vk_fail("vkWaitForFences(frame resources)", result, error);
    frame.submitted = false;
    return true;
}

bool prepare_draw_visibility_queries(
    VkDevice device, size_t draw_count, FrameResources& resources,
    std::vector<CapturedVulkanDrawVisibility>* draw_visibility) {
    if (!draw_visibility) return false;
    draw_visibility->assign(draw_count, {});
    if (draw_count == 0 || draw_count > std::numeric_limits<uint32_t>::max()) {
        return false;
    }
    VkQueryPoolCreateInfo query_info{};
    query_info.sType = VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO;
    query_info.queryType = VK_QUERY_TYPE_OCCLUSION;
    query_info.queryCount = static_cast<uint32_t>(draw_count);
    if (vkCreateQueryPool(device, &query_info, nullptr,
                          &resources.draw_visibility_query_pool) != VK_SUCCESS) {
        return false;
    }
    return true;
}

template <typename RecordDraw>
void record_draw_with_visibility_query(FrameResources& resources,
                                       VkCommandBuffer command,
                                       uint32_t draw_index,
                                       RecordDraw&& record_draw) {
    if (!resources.draw_visibility_query_pool) {
        record_draw();
        return;
    }
    vkCmdBeginQuery(command, resources.draw_visibility_query_pool, draw_index, 0);
    record_draw();
    vkCmdEndQuery(command, resources.draw_visibility_query_pool, draw_index);
    resources.draw_visibility_query_indices.push_back(draw_index);
}

void collect_draw_visibility_queries(
    const FrameResources& resources,
    std::vector<CapturedVulkanDrawVisibility>* draw_visibility) {
    if (!draw_visibility || !resources.draw_visibility_query_pool) return;
    for (uint32_t draw_index : resources.draw_visibility_query_indices) {
        uint64_t result = 0;
        if (vkGetQueryPoolResults(resources.device,
                                  resources.draw_visibility_query_pool,
                                  draw_index, 1, sizeof(result), &result,
                                  sizeof(result), VK_QUERY_RESULT_64_BIT |
                                                     VK_QUERY_RESULT_WAIT_BIT) ==
            VK_SUCCESS) {
            (*draw_visibility)[draw_index] = {true, result != 0};
        }
    }
}

bool retire_reusable_frames(TextureCacheState* cache, uint32_t upload_slot,
                            std::string* error) {
    for (auto it = cache->in_flight.begin(); it != cache->in_flight.end();) {
        FrameResources& frame = **it;
        const VkResult status = vkGetFenceStatus(frame.device, frame.completion_fence);
        if (status == VK_SUCCESS) {
            frame.submitted = false;
            it = cache->in_flight.erase(it);
            cache->in_flight_frame_count.fetch_sub(1, std::memory_order_release);
        } else if (status == VK_NOT_READY && frame.upload_slot == upload_slot) {
            if (!wait_for_frame(frame, error)) return false;
            it = cache->in_flight.erase(it);
            cache->in_flight_frame_count.fetch_sub(1, std::memory_order_release);
        } else if (status == VK_NOT_READY) {
            ++it;
        } else {
            return vk_fail("vkGetFenceStatus(frame resources)", status, error);
        }
    }
    while (cache->in_flight.size() >= kFramesInFlight) {
        if (!wait_for_frame(*cache->in_flight.front(), error)) return false;
        cache->in_flight.pop_front();
        cache->in_flight_frame_count.fetch_sub(1, std::memory_order_release);
    }
    return true;
}

bool wait_for_all_frames(TextureCacheState* cache, std::string* error) {
    while (!cache->in_flight.empty()) {
        if (!wait_for_frame(*cache->in_flight.front(), error)) return false;
        cache->in_flight.pop_front();
        cache->in_flight_frame_count.fetch_sub(1, std::memory_order_release);
    }
    return true;
}

void destroy_cached_graphics_pipeline(VkDevice device,
                                     CachedGraphicsPipeline& pipeline) {
    if (pipeline.pipeline) vkDestroyPipeline(device, pipeline.pipeline, nullptr);
    pipeline = {};
}

bool graphics_pipeline_is_in_flight(const TextureCacheState& cache,
                                    const CachedGraphicsPipeline* pipeline) {
    for (const auto& frame : cache.in_flight) {
        for (const DrawResources& draw : frame->draws) {
            if (draw.cached_pipeline_entry == pipeline) return true;
        }
        if (frame->copy_draw.cached_pipeline_entry == pipeline) return true;
    }
    return false;
}

bool make_room_for_graphics_pipeline(TextureCacheState* cache) {
    if (cache->graphics_pipelines.size() < kGraphicsPipelineCacheEntryLimit) return true;
    auto victim = cache->graphics_pipelines.end();
    for (auto it = cache->graphics_pipelines.begin();
         it != cache->graphics_pipelines.end(); ++it) {
        if (graphics_pipeline_is_in_flight(*cache, &it->second)) continue;
        if (victim == cache->graphics_pipelines.end() ||
            it->second.last_used_frame < victim->second.last_used_frame) {
            victim = it;
        }
    }
    if (victim == cache->graphics_pipelines.end()) return false;
    destroy_cached_graphics_pipeline(cache->device, victim->second);
    cache->graphics_pipelines.erase(victim);
    return true;
}

bool begin_texture_cache_frame(TextureCacheState* cache, VkDevice device,
                               std::string* error) {
    if (!cache) return true;
  if (cache->device && cache->device != device &&
        (!cache->draw_buffers.empty() || !cache->textures.empty() ||
         !cache->guest_copy_images.empty() ||
         !cache->edram_targets.empty() ||
         !cache->graphics_pipelines.empty() ||
         !cache->descriptor_layouts.empty() ||
         !cache->samplers.empty() || !cache->in_flight.empty())) {
        return fail("captured Vulkan resource cache cannot be shared across devices", error);
    }
    cache->device = device;
    ++cache->frame;
    if (cache->frame == 0) ++cache->frame;
    cache->upload_slot = static_cast<uint32_t>((cache->frame - 1u) % kFramesInFlight);
    if (!retire_reusable_frames(cache, cache->upload_slot, error)) return false;
    const bool evicting = std::any_of(
        cache->textures.begin(), cache->textures.end(), [&](const auto& entry) {
            return cache->frame - entry.second.last_used_frame >
                   kR8TextureCacheLifetimeFrames;
        });
    const bool evicting_draw_buffers = std::any_of(
        cache->draw_buffers.begin(), cache->draw_buffers.end(),
        [&](const auto& entry) {
            return cache->frame - entry.second.last_used_frame >
                   kR8TextureCacheLifetimeFrames;
        });
    const bool evicting_guest_copy_images = std::any_of(
        cache->guest_copy_images.begin(), cache->guest_copy_images.end(),
        [&](const auto& entry) {
            return cache->frame - entry.second.last_used_frame >
                   kGuestCopyImageCacheLifetimeFrames;
        });
    const bool evicting_edram_targets = std::any_of(
        cache->edram_targets.begin(), cache->edram_targets.end(),
        [&](const auto& entry) {
            return cache->frame - entry.second.last_used_frame >
                   kEdramTargetCacheLifetimeFrames;
        });
    if ((evicting || evicting_draw_buffers || evicting_guest_copy_images ||
         evicting_edram_targets) &&
        !wait_for_all_frames(cache, error)) {
        return false;
    }
    for (auto it = cache->textures.begin(); it != cache->textures.end();) {
        if (cache->frame - it->second.last_used_frame > kR8TextureCacheLifetimeFrames) {
            cache->estimated_bytes -= it->second.estimated_bytes;
            destroy_cached_r8_texture(device, it->second);
            it = cache->textures.erase(it);
        } else {
            ++it;
        }
    }
    for (auto it = cache->draw_buffers.begin();
         it != cache->draw_buffers.end();) {
        if (cache->frame - it->second.last_used_frame >
            kR8TextureCacheLifetimeFrames) {
            destroy_cached_draw_buffers(device, it->second,
                                        &cache->draw_buffers_bytes);
            it = cache->draw_buffers.erase(it);
        } else {
            ++it;
        }
    }
    for (auto it = cache->guest_copy_images.begin();
         it != cache->guest_copy_images.end();) {
        if (cache->frame - it->second.last_used_frame >
            kGuestCopyImageCacheLifetimeFrames) {
            cache->guest_copy_image_bytes -= it->second.estimated_bytes;
            destroy_cached_guest_copy_image(device, it->second);
            it = cache->guest_copy_images.erase(it);
        } else {
            ++it;
        }
    }
    for (auto it = cache->edram_targets.begin();
         it != cache->edram_targets.end();) {
        if (cache->frame - it->second.last_used_frame >
            kEdramTargetCacheLifetimeFrames) {
            cache->edram_target_bytes -= it->second.estimated_bytes;
            destroy_image_resource(device, it->second.depth);
            destroy_image_resource(device, it->second.color);
            it = cache->edram_targets.erase(it);
        } else {
            ++it;
        }
    }
    return true;
}

bool acquire_cached_r8_texture(
    TextureCacheState* cache,
    const VkPhysicalDeviceMemoryProperties& memory_properties,
    VkDevice device,
    size_t draw_index,
    uint32_t fetch_constant_index,
    uint32_t width,
    uint32_t height,
    const std::vector<uint8_t>& pixels,
    DrawTextureResources* output,
    bool* cached,
    std::string* error) {
    if (!cache || !output || !cached) return fail("invalid R8 texture cache request", error);
    *cached = false;
    const TextureCacheKey key{draw_index, fetch_constant_index, width, height};
    auto found = cache->textures.find(key);
    if (found == cache->textures.end()) {
        const uint64_t minimum_allocation =
            static_cast<uint64_t>(pixels.size()) * (1u + kFramesInFlight);
        if (minimum_allocation > kR8TextureCacheBudgetBytes - cache->estimated_bytes) {
            return true;
        }
        CachedR8Texture created{};
        for (BufferResource& upload : created.uploads) {
            if (!create_buffer(memory_properties, device, pixels.size(),
                               VK_BUFFER_USAGE_TRANSFER_SRC_BIT, nullptr,
                               &upload, error)) {
                destroy_cached_r8_texture(device, created);
                return false;
            }
        }
        if (!create_texture_image(memory_properties, device, width, height,
                                  VK_FORMAT_R8_UNORM, &created.image, error)) {
            destroy_cached_r8_texture(device, created);
            return false;
        }
        created.estimated_bytes = created.image.allocation_size;
        for (const BufferResource& upload : created.uploads) {
            created.estimated_bytes += upload.allocation_size;
        }
        if (created.estimated_bytes >
            kR8TextureCacheBudgetBytes - cache->estimated_bytes) {
            destroy_cached_r8_texture(device, created);
            return true;
        }
        for (BufferResource& upload : created.uploads) {
            const VkResult result = vkMapMemory(
                device, upload.memory, 0, VK_WHOLE_SIZE, 0, &upload.mapped);
            if (result != VK_SUCCESS) {
                destroy_cached_r8_texture(device, created);
                return vk_fail("vkMapMemory(cached R8 upload)", result, error);
            }
        }
        found = cache->textures.emplace(key, std::move(created)).first;
        cache->estimated_bytes += found->second.estimated_bytes;
    }

    CachedR8Texture& texture = found->second;
    BufferResource& upload = texture.uploads[cache->upload_slot];
    std::memcpy(upload.mapped, pixels.data(), pixels.size());
    if ((upload.memory_flags & VK_MEMORY_PROPERTY_HOST_COHERENT_BIT) == 0) {
        VkMappedMemoryRange range{};
        range.sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE;
        range.memory = upload.memory;
        range.size = VK_WHOLE_SIZE;
        const VkResult result = vkFlushMappedMemoryRanges(device, 1, &range);
        if (result != VK_SUCCESS) return vk_fail("vkFlushMappedMemoryRanges(cached R8)",
                                                 result, error);
    }
    texture.last_used_frame = cache->frame;
    output->upload = upload;
    output->image = texture.image;
    output->upload_old_layout = texture.initialized
        ? VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL
        : VK_IMAGE_LAYOUT_UNDEFINED;
    output->cached = true;
    *cached = true;
    return true;
}

void finish_texture_cache_frame(TextureCacheState* cache) {
    if (!cache) return;
    for (auto& [key, texture] : cache->textures) {
        if (texture.last_used_frame == cache->frame) texture.initialized = true;
    }
    for (auto& [key, image] : cache->guest_copy_images) {
        if (image.last_used_frame == cache->frame) image.initialized = true;
    }
    for (auto& [key, target] : cache->edram_targets) {
        if (target.last_used_frame == cache->frame) {
            target.color_initialized = true;
        }
        if (target.last_depth_used_frame == cache->frame) {
            target.depth_initialized = true;
        }
    }
}

void clear_texture_cache(TextureCacheState* cache) {
    if (!cache) return;
    wait_for_all_frames(cache, nullptr);
    for (auto& [key, pipeline] : cache->graphics_pipelines) {
        destroy_cached_graphics_pipeline(cache->device, pipeline);
    }
    cache->graphics_pipelines.clear();
    for (auto& [key, layouts] : cache->descriptor_layouts) {
        if (layouts.pipeline)
            vkDestroyPipelineLayout(cache->device, layouts.pipeline, nullptr);
        if (layouts.textures)
            vkDestroyDescriptorSetLayout(cache->device, layouts.textures, nullptr);
        if (layouts.constants)
            vkDestroyDescriptorSetLayout(cache->device, layouts.constants, nullptr);
    }
    cache->descriptor_layouts.clear();
    cache->descriptor_layout_cache_hits = 0;
    for (auto& [key, sampler] : cache->samplers) {
        if (sampler) vkDestroySampler(cache->device, sampler, nullptr);
    }
    cache->samplers.clear();
    for (auto& [key, texture] : cache->textures) {
        destroy_cached_r8_texture(cache->device, texture);
    }
    cache->textures.clear();
    for (auto& [key, image] : cache->guest_copy_images) {
        destroy_cached_guest_copy_image(cache->device, image);
    }
    cache->guest_copy_images.clear();
    cache->guest_copy_image_bytes = 0;
    for (auto& [key, target] : cache->edram_targets) {
        destroy_image_resource(cache->device, target.depth);
        destroy_image_resource(cache->device, target.color);
    }
    cache->edram_targets.clear();
    cache->edram_target_bytes = 0;
    for (auto& [draw_index, buffers] : cache->draw_buffers) {
        destroy_cached_draw_buffers(cache->device, buffers,
                                    &cache->draw_buffers_bytes);
    }
    cache->draw_buffers.clear();
    cache->draw_buffers_bytes = 0;
    cache->estimated_bytes = 0;
    cache->device = VK_NULL_HANDLE;
    cache->frame = 0;
    cache->upload_slot = 0;
}

bool create_render_attachment(
    const VkPhysicalDeviceMemoryProperties& memory_properties,
    VkDevice device,
    uint32_t width,
    uint32_t height,
    VkFormat format,
    VkImageUsageFlags usage,
    VkImageAspectFlags aspect,
    VkSampleCountFlagBits samples,
    ImageResource* output,
    std::string* error,
    VkImageCreateFlags flags = 0) {
    VkImageCreateInfo image_info{};
    image_info.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
    image_info.flags = flags;
    image_info.imageType = VK_IMAGE_TYPE_2D;
    image_info.format = format;
    image_info.extent = {width, height, 1};
    image_info.mipLevels = 1;
    image_info.arrayLayers = 1;
    image_info.samples = samples;
    image_info.tiling = VK_IMAGE_TILING_OPTIMAL;
    image_info.usage = usage;
    image_info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    image_info.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    VkResult result = vkCreateImage(device, &image_info, nullptr, &output->image);
    if (result != VK_SUCCESS) return vk_fail("vkCreateImage(render attachment)", result, error);

    VkMemoryRequirements requirements{};
    vkGetImageMemoryRequirements(device, output->image, &requirements);
    output->allocation_size = requirements.size;
    const uint32_t memory_type = find_memory_type(
        memory_properties, requirements.memoryTypeBits, 0,
        VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    if (memory_type == UINT32_MAX) {
        return fail("no compatible Vulkan render attachment memory type", error);
    }
    VkMemoryAllocateInfo allocate_info{};
    allocate_info.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    allocate_info.allocationSize = requirements.size;
    allocate_info.memoryTypeIndex = memory_type;
    result = vkAllocateMemory(device, &allocate_info, nullptr, &output->memory);
    if (result != VK_SUCCESS) return vk_fail("vkAllocateMemory(render attachment)", result, error);
    result = vkBindImageMemory(device, output->image, output->memory, 0);
    if (result != VK_SUCCESS) return vk_fail("vkBindImageMemory(render attachment)", result, error);

    VkImageViewCreateInfo view_info{};
    view_info.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
    view_info.image = output->image;
    view_info.viewType = VK_IMAGE_VIEW_TYPE_2D;
    view_info.format = format;
    view_info.subresourceRange.aspectMask = aspect;
    view_info.subresourceRange.levelCount = 1;
    view_info.subresourceRange.layerCount = 1;
    result = vkCreateImageView(device, &view_info, nullptr, &output->view);
    if (result != VK_SUCCESS) return vk_fail("vkCreateImageView(render attachment)", result, error);
    return true;
}

VkSamplerAddressMode sampler_address_mode(TextureClamp clamp, bool* supported) {
    switch (clamp) {
        case TextureClamp::Repeat: return VK_SAMPLER_ADDRESS_MODE_REPEAT;
        case TextureClamp::MirroredRepeat: return VK_SAMPLER_ADDRESS_MODE_MIRRORED_REPEAT;
        case TextureClamp::ClampToEdge: return VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
        case TextureClamp::ClampToBorder: return VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_BORDER;
        default:
            *supported = false;
            return VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    }
}

VkFilter sampler_filter(TextureFilter filter, bool* supported) {
    if (filter == TextureFilter::Linear || filter == TextureFilter::BaseMap) {
        return VK_FILTER_LINEAR;
    }
    if (filter == TextureFilter::Point) return VK_FILTER_NEAREST;
    *supported = false;
    return VK_FILTER_NEAREST;
}

VkCompareOp compare_op(uint32_t value) {
    static constexpr VkCompareOp kCompareOps[] = {
        VK_COMPARE_OP_NEVER, VK_COMPARE_OP_LESS, VK_COMPARE_OP_EQUAL,
        VK_COMPARE_OP_LESS_OR_EQUAL, VK_COMPARE_OP_GREATER,
        VK_COMPARE_OP_NOT_EQUAL, VK_COMPARE_OP_GREATER_OR_EQUAL,
        VK_COMPARE_OP_ALWAYS,
    };
    return kCompareOps[value & 7u];
}

bool captured_depth_test_is_noop(const CapturedRasterState& raster) {
    return raster.depth_test_enabled && !raster.depth_write_enabled &&
           !raster.stencil_test_enabled &&
           ((raster.depth_control >> 4) & 7u) == 7u;
}

bool captured_depth_stencil_attachment_used(
    const CapturedRasterState& raster) {
    return raster.depth_write_enabled || raster.stencil_test_enabled ||
           (raster.depth_test_enabled &&
            !captured_depth_test_is_noop(raster));
}

VkStencilOp stencil_op(uint32_t value) {
    static constexpr VkStencilOp kStencilOps[] = {
        VK_STENCIL_OP_KEEP, VK_STENCIL_OP_ZERO, VK_STENCIL_OP_REPLACE,
        VK_STENCIL_OP_INCREMENT_AND_CLAMP, VK_STENCIL_OP_DECREMENT_AND_CLAMP,
        VK_STENCIL_OP_INVERT, VK_STENCIL_OP_INCREMENT_AND_WRAP,
        VK_STENCIL_OP_DECREMENT_AND_WRAP,
    };
    return kStencilOps[value & 7u];
}

VkSampleCountFlagBits sample_count_flag(uint32_t samples) {
    switch (samples) {
        case 1: return VK_SAMPLE_COUNT_1_BIT;
        case 2: return VK_SAMPLE_COUNT_2_BIT;
        case 4: return VK_SAMPLE_COUNT_4_BIT;
        default: return VkSampleCountFlagBits{};
    }
}

// Diagnostics are opt-in and file-based because this translation unit has no
// logging facility. Kept intentionally tiny and only on the EDRAM cache paths
// that matter for source-target lifetime questions.
bool edram_trace_enabled() {
  static const bool enabled = [] {
    const char* raw = std::getenv("SHIFT_NATIVE_VULKAN_TRACE_EDRAM");
    return raw && *raw && std::strcmp(raw, "0") != 0;
  }();
  return enabled;
}

void edram_trace(const std::string& line) {
  if (!edram_trace_enabled()) return;
  const char* path = std::getenv("SHIFT_NATIVE_VULKAN_TRACE_EDRAM");
  std::ofstream file(path, std::ios::app);
  if (file) file << line << '\n';
}

bool acquire_edram_target(
    TextureCacheState* cache,
    const VkPhysicalDeviceMemoryProperties& memory_properties,
    VkDevice device,
    const CapturedRasterState& raster,
    VkFormat color_format,
    bool needs_depth,
    CachedEdramTarget** output,
    std::string* error) {
  if (!cache || !output || !raster.width || !raster.height ||
      color_format == VK_FORMAT_UNDEFINED) {
    return fail("invalid persistent Xenos EDRAM target request", error);
  }
  const VkSampleCountFlagBits samples = sample_count_flag(raster.sample_count);
  if (samples == VkSampleCountFlagBits{}) {
    return fail("persistent Xenos EDRAM target uses an unsupported sample count",
                error);
  }

  // The key is tile-granular, so the backing image must be allocated at the
  // same rounded extent: otherwise a caller whose extent is slightly larger
  // than the first claimant's would key to this entry and then render outside
  // the image. Rendering stays per-caller because every pass uses its own
  // raster.width/height for the viewport and scissor.
  const CapturedRasterState granular = edram_tile_granular_layout(raster);
  const EdramTargetKey key = make_edram_target_key(raster, color_format);
  auto found = cache->edram_targets.find(key);
  if (found == cache->edram_targets.end()) {
    CachedEdramTarget created{};
    constexpr VkImageUsageFlags color_usage =
        VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_SAMPLED_BIT |
        VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
    if (!create_render_attachment(
            memory_properties, device, granular.width, granular.height,
            color_format, color_usage, VK_IMAGE_ASPECT_COLOR_BIT, samples,
            &created.color, error)) {
      destroy_image_resource(device, created.color);
      return false;
    }
    created.estimated_bytes = created.color.allocation_size;
    if (needs_depth) {
      if (!create_render_attachment(
              memory_properties, device, granular.width, granular.height,
              VK_FORMAT_D24_UNORM_S8_UINT,
              VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT,
              VK_IMAGE_ASPECT_DEPTH_BIT | VK_IMAGE_ASPECT_STENCIL_BIT,
              samples, &created.depth, error)) {
        destroy_image_resource(device, created.depth);
        destroy_image_resource(device, created.color);
        return false;
      }
      created.estimated_bytes += created.depth.allocation_size;
    }
    if (created.estimated_bytes > kEdramTargetCacheBudgetBytes ||
        cache->edram_target_bytes >
            kEdramTargetCacheBudgetBytes - created.estimated_bytes) {
      destroy_image_resource(device, created.depth);
      destroy_image_resource(device, created.color);
      std::ostringstream message;
      message << "persistent Xenos EDRAM target cache requires "
              << created.estimated_bytes << " bytes and exceeds its "
              << kEdramTargetCacheBudgetBytes << "-byte budget";
      return fail(message.str(), error);
    }
    found = cache->edram_targets.emplace(key, std::move(created)).first;
    cache->edram_target_bytes += found->second.estimated_bytes;
    {
      std::ostringstream trace;
      trace << "create frame=" << cache->frame << " base=0x" << std::hex
            << key.values[0] << " depth=0x" << key.values[1] << std::dec
            << " extent=" << key.values[2] << 'x' << key.values[3]
            << " pitch=" << key.values[4] << " gcf=" << key.values[5]
            << " cf=" << key.values[6] << " samples=" << key.values[7]
            << " depth_only=" << key.values[9] << " count="
            << cache->edram_targets.size();
      edram_trace(trace.str());
    }
  } else if (needs_depth && found->second.depth.image == VK_NULL_HANDLE) {
    ImageResource depth{};
    if (!create_render_attachment(
            memory_properties, device, granular.width, granular.height,
            VK_FORMAT_D24_UNORM_S8_UINT,
            VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT,
            VK_IMAGE_ASPECT_DEPTH_BIT | VK_IMAGE_ASPECT_STENCIL_BIT,
            samples, &depth, error)) {
      destroy_image_resource(device, depth);
      return false;
    }
    if (depth.allocation_size > kEdramTargetCacheBudgetBytes -
                                    cache->edram_target_bytes) {
      destroy_image_resource(device, depth);
      return fail("persistent Xenos EDRAM depth target exceeds its 192 MiB cache budget",
                  error);
    }
    found->second.estimated_bytes += depth.allocation_size;
    cache->edram_target_bytes += depth.allocation_size;
    found->second.depth = depth;
  }

  CachedEdramTarget& target = found->second;
  target.last_used_frame = cache->frame;
  if (needs_depth) target.last_depth_used_frame = cache->frame;
  *output = &target;
  return true;
}

bool frame_has_gamma_color_target(
    const std::vector<CapturedVulkanDraw>& draws) {
    return std::any_of(draws.begin(), draws.end(), [](const CapturedVulkanDraw& draw) {
        return draw.raster.color_format == CapturedColorTargetFormat::Rgba8Gamma;
    });
}

bool is_captured_gamma_depth_only_view_alias(
    const CapturedRasterState& first, const CapturedRasterState& second) {
    if (first.depth_only == second.depth_only) return false;
    const CapturedRasterState& color = first.depth_only ? second : first;
    const CapturedRasterState& depth = first.depth_only ? first : second;
    const bool captured_4x_layout = color.sample_count == 4 &&
        depth.sample_count == 4 && color.surface_pitch == depth.surface_pitch;
    const bool captured_1x_to_4x_layout = color.sample_count == 1 &&
        depth.sample_count == 4 && depth.surface_pitch <= UINT32_MAX / 2u &&
        color.surface_pitch == depth.surface_pitch * 2u;
    return color.color_write_mask != 0 && depth.color_write_mask == 0 &&
        (captured_4x_layout || captured_1x_to_4x_layout) &&
        color.color_base_tiles == depth.color_base_tiles &&
        color.depth_base_tiles == depth.depth_base_tiles &&
        color.width == depth.width && color.height == depth.height &&
        color.depth_format == depth.depth_format &&
        color.guest_color_format == 1 &&
        color.color_format == CapturedColorTargetFormat::Rgba8Gamma &&
        depth.guest_color_format == 0 &&
        depth.color_format == CapturedColorTargetFormat::Rgba8Linear;
}

bool is_captured_gamma_4x_to_1x_edram_alias(
    const CapturedRasterState& source,
    const CapturedRasterState& destination) {
    if (source.width != 1280 || source.height != 720 ||
        destination.width != source.width ||
        destination.height != source.height ||
        source.surface_pitch != 640 || destination.surface_pitch != 1280 ||
        source.sample_count != 4 || destination.sample_count != 1 ||
        source.color_base_tiles != destination.color_base_tiles ||
        source.depth_base_tiles != destination.depth_base_tiles ||
        source.guest_color_format != 1 ||
        destination.guest_color_format != 1 ||
        source.color_format != CapturedColorTargetFormat::Rgba8Gamma ||
        destination.color_format != CapturedColorTargetFormat::Rgba8Gamma ||
        source.depth_format != destination.depth_format ||
        source.depth_only || destination.depth_only) {
        return false;
    }
    for (bool depth_target : {false, true}) {
        std::vector<CapturedEdramTileAlias> aliases;
        if (!captured_xenos_edram_alias_tiles(
                source, destination, depth_target, &aliases, nullptr) ||
            aliases.size() != 720 ||
            !std::all_of(aliases.begin(), aliases.end(),
                         [](const CapturedEdramTileAlias& alias) {
                             return alias.source_tile_x ==
                                        alias.destination_tile_x &&
                                    alias.source_tile_y ==
                                        alias.destination_tile_y;
                         })) {
            return false;
        }
    }
    return true;
}

VkFormat captured_color_format(CapturedColorTargetFormat format,
                               bool linear_rgba8_intermediate) {
    switch (format) {
        case CapturedColorTargetFormat::Rgba8Linear:
        case CapturedColorTargetFormat::Rgba8Gamma:
            // RGBA8 linear and gamma draws can share one live EDRAM target.
            // When gamma occurs, keep both variants in the linear UNORM16
            // attachment so Vulkan can blend the gamma draw in linear light.
            return linear_rgba8_intermediate
                ? VK_FORMAT_R16G16B16A16_UNORM
                : (format == CapturedColorTargetFormat::Rgba8Gamma
                       ? VK_FORMAT_R16G16B16A16_UNORM
                       : VK_FORMAT_R8G8B8A8_UNORM);
        case CapturedColorTargetFormat::Rgb10A2Unorm:
            return VK_FORMAT_A2B10G10R10_UNORM_PACK32;
        case CapturedColorTargetFormat::Rgb10A2Float:
            return VK_FORMAT_R16G16B16A16_SFLOAT;
        case CapturedColorTargetFormat::Rg16Float:
            return VK_FORMAT_R16G16_SFLOAT;
    }
    return VK_FORMAT_UNDEFINED;
}

VkFormat captured_copy_destination_format(uint32_t format) {
    switch (format) {
        case 6: return VK_FORMAT_A2B10G10R10_UNORM_PACK32;
        case 26: return VK_FORMAT_R16G16B16A16_UINT;
        case 31: return VK_FORMAT_R16G16_SFLOAT;
        default: return VK_FORMAT_UNDEFINED;
    }
}

CachedEdramTarget* find_initialized_edram_target(
    TextureCacheState* cache,
    const CapturedRasterState& raster) {
  if (!cache) return nullptr;
  const VkFormat color_format = captured_color_format(raster.color_format, false);
  if (color_format == VK_FORMAT_UNDEFINED) return nullptr;
  const EdramTargetKey key = make_edram_target_key(raster, color_format);
  const auto found = cache->edram_targets.find(key);
  const bool present = found != cache->edram_targets.end();
  const bool initialized = present && found->second.color_initialized;
  const bool not_future = present && found->second.last_used_frame <= cache->frame;
  const bool fresh = present && not_future &&
      cache->frame + 1u - found->second.last_used_frame <=
          kEdramTargetCacheLifetimeFrames;
  if (!present || !initialized || !not_future || !fresh) {
    if (edram_trace_enabled()) {
      std::ostringstream trace;
      trace << "lookup-miss frame=" << cache->frame << " base=0x" << std::hex
            << key.values[0] << " depth=0x" << key.values[1] << std::dec
            << " extent=" << key.values[2] << 'x' << key.values[3]
            << " pitch=" << key.values[4] << " gcf=" << key.values[5]
            << " cf=" << key.values[6] << " samples=" << key.values[7]
            << " depth_only=" << key.values[9] << " present=" << present;
      if (present) {
        trace << " initialized=" << found->second.color_initialized
              << " last_used=" << found->second.last_used_frame;
      }
      trace << " cached=" << cache->edram_targets.size();
      edram_trace(trace.str());
    }
    return nullptr;
  }
  return &found->second;
}

bool acquire_guest_copy_image(
    TextureCacheState* cache,
    const VkPhysicalDeviceMemoryProperties& memory_properties,
    VkDevice device,
    const CapturedCopyState& state,
    uint32_t width,
    uint32_t height,
    VkFormat format,
    CachedGuestCopyImage** output,
    std::string* error) {
    if (!cache || !output || !width || !height ||
        state.destination_base == 0 || format == VK_FORMAT_UNDEFINED) {
        return fail("invalid guest Copy/Convert image cache request", error);
    }
    *output = nullptr;
    const GuestCopyImageKey key = make_guest_copy_image_key(state);
    auto found = cache->guest_copy_images.find(key);
    if (found == cache->guest_copy_images.end()) {
        CachedGuestCopyImage created{};
        if (!create_render_attachment(
                memory_properties, device, width, height, format,
                VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT |
                    VK_IMAGE_USAGE_SAMPLED_BIT |
                    VK_IMAGE_USAGE_TRANSFER_SRC_BIT,
                VK_IMAGE_ASPECT_COLOR_BIT, VK_SAMPLE_COUNT_1_BIT,
                &created.image, error,
                state.destination_format == 26u
                    ? VK_IMAGE_CREATE_MUTABLE_FORMAT_BIT : 0u)) {
            destroy_cached_guest_copy_image(device, created);
            return false;
        }
        if (state.destination_format == 26u) {
            VkImageViewCreateInfo view_info{};
            view_info.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
            view_info.image = created.image.image;
            view_info.viewType = VK_IMAGE_VIEW_TYPE_2D;
            view_info.format = VK_FORMAT_R16G16B16A16_UNORM;
            view_info.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            view_info.subresourceRange.levelCount = 1;
            view_info.subresourceRange.layerCount = 1;
            const VkResult view_result = vkCreateImageView(
                device, &view_info, nullptr, &created.sampled_view);
            if (view_result != VK_SUCCESS) {
                destroy_cached_guest_copy_image(device, created);
                return vk_fail("vkCreateImageView(format-26 texture)",
                               view_result, error);
            }
        }
        created.estimated_bytes = created.image.allocation_size;
        if (created.estimated_bytes > kGuestCopyImageCacheBudgetBytes ||
            cache->guest_copy_image_bytes >
                kGuestCopyImageCacheBudgetBytes - created.estimated_bytes) {
            destroy_cached_guest_copy_image(device, created);
            return fail("guest Copy/Convert image cache exceeded its 32 MiB budget",
                        error);
        }
        found = cache->guest_copy_images.emplace(key, std::move(created)).first;
        cache->guest_copy_image_bytes += found->second.estimated_bytes;
    }
    CachedGuestCopyImage& image = found->second;
    image.last_used_frame = cache->frame;
    *output = &image;
    return true;
}

CachedGuestCopyImage* find_guest_copy_texture(
    TextureCacheState* cache, const CapturedVulkanTexture& texture) {
  const bool format31 = texture.guest_format == 31u &&
      texture.guest_endian == 2u && !texture.guest_tiled &&
      !texture.guest_integer_format && !texture.guest_packed_mips &&
      texture.guest_pitch == texture.width;
  const bool format26 = texture.guest_format == 26u &&
      texture.guest_endian == 1u && texture.guest_tiled &&
      texture.guest_integer_format && !texture.guest_packed_mips &&
      texture.width == 1280u && texture.height == 720u &&
      texture.guest_pitch == 1280u;
  if (!cache || !texture.guest_copy_source || texture.guest_address == 0 ||
      (!format31 && !format26) || texture.width == 0 || texture.height == 0) {
    return nullptr;
  }
  for (auto& [key, image] : cache->guest_copy_images) {
    const auto& values = key.values;
    const bool format_key_matches = format31
        ? values[3] == 31u && values[4] == 7u &&
              static_cast<int32_t>(values[5]) == 0 && values[6] == 2u &&
              values[7] == 0u
        : values[3] == 26u && values[4] == 2u &&
              static_cast<int32_t>(values[5]) == 11 && values[6] == 1u &&
              values[7] == 6u && image.sampled_view != VK_NULL_HANDLE;
    if (image.initialized && values[0] == texture.guest_address &&
        values[1] == texture.guest_pitch && values[2] == texture.height &&
        format_key_matches &&
        values[8] == 0u && values[9] == 0u &&
        values[10] == 0u && values[11] == 0u && values[12] ==
            static_cast<uint32_t>(CapturedCopyCommand::Convert) &&
        values[13] == 0u) {
      image.last_used_frame = cache->frame;
      return &image;
    }
  }
  return nullptr;
}

uint32_t color_format_bytes(VkFormat format) {
    switch (format) {
        case VK_FORMAT_R8G8B8A8_UNORM:
        case VK_FORMAT_A2B10G10R10_UNORM_PACK32:
        case VK_FORMAT_R16G16_SFLOAT:
            return 4;
        case VK_FORMAT_R16G16B16A16_UINT:
        case VK_FORMAT_R16G16B16A16_UNORM:
        case VK_FORMAT_R16G16B16A16_SFLOAT:
            return 8;
        default:
            return 0;
    }
}

void source_readback_unsupported(CapturedVulkanSourceReadback* readback,
                                 std::string reason) {
    if (!readback) return;
    readback->status = CapturedVulkanSourceReadback::Status::Unsupported;
    readback->bytes.clear();
    readback->reason = std::move(reason);
}

bool prepare_source_readback_buffer(
    const VkPhysicalDeviceMemoryProperties& memory_properties,
    VkDevice device,
    uint32_t width,
    uint32_t height,
    VkFormat format,
    uint32_t sample_count,
    bool multisample_average_resolve,
    FrameResources& resources,
    CapturedVulkanSourceReadback* readback) {
    if (!readback) return false;
    readback->width = width;
    readback->height = height;
    readback->format = format;
    readback->sample_count = sample_count;
    readback->multisample_average_resolve = multisample_average_resolve;
    const uint32_t bytes_per_pixel = color_format_bytes(format);
    const uint64_t pixel_count = static_cast<uint64_t>(width) * height;
    if (!width || !height || !bytes_per_pixel ||
        pixel_count > std::numeric_limits<size_t>::max() / bytes_per_pixel ||
        pixel_count > std::numeric_limits<VkDeviceSize>::max() / bytes_per_pixel) {
        source_readback_unsupported(readback,
                                    "source extent or Vulkan format is not readable");
        return false;
    }
    resources.source_readback_size =
        static_cast<VkDeviceSize>(pixel_count * bytes_per_pixel);
    std::string resource_error;
    if (!create_buffer(memory_properties, device, resources.source_readback_size,
                       VK_BUFFER_USAGE_TRANSFER_DST_BIT, nullptr,
                       &resources.source_readback, &resource_error)) {
        source_readback_unsupported(readback,
                                    "source staging buffer unavailable: " + resource_error);
        return false;
    }
    readback->reason = "source image readback was not submitted";
    return true;
}

void set_copy_resolution_constants(CapturedVulkanDraw *draw,
                                   uint32_t source_width,
                                   uint32_t source_height,
                                   uint32_t destination_width,
                                   uint32_t destination_height) {
  if (!draw || !destination_width || !destination_height)
    return;
  const float scale[2] = {
      static_cast<float>(source_width) / destination_width,
      static_cast<float>(source_height) / destination_height,
  };
  std::memcpy(draw->constants.pixel_float_constants[0].data(), scale,
              sizeof(scale));
}

CapturedVulkanDraw make_copy_resolve_draw(
    const CapturedVulkanCopy& copy, uint32_t source_width,
    uint32_t source_height, uint32_t destination_width,
    uint32_t destination_height, bool single_sample_shader) {
  CapturedVulkanDraw copy_draw = copy.source_geometry_ready
      ? copy.source_geometry : CapturedVulkanDraw{};
  if (!copy.source_geometry_ready) {
    copy_draw.vertex_shader_spirv = copy.vertex_shader_spirv;
    copy_draw.auto_index = true;
    copy_draw.index_count = 3;
    copy_draw.raster.width = destination_width;
    copy_draw.raster.height = destination_height;
    copy_draw.raster.scissor_x1 = destination_width;
    copy_draw.raster.scissor_y1 = destination_height;
    copy_draw.raster.scissor_has_area = true;
  }
  copy_draw.pixel_shader_spirv = copy.source_gamma
      ? (single_sample_shader ? copy.gamma_single_sample_pixel_shader_spirv
                              : copy.gamma_pixel_shader_spirv)
      : (single_sample_shader ? copy.single_sample_pixel_shader_spirv
                              : copy.pixel_shader_spirv);
  copy_draw.pixel_shader_spirv_linear_target.clear();
  copy_draw.texture_width = 1;
  copy_draw.texture_height = 1;
  copy_draw.texture_rgba8 = {0, 0, 0, 255};
  copy_draw.raster.sample_count = 1;
  copy_draw.raster.color_write_mask = 0xFu;
  copy_draw.raster.depth_test_enabled = false;
  copy_draw.raster.depth_write_enabled = false;
  copy_draw.raster.stencil_test_enabled = false;
  copy_draw.raster.depth_control = 0;
  copy_draw.raster.blend_control_0 = 0x00010001u;
  set_copy_resolution_constants(&copy_draw, source_width, source_height,
                                destination_width, destination_height);
  copy_draw.texture_sampling.clamps = {TextureClamp::ClampToEdge,
                                       TextureClamp::ClampToEdge,
                                       TextureClamp::ClampToEdge};
  copy_draw.texture_sampling.mag_filter = TextureFilter::Point;
  copy_draw.texture_sampling.min_filter = TextureFilter::Point;
  copy_draw.texture_sampling.mip_filter = TextureFilter::Point;
  copy_draw.texture_sampling.anisotropy = TextureAnisotropy::Disabled;
  copy_draw.texture_sampling.border_color = TextureBorderColor::AbgrBlack;
  copy_draw.texture_sampling.border_alpha_known = true;
  return copy_draw;
}

void record_copy_resolve_draw(VkCommandBuffer command,
                              const DrawResources& draw_resources,
                              const CapturedVulkanCopy& copy,
                              uint32_t target_width,
                              uint32_t target_height) {
  const CapturedVulkanDraw* source = copy.source_geometry_ready
      ? &copy.source_geometry : nullptr;
  VkViewport viewport{};
  if (source && source->raster.clip_disabled_window_coordinates) {
    viewport.width = static_cast<float>(target_width);
    viewport.height = static_cast<float>(target_height);
  } else if (source && source->raster.viewport_width != 0.0f &&
             source->raster.viewport_height != 0.0f && source->raster.width &&
             source->raster.height) {
    const float scale_x = static_cast<float>(target_width) / source->raster.width;
    const float scale_y = static_cast<float>(target_height) / source->raster.height;
    viewport.x = source->raster.viewport_x * scale_x;
    viewport.y = source->raster.viewport_y * scale_y;
    viewport.width = source->raster.viewport_width * scale_x;
    viewport.height = source->raster.viewport_height * scale_y;
  } else {
    viewport.y = source && source->raster.viewport_y_flipped
        ? static_cast<float>(target_height) : 0.0f;
    viewport.width = static_cast<float>(target_width);
    viewport.height = source && source->raster.viewport_y_flipped
        ? -static_cast<float>(target_height) : static_cast<float>(target_height);
  }
  viewport.minDepth = 0.0f;
  viewport.maxDepth = 1.0f;

  const auto scaled_edge = [](uint32_t edge, uint32_t source_extent,
                              uint32_t target_extent, bool round_up) {
    if (source_extent == 0) return uint32_t{0};
    const uint64_t numerator = static_cast<uint64_t>(edge) * target_extent;
    const uint64_t quotient = numerator / source_extent;
    return static_cast<uint32_t>(quotient +
        (round_up && numerator % source_extent != 0 ? 1u : 0u));
  };
  const uint32_t x0 = source
      ? scaled_edge(source->raster.scissor_x0, source->raster.width,
                    target_width, false) : 0;
  const uint32_t y0 = source
      ? scaled_edge(source->raster.scissor_y0, source->raster.height,
                    target_height, false) : 0;
  const uint32_t x1 = source
      ? scaled_edge(source->raster.scissor_x1, source->raster.width,
                    target_width, true) : target_width;
  const uint32_t y1 = source
      ? scaled_edge(source->raster.scissor_y1, source->raster.height,
                    target_height, true) : target_height;
  VkRect2D scissor{{static_cast<int32_t>(x0), static_cast<int32_t>(y0)},
                   {x1 - x0, y1 - y0}};
  const VkDeviceSize vertex_offset = 0;
  vkCmdBindPipeline(command, VK_PIPELINE_BIND_POINT_GRAPHICS,
                    draw_resources.pipeline);
  vkCmdSetViewport(command, 0, 1, &viewport);
  vkCmdSetScissor(command, 0, 1, &scissor);
  if (draw_resources.vertices.buffer != VK_NULL_HANDLE) {
    vkCmdBindVertexBuffers(command, 0, 1, &draw_resources.vertices.buffer,
                           &vertex_offset);
  }
  vkCmdBindDescriptorSets(command, VK_PIPELINE_BIND_POINT_GRAPHICS,
                          draw_resources.pipeline_layout, 0, 2,
                          draw_resources.descriptor_sets, 0, nullptr);
  if (!source || source->auto_index) {
    vkCmdDraw(command, source ? source->index_count : 3u, 1, 0, 0);
  } else {
    vkCmdBindIndexBuffer(command, draw_resources.indices.buffer, 0,
                         VK_INDEX_TYPE_UINT16);
    vkCmdDrawIndexed(command, source->index_count, 1, 0, 0, 0);
  }
}

uint64_t regular_render_pass_key(VkFormat color_format,
                                 VkSampleCountFlagBits samples,
                                 bool needs_depth, bool has_copy) {
  return (uint64_t{1} << 63) | (static_cast<uint64_t>(color_format) << 32) |
         (static_cast<uint64_t>(samples) << 8) |
         (needs_depth ? uint64_t{2} : uint64_t{0}) |
         (has_copy ? uint64_t{1} : uint64_t{0});
}

bool create_draw_resources(
    const CapturedVulkanDraw &source, size_t draw_index,
    TextureCacheState *texture_cache,
    const VkPhysicalDeviceMemoryProperties &memory_properties, VkDevice device,
    VkRenderPass render_pass, uint64_t render_pass_key,
    VkPipelineCache pipeline_cache, bool geometry_shader_enabled,
    CapturedVulkanSamplerCapabilities sampler_capabilities,
    DrawResources *output, std::string *error,
    bool use_linear_gamma_target_shader = false) {
  const std::vector<uint32_t> &pixel_shader_spirv =
      use_linear_gamma_target_shader
          ? source.pixel_shader_spirv_linear_target
          : source.pixel_shader_spirv;
  const uint32_t vertex_constants_size =
      sizeof(source.constants.vertex_float_constants);
  const uint32_t pixel_constants_size =
      sizeof(source.constants.pixel_float_constants);
  const bool has_vertex_inputs = !source.vertex_input_attributes.empty();
  struct TextureInput {
    uint32_t fetch_constant_index;
    const CapturedTextureSampling *sampling;
    uint32_t width;
    uint32_t height;
    CapturedVulkanTexture::Format format;
    const std::vector<uint8_t> *pixels;
    const CapturedVulkanTexture *captured = nullptr;
    VkImageView external_image_view = VK_NULL_HANDLE;
  };
  std::vector<TextureInput> texture_inputs;
  if (source.textures.empty()) {
      texture_inputs.push_back({0, &source.texture_sampling, source.texture_width,
                              source.texture_height,
                              CapturedVulkanTexture::Format::Rgba8,
                              &source.texture_rgba8, nullptr,
                              VK_NULL_HANDLE});
  } else {
    texture_inputs.reserve(source.textures.size());
    for (const CapturedVulkanTexture &texture : source.textures) {
      texture_inputs.push_back({texture.fetch_constant_index, &texture.sampling,
                                texture.width, texture.height, texture.format,
                                &texture.pixels, &texture,
                                texture.external_image_view});
    }
  }
  uint64_t total_texture_size = 0;
  for (size_t i = 0; i < texture_inputs.size(); ++i) {
    const TextureInput &texture = texture_inputs[i];
    const CapturedVulkanTexture *captured = texture.captured;
    const bool external_image = texture.external_image_view != VK_NULL_HANDLE;
    const bool captured_copy_source = captured &&
        find_guest_copy_texture(texture_cache, *captured) != nullptr;
    if (captured && captured->guest_copy_source && !captured_copy_source) {
      std::ostringstream message;
      message << "captured Copy/Convert texture cache lookup failed for address 0x"
              << std::hex << captured->guest_address << std::dec << " extent "
              << captured->width << 'x' << captured->height << " pitch "
              << captured->guest_pitch << "; cached copy keys="
              << (texture_cache ? texture_cache->guest_copy_images.size() : 0);
      if (texture_cache) {
        for (const auto& [key, image] : texture_cache->guest_copy_images) {
          (void)image;
          message << " [";
          for (size_t key_index = 0; key_index < key.values.size(); ++key_index) {
            if (key_index) message << ',';
            message << key.values[key_index];
          }
          message << ']';
        }
      }
      return fail(message.str(), error);
    }
    const uint64_t pixel_count =
        static_cast<uint64_t>(texture.width) * texture.height;
    const uint32_t bytes_per_pixel = texture.format ==
            CapturedVulkanTexture::Format::R8
        ? 1u
        : texture.format == CapturedVulkanTexture::Format::Rgba16Unorm
              ? 8u
              : 4u;
    if (texture.format != CapturedVulkanTexture::Format::R8 &&
        texture.format != CapturedVulkanTexture::Format::Rgba8 &&
        texture.format != CapturedVulkanTexture::Format::Rgba8Snorm &&
        texture.format != CapturedVulkanTexture::Format::Rg16Float &&
        texture.format != CapturedVulkanTexture::Format::Rgba16Unorm) {
      return fail("captured Vulkan texture format is unsupported", error);
    }
    if (texture.fetch_constant_index >= 32 || texture.width == 0 ||
        texture.height == 0 || pixel_count > (uint64_t{1} << 24) ||
        (!captured_copy_source && !external_image &&
         pixel_count * bytes_per_pixel != texture.pixels->size()) ||
        total_texture_size >
            (uint64_t{1} << 26) -
                (captured_copy_source || external_image
                     ? 0 : pixel_count * bytes_per_pixel)) {
      std::ostringstream message;
      message << "captured Vulkan texture resources are incomplete or oversized"
              << " at texture " << i << " (fetch="
              << texture.fetch_constant_index << ", extent=" << texture.width
              << 'x' << texture.height << ", bytes=" << texture.pixels->size()
              << ", expected=" << pixel_count * bytes_per_pixel
              << ", copy-cache=" << captured_copy_source << ')';
      return fail(message.str(), error);
    }
    for (size_t j = 0; j < i; ++j) {
      if (texture_inputs[j].fetch_constant_index ==
          texture.fetch_constant_index) {
        return fail("captured Vulkan textures use a duplicate fetch constant",
                    error);
      }
    }
    if (!captured_copy_source && !external_image)
      total_texture_size += pixel_count * bytes_per_pixel;
  }
  std::sort(texture_inputs.begin(), texture_inputs.end(),
            [](const TextureInput &left, const TextureInput &right) {
              return left.fetch_constant_index < right.fetch_constant_index;
            });
  if ((has_vertex_inputs && source.vertices.empty()) ||
      (!has_vertex_inputs && !source.vertices.empty()) ||
      source.index_count == 0 ||
      (source.auto_index ? !source.indices.empty() : source.indices.empty()) ||
      source.vertex_shader_spirv.empty() || pixel_shader_spirv.empty() ||
      (source.topology == PrimitiveTopology::RectangleList &&
       source.geometry_shader_spirv.empty()) ||
      (source.topology != PrimitiveTopology::RectangleList &&
       !source.geometry_shader_spirv.empty()) ||
      (!source.geometry_shader_spirv.empty() && !geometry_shader_enabled) ||
      (has_vertex_inputs && source.vertex_stride_bytes == 0) ||
      texture_inputs.empty()) {
    return fail("captured Vulkan draw resources are incomplete or oversized",
                error);
  }
  if (source.raster.blend_control_0 != 0x07060706u &&
      source.raster.blend_control_0 != 0x07010706u &&
      source.raster.blend_control_0 != 0x00010001u &&
      source.raster.blend_control_0 != 0x00010701u) {
    return fail("captured blend control is outside the supported retail draw",
                error);
  }
  const VkSampleCountFlagBits raster_samples =
      sample_count_flag(source.raster.sample_count);
  if (raster_samples == VkSampleCountFlagBits{}) {
    return fail("captured sample count is outside the Vulkan 1.1 subset",
                error);
  }

  GraphicsPipelineKey pipeline_key;
  CachedGraphicsPipeline *cached_pipeline_entry = nullptr;
  if (texture_cache && render_pass_key != 0) {
    pipeline_key.reserve(32 + source.vertex_shader_spirv.size() +
                         source.geometry_shader_spirv.size() +
                         pixel_shader_spirv.size());
    const auto append = [&pipeline_key](uint64_t value) {
      pipeline_key.push_back(value);
    };
    const auto append_shader = [&append](const std::vector<uint32_t> &shader) {
      append(shader.size());
      for (uint32_t word : shader)
        append(word);
    };
    append(1); // Pipeline key schema.
    append(render_pass_key);
    append(source.vertex_stride_bytes);
    append(static_cast<uint32_t>(source.topology));
    append(has_vertex_inputs);
    append(source.vertex_input_attributes.size());
    for (const CapturedVertexInputAttribute &attribute :
         source.vertex_input_attributes) {
      append(attribute.location);
      append(static_cast<uint64_t>(attribute.offset_dwords));
      append(static_cast<uint64_t>(attribute.stride_dwords));
      append(attribute.vertex_format);
    }
    append(static_cast<uint32_t>(source.raster.color_format));
    append(source.raster.sample_count);
    append(static_cast<uint32_t>(source.raster.cull_mode));
    append(source.raster.front_face_ccw);
    append(source.raster.depth_test_enabled);
    append(source.raster.depth_write_enabled);
    append(source.raster.depth_control);
    append(source.raster.stencil_test_enabled);
    append(source.raster.stencil_refmask);
    append(source.raster.blend_control_0);
    append(source.raster.color_write_mask);
    append_shader(source.vertex_shader_spirv);
    append_shader(source.geometry_shader_spirv);
    append_shader(pixel_shader_spirv);
    append(texture_inputs.size());
    for (const TextureInput &texture : texture_inputs) {
      append(texture.fetch_constant_index);
    }

    const auto found = texture_cache->graphics_pipelines.find(pipeline_key);
    if (found != texture_cache->graphics_pipelines.end()) {
      cached_pipeline_entry = &found->second;
      cached_pipeline_entry->last_used_frame = texture_cache->frame;
      output->cached_pipeline_entry = cached_pipeline_entry;
      output->pipeline = cached_pipeline_entry->pipeline;
    }
  }

  CachedDrawBuffers* cached_draw_buffers = nullptr;
  if (texture_cache && draw_index != std::numeric_limits<size_t>::max()) {
    auto found = texture_cache->draw_buffers.find(draw_index);
    if (found == texture_cache->draw_buffers.end() &&
        texture_cache->draw_buffers.size() < kDrawBufferCacheEntryLimit) {
      found = texture_cache->draw_buffers.emplace(
          draw_index, CachedDrawBuffers{}).first;
    }
    if (found != texture_cache->draw_buffers.end()) {
      cached_draw_buffers = &found->second;
      cached_draw_buffers->last_used_frame = texture_cache->frame;
    }
  }
  if ((has_vertex_inputs &&
       !upload_draw_buffer(
           memory_properties, device, source.vertices.size(),
           VK_BUFFER_USAGE_VERTEX_BUFFER_BIT, source.vertices.data(),
           texture_cache,
           cached_draw_buffers ? &cached_draw_buffers->vertices : nullptr,
           &output->vertices, error)) ||
      (!source.auto_index &&
       !upload_draw_buffer(
           memory_properties, device, source.indices.size(),
           VK_BUFFER_USAGE_INDEX_BUFFER_BIT, source.indices.data(),
           texture_cache,
           cached_draw_buffers ? &cached_draw_buffers->indices : nullptr,
           &output->indices, error)) ||
      !upload_draw_buffer(
          memory_properties, device, vertex_constants_size,
          VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT,
          source.constants.vertex_float_constants.data(), texture_cache,
          cached_draw_buffers ? &cached_draw_buffers->vertex_constants : nullptr,
          &output->vertex_constants, error) ||
      !upload_draw_buffer(
          memory_properties, device, pixel_constants_size,
          VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT,
          source.constants.pixel_float_constants.data(), texture_cache,
          cached_draw_buffers ? &cached_draw_buffers->pixel_constants : nullptr,
          &output->pixel_constants, error)) {
    return false;
  }

  for (const TextureInput &input : texture_inputs) {
    DrawTextureResources &texture = output->textures.emplace_back();
    texture.fetch_constant_index = input.fetch_constant_index;
    texture.width = input.width;
    texture.height = input.height;
    if (input.external_image_view) {
      texture.image.view = input.external_image_view;
      texture.image.borrowed = true;
      texture.external_image = true;
      texture.cached = true;
    } else {
      const VkFormat image_format =
          input.format == CapturedVulkanTexture::Format::R8
              ? VK_FORMAT_R8_UNORM
              : input.format == CapturedVulkanTexture::Format::Rg16Float
                    ? VK_FORMAT_R16G16_SFLOAT
                    : input.format == CapturedVulkanTexture::Format::Rgba16Unorm
                          ? VK_FORMAT_R16G16B16A16_UNORM
                          : input.format == CapturedVulkanTexture::Format::Rgba8Snorm
                                ? VK_FORMAT_R8G8B8A8_SNORM
                                : VK_FORMAT_R8G8B8A8_UNORM;
      CachedGuestCopyImage *guest_copy_image = input.captured
          ? find_guest_copy_texture(texture_cache, *input.captured)
          : nullptr;
      if (input.captured && input.captured->guest_copy_source &&
          !guest_copy_image) {
        return fail("captured Copy/Convert texture has no initialized exact-layout source image",
                    error);
      }
      if (guest_copy_image) {
        texture.image = guest_copy_image->image;
        if (input.captured->guest_format == 26u) {
          texture.image.view = guest_copy_image->sampled_view;
        }
        texture.image.borrowed = true;
        texture.cached = true;
        texture.guest_copy_source = true;
      }
      if (texture_cache && input.format == CapturedVulkanTexture::Format::R8) {
        if (!acquire_cached_r8_texture(texture_cache, memory_properties, device,
                                       draw_index, input.fetch_constant_index,
                                       input.width, input.height, *input.pixels,
                                       &texture, &texture.cached, error)) {
          return false;
        }
      }
      if (!texture.cached &&
          (!create_buffer(memory_properties, device, input.pixels->size(),
                          VK_BUFFER_USAGE_TRANSFER_SRC_BIT, input.pixels->data(),
                          &texture.upload, error) ||
           !create_texture_image(memory_properties, device, input.width,
                                 input.height, image_format, &texture.image,
                                 error))) {
        return false;
      }
    }
    bool sampler_supported = true;
    VkSamplerCreateInfo sampler_info{};
    sampler_info.sType = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO;
    sampler_info.magFilter =
        sampler_filter(input.sampling->mag_filter, &sampler_supported);
    sampler_info.minFilter =
        sampler_filter(input.sampling->min_filter, &sampler_supported);
    switch (input.sampling->mip_filter) {
    case TextureFilter::Point:
    case TextureFilter::BaseMap:
      sampler_info.mipmapMode = VK_SAMPLER_MIPMAP_MODE_NEAREST;
      break;
    case TextureFilter::Linear:
      sampler_info.mipmapMode = VK_SAMPLER_MIPMAP_MODE_LINEAR;
      break;
    default:
      sampler_supported = false;
      sampler_info.mipmapMode = VK_SAMPLER_MIPMAP_MODE_NEAREST;
      break;
    }
    sampler_info.addressModeU =
        sampler_address_mode(input.sampling->clamps[0], &sampler_supported);
    sampler_info.addressModeV =
        sampler_address_mode(input.sampling->clamps[1], &sampler_supported);
    sampler_info.addressModeW =
        sampler_address_mode(input.sampling->clamps[2], &sampler_supported);
    sampler_info.maxLod = 0.0f;
    sampler_info.borderColor = input.sampling->border_alpha_known
                                   ? VK_BORDER_COLOR_FLOAT_OPAQUE_BLACK
                                   : VK_BORDER_COLOR_FLOAT_TRANSPARENT_BLACK;
    float requested_anisotropy = 1.0f;
    switch (input.sampling->anisotropy) {
    case TextureAnisotropy::Disabled:
    case TextureAnisotropy::Max1To1:
      break;
    case TextureAnisotropy::Max2To1:
      requested_anisotropy = 2.0f;
      break;
    case TextureAnisotropy::Max4To1:
      requested_anisotropy = 4.0f;
      break;
    case TextureAnisotropy::Max8To1:
      requested_anisotropy = 8.0f;
      break;
    case TextureAnisotropy::Max16To1:
      requested_anisotropy = 16.0f;
      break;
    default:
      sampler_supported = false;
      break;
    }
    if (sampler_capabilities.anisotropy_enabled &&
        sampler_capabilities.max_anisotropy > 1.0f &&
        requested_anisotropy > 1.0f) {
      sampler_info.anisotropyEnable = VK_TRUE;
      sampler_info.maxAnisotropy =
          std::min(requested_anisotropy, sampler_capabilities.max_anisotropy);
    }
    if (!sampler_supported ||
        input.sampling->border_color != TextureBorderColor::AbgrBlack) {
      return fail(
          "captured sampler state is outside the Vulkan 1.1 live-draw subset",
          error);
    }
    const SamplerCacheKey sampler_key = make_sampler_cache_key(sampler_info);
    if (texture_cache) {
      const auto cached_sampler = texture_cache->samplers.find(sampler_key);
      if (cached_sampler != texture_cache->samplers.end()) {
        texture.sampler = cached_sampler->second;
        texture.cached_sampler = true;
      }
    }
    if (!texture.sampler) {
      const VkResult sampler_result =
          vkCreateSampler(device, &sampler_info, nullptr, &texture.sampler);
      if (sampler_result != VK_SUCCESS)
        return vk_fail("vkCreateSampler", sampler_result, error);
      if (texture_cache &&
          texture_cache->samplers.size() < kSamplerCacheEntryLimit) {
        texture_cache->samplers.emplace(sampler_key, texture.sampler);
        texture.cached_sampler = true;
      }
    }
  }

  VkResult result = VK_SUCCESS;
  if (!cached_pipeline_entry) {
    VkShaderModuleCreateInfo shader_info{};
    shader_info.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
    shader_info.codeSize = source.vertex_shader_spirv.size() * sizeof(uint32_t);
    shader_info.pCode = source.vertex_shader_spirv.data();
    result = vkCreateShaderModule(device, &shader_info, nullptr,
                                  &output->vertex_shader);
    if (result != VK_SUCCESS) {
      return vk_fail("vkCreateShaderModule(vertex)", result, error);
    }
    if (!source.geometry_shader_spirv.empty()) {
      shader_info.codeSize =
          source.geometry_shader_spirv.size() * sizeof(uint32_t);
      shader_info.pCode = source.geometry_shader_spirv.data();
      result = vkCreateShaderModule(device, &shader_info, nullptr,
                                    &output->geometry_shader);
      if (result != VK_SUCCESS) {
        return vk_fail("vkCreateShaderModule(geometry)", result, error);
      }
    }
    shader_info.codeSize = pixel_shader_spirv.size() * sizeof(uint32_t);
    shader_info.pCode = pixel_shader_spirv.data();
    result = vkCreateShaderModule(device, &shader_info, nullptr,
                                  &output->pixel_shader);
    if (result != VK_SUCCESS) {
      return vk_fail("vkCreateShaderModule(pixel)", result, error);
    }
  }

  VkDescriptorSetLayoutBinding constant_bindings[2]{};
  constant_bindings[0] = {14, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 1,
                          VK_SHADER_STAGE_VERTEX_BIT, nullptr};
  constant_bindings[1] = {15, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 1,
                          VK_SHADER_STAGE_FRAGMENT_BIT, nullptr};
  VkDescriptorSetLayoutCreateInfo descriptor_layout_info{};
  descriptor_layout_info.sType =
      VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
  descriptor_layout_info.bindingCount = 2;
  descriptor_layout_info.pBindings = constant_bindings;

  std::vector<VkDescriptorSetLayoutBinding> texture_bindings;
  texture_bindings.reserve(output->textures.size());
  for (const DrawTextureResources &texture : output->textures) {
    texture_bindings.push_back({texture.fetch_constant_index,
                                VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 1,
                                VK_SHADER_STAGE_FRAGMENT_BIT, nullptr});
  }
  DescriptorLayoutKey descriptor_layout_key;
  descriptor_layout_key.reserve(texture_bindings.size());
  for (const VkDescriptorSetLayoutBinding& binding : texture_bindings) {
    descriptor_layout_key.push_back(binding.binding);
  }
  bool descriptor_layouts_reused = false;
  if (texture_cache) {
    const auto cached = texture_cache->descriptor_layouts.find(
        descriptor_layout_key);
    if (cached != texture_cache->descriptor_layouts.end()) {
      output->descriptor_layouts[0] = cached->second.constants;
      output->descriptor_layouts[1] = cached->second.textures;
      output->pipeline_layout = cached->second.pipeline;
      output->cached_descriptor_layouts = true;
      descriptor_layouts_reused = true;
      ++texture_cache->descriptor_layout_cache_hits;
    }
  }
  if (!descriptor_layouts_reused) {
    result = vkCreateDescriptorSetLayout(device, &descriptor_layout_info,
                                         nullptr,
                                         &output->descriptor_layouts[0]);
    if (result != VK_SUCCESS)
      return vk_fail("vkCreateDescriptorSetLayout(constants)", result, error);

    descriptor_layout_info.bindingCount =
        static_cast<uint32_t>(texture_bindings.size());
    descriptor_layout_info.pBindings = texture_bindings.data();
    result = vkCreateDescriptorSetLayout(device, &descriptor_layout_info,
                                         nullptr,
                                         &output->descriptor_layouts[1]);
    if (result != VK_SUCCESS)
      return vk_fail("vkCreateDescriptorSetLayout(texture)", result, error);

    const VkPipelineLayoutCreateInfo pipeline_layout_info{
        VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        nullptr,
        0,
        2,
        output->descriptor_layouts,
        0,
        nullptr};
    result = vkCreatePipelineLayout(device, &pipeline_layout_info, nullptr,
                                    &output->pipeline_layout);
    if (result != VK_SUCCESS)
      return vk_fail("vkCreatePipelineLayout", result, error);

    if (texture_cache &&
        texture_cache->descriptor_layouts.size() <
            kDescriptorLayoutCacheEntryLimit) {
      const auto [entry, inserted] = texture_cache->descriptor_layouts.emplace(
          descriptor_layout_key,
          CachedDescriptorLayouts{output->descriptor_layouts[0],
                                  output->descriptor_layouts[1],
                                  output->pipeline_layout});
      if (inserted) {
        output->cached_descriptor_layouts = true;
      } else {
        vkDestroyPipelineLayout(device, output->pipeline_layout, nullptr);
        vkDestroyDescriptorSetLayout(device, output->descriptor_layouts[1],
                                     nullptr);
        vkDestroyDescriptorSetLayout(device, output->descriptor_layouts[0],
                                     nullptr);
        output->descriptor_layouts[0] = entry->second.constants;
        output->descriptor_layouts[1] = entry->second.textures;
        output->pipeline_layout = entry->second.pipeline;
        output->cached_descriptor_layouts = true;
      }
    }
  }

  const VkDescriptorPoolSize pool_sizes[2] = {
      {VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 2},
      {VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
       static_cast<uint32_t>(output->textures.size())},
  };
  VkDescriptorPoolCreateInfo pool_info{};
  pool_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
  pool_info.maxSets = 2;
  pool_info.poolSizeCount = 2;
  pool_info.pPoolSizes = pool_sizes;
  result = vkCreateDescriptorPool(device, &pool_info, nullptr,
                                  &output->descriptor_pool);
  if (result != VK_SUCCESS)
    return vk_fail("vkCreateDescriptorPool", result, error);
  VkDescriptorSetAllocateInfo set_info{};
  set_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
  set_info.descriptorPool = output->descriptor_pool;
  set_info.descriptorSetCount = 2;
  set_info.pSetLayouts = output->descriptor_layouts;
  result = vkAllocateDescriptorSets(device, &set_info, output->descriptor_sets);
  if (result != VK_SUCCESS)
    return vk_fail("vkAllocateDescriptorSets", result, error);

  VkDescriptorBufferInfo vertex_constant_info{output->vertex_constants.buffer,
                                              0, vertex_constants_size};
  VkDescriptorBufferInfo pixel_constant_info{output->pixel_constants.buffer, 0,
                                             pixel_constants_size};
  std::vector<VkDescriptorImageInfo> texture_infos;
  std::vector<VkWriteDescriptorSet> writes(2 + output->textures.size());
  texture_infos.reserve(output->textures.size());
  writes[0].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
  writes[0].dstSet = output->descriptor_sets[0];
  writes[0].dstBinding = 14;
  writes[0].descriptorCount = 1;
  writes[0].descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
  writes[0].pBufferInfo = &vertex_constant_info;
  writes[1].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
  writes[1].dstSet = output->descriptor_sets[0];
  writes[1].dstBinding = 15;
  writes[1].descriptorCount = 1;
  writes[1].descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
  writes[1].pBufferInfo = &pixel_constant_info;
  for (size_t i = 0; i < output->textures.size(); ++i) {
    const DrawTextureResources &texture = output->textures[i];
    texture_infos.push_back({texture.sampler, texture.image.view,
                             VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL});
    VkWriteDescriptorSet &write = writes[2 + i];
    write.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
    write.dstSet = output->descriptor_sets[1];
    write.dstBinding = texture.fetch_constant_index;
    write.descriptorCount = 1;
    write.descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
    write.pImageInfo = &texture_infos.back();
  }
  vkUpdateDescriptorSets(device, static_cast<uint32_t>(writes.size()),
                         writes.data(), 0, nullptr);

  if (!cached_pipeline_entry) {
    VkPipelineShaderStageCreateInfo stages[3]{};
    stages[0].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
    stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
    stages[0].module = output->vertex_shader;
    stages[0].pName = "main";
    uint32_t stage_count = 1;
    if (output->geometry_shader) {
      stages[stage_count].sType =
          VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
      stages[stage_count].stage = VK_SHADER_STAGE_GEOMETRY_BIT;
      stages[stage_count].module = output->geometry_shader;
      stages[stage_count].pName = "main";
      ++stage_count;
    }
    stages[stage_count].sType =
        VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
    stages[stage_count].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
    stages[stage_count].module = output->pixel_shader;
    stages[stage_count].pName = "main";
    ++stage_count;
    const VkVertexInputBindingDescription vertex_binding{
        0, source.vertex_stride_bytes, VK_VERTEX_INPUT_RATE_VERTEX};
    std::vector<VkVertexInputAttributeDescription> vertex_attributes;
    if (has_vertex_inputs) {
      vertex_attributes.reserve(source.vertex_input_attributes.size());
      for (const CapturedVertexInputAttribute &input :
           source.vertex_input_attributes) {
        VkFormat format = VK_FORMAT_UNDEFINED;
        if (input.vertex_format == 6) {
          format = VK_FORMAT_R8G8B8A8_UNORM;
        } else if (input.vertex_format == 37) {
          format = VK_FORMAT_R32G32_SFLOAT;
        } else if (input.vertex_format == 57) {
          format = VK_FORMAT_R32G32B32_SFLOAT;
        } else if (input.vertex_format == 38) {
          format = VK_FORMAT_R32G32B32A32_SFLOAT;
        } else {
          return fail("captured Vulkan vertex format is unsupported", error);
        }
        if (input.offset_dwords < 0 ||
            static_cast<uint64_t>(input.stride_dwords) * 4u !=
                source.vertex_stride_bytes) {
          return fail("captured Vulkan vertex layout is inconsistent", error);
        }
        vertex_attributes.push_back(
            {input.location, 0, format,
             static_cast<uint32_t>(input.offset_dwords) * 4u});
      }
    }
    VkPipelineVertexInputStateCreateInfo vertex_input{};
    vertex_input.sType =
        VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;
    vertex_input.vertexBindingDescriptionCount = has_vertex_inputs ? 1u : 0u;
    vertex_input.pVertexBindingDescriptions =
        has_vertex_inputs ? &vertex_binding : nullptr;
    vertex_input.vertexAttributeDescriptionCount =
        static_cast<uint32_t>(vertex_attributes.size());
    vertex_input.pVertexAttributeDescriptions = vertex_attributes.data();
    VkPipelineInputAssemblyStateCreateInfo assembly{};
    assembly.sType =
        VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO;
    if (source.topology == PrimitiveTopology::TriangleList) {
      assembly.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
    } else if (source.topology == PrimitiveTopology::PointList) {
      assembly.topology = VK_PRIMITIVE_TOPOLOGY_POINT_LIST;
    } else if (source.topology == PrimitiveTopology::RectangleList) {
      assembly.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
    } else if (source.topology == PrimitiveTopology::TriangleStrip) {
      assembly.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_STRIP;
    } else {
      return fail("captured Vulkan primitive topology is unsupported", error);
    }
    VkPipelineViewportStateCreateInfo viewport_state{};
    viewport_state.sType =
        VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO;
    viewport_state.viewportCount = 1;
    viewport_state.scissorCount = 1;
    VkPipelineRasterizationStateCreateInfo raster{};
    raster.sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
    raster.polygonMode = VK_POLYGON_MODE_FILL;
    switch (source.raster.cull_mode) {
    case CapturedRasterState::CullMode::None:
      raster.cullMode = VK_CULL_MODE_NONE;
      break;
    case CapturedRasterState::CullMode::Front:
      raster.cullMode = VK_CULL_MODE_FRONT_BIT;
      break;
    case CapturedRasterState::CullMode::Back:
      raster.cullMode = VK_CULL_MODE_BACK_BIT;
      break;
    }
    raster.frontFace = source.raster.front_face_ccw
                           ? VK_FRONT_FACE_COUNTER_CLOCKWISE
                           : VK_FRONT_FACE_CLOCKWISE;
    raster.lineWidth = 1.0f;
    VkPipelineMultisampleStateCreateInfo multisample{};
    multisample.sType =
        VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
    multisample.rasterizationSamples = raster_samples;
    VkPipelineDepthStencilStateCreateInfo depth{};
    depth.sType = VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO;
    depth.depthTestEnable = source.raster.depth_test_enabled &&
                            !captured_depth_test_is_noop(source.raster);
    depth.depthWriteEnable = source.raster.depth_write_enabled;
    depth.depthCompareOp = compare_op((source.raster.depth_control >> 4) & 7u);
    depth.stencilTestEnable = source.raster.stencil_test_enabled;
    const uint32_t stencil_reference = source.raster.stencil_refmask & 0xFFu;
    const uint32_t stencil_compare_mask =
        (source.raster.stencil_refmask >> 8) & 0xFFu;
    const uint32_t stencil_write_mask =
        (source.raster.stencil_refmask >> 16) & 0xFFu;
    const VkStencilOpState front_stencil{
        stencil_op((source.raster.depth_control >> 11) & 7u),
        stencil_op((source.raster.depth_control >> 14) & 7u),
        stencil_op((source.raster.depth_control >> 17) & 7u),
        compare_op((source.raster.depth_control >> 8) & 7u),
        stencil_compare_mask,
        stencil_write_mask,
        stencil_reference};
    VkStencilOpState back_stencil = front_stencil;
    if ((source.raster.depth_control & (1u << 7)) != 0) {
      back_stencil.failOp =
          stencil_op((source.raster.depth_control >> 23) & 7u);
      back_stencil.passOp =
          stencil_op((source.raster.depth_control >> 26) & 7u);
      back_stencil.depthFailOp =
          stencil_op((source.raster.depth_control >> 29) & 7u);
      back_stencil.compareOp =
          compare_op((source.raster.depth_control >> 20) & 7u);
    }
    depth.front = front_stencil;
    depth.back = back_stencil;
    VkPipelineColorBlendAttachmentState blend_attachment{};
    blend_attachment.blendEnable = source.raster.blend_control_0 != 0x00010001u;
    if (source.raster.blend_control_0 == 0x07060706u) {
      blend_attachment.srcColorBlendFactor = VK_BLEND_FACTOR_SRC_ALPHA;
      blend_attachment.dstColorBlendFactor =
          VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
      blend_attachment.srcAlphaBlendFactor = VK_BLEND_FACTOR_SRC_ALPHA;
      blend_attachment.dstAlphaBlendFactor =
          VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
    } else if (source.raster.blend_control_0 == 0x07010706u) {
      blend_attachment.srcColorBlendFactor = VK_BLEND_FACTOR_SRC_ALPHA;
      blend_attachment.dstColorBlendFactor =
          VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
      blend_attachment.srcAlphaBlendFactor = VK_BLEND_FACTOR_ONE;
      blend_attachment.dstAlphaBlendFactor =
          VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
    } else if (source.raster.blend_control_0 == 0x00010701u) {
      // Premultiplied-alpha blend: the source color already carries its
      // alpha, so the color term uses ONE rather than SRC_ALPHA. Retail emits
      // this on the menu overlay draws.
      blend_attachment.srcColorBlendFactor = VK_BLEND_FACTOR_ONE;
      blend_attachment.dstColorBlendFactor =
          VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
      blend_attachment.srcAlphaBlendFactor = VK_BLEND_FACTOR_ONE;
      blend_attachment.dstAlphaBlendFactor =
          VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
    } else {
      blend_attachment.srcColorBlendFactor = VK_BLEND_FACTOR_ONE;
      blend_attachment.dstColorBlendFactor = VK_BLEND_FACTOR_ZERO;
      blend_attachment.srcAlphaBlendFactor = VK_BLEND_FACTOR_ONE;
      blend_attachment.dstAlphaBlendFactor = VK_BLEND_FACTOR_ZERO;
    }
    blend_attachment.colorBlendOp = VK_BLEND_OP_ADD;
    blend_attachment.alphaBlendOp = VK_BLEND_OP_ADD;
    blend_attachment.colorWriteMask = 0;
    if (source.raster.color_write_mask & 1u)
      blend_attachment.colorWriteMask |= VK_COLOR_COMPONENT_R_BIT;
    if (source.raster.color_write_mask & 2u)
      blend_attachment.colorWriteMask |= VK_COLOR_COMPONENT_G_BIT;
    if (source.raster.color_write_mask & 4u)
      blend_attachment.colorWriteMask |= VK_COLOR_COMPONENT_B_BIT;
    if (source.raster.color_write_mask & 8u)
      blend_attachment.colorWriteMask |= VK_COLOR_COMPONENT_A_BIT;
    VkPipelineColorBlendStateCreateInfo blend{};
    blend.sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
    blend.attachmentCount = 1;
    blend.pAttachments = &blend_attachment;
    const VkDynamicState dynamic_values[] = {VK_DYNAMIC_STATE_VIEWPORT,
                                             VK_DYNAMIC_STATE_SCISSOR};
    VkPipelineDynamicStateCreateInfo dynamic{};
    dynamic.sType = VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO;
    dynamic.dynamicStateCount = 2;
    dynamic.pDynamicStates = dynamic_values;
    VkGraphicsPipelineCreateInfo pipeline_info{};
    pipeline_info.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;
    pipeline_info.stageCount = stage_count;
    pipeline_info.pStages = stages;
    pipeline_info.pVertexInputState = &vertex_input;
    pipeline_info.pInputAssemblyState = &assembly;
    pipeline_info.pViewportState = &viewport_state;
    pipeline_info.pRasterizationState = &raster;
    pipeline_info.pMultisampleState = &multisample;
    pipeline_info.pDepthStencilState = &depth;
    pipeline_info.pColorBlendState = &blend;
    pipeline_info.pDynamicState = &dynamic;
    pipeline_info.layout = output->pipeline_layout;
    pipeline_info.renderPass = render_pass;
    result = vkCreateGraphicsPipelines(
        device, pipeline_cache, 1, &pipeline_info, nullptr, &output->pipeline);
    if (result != VK_SUCCESS)
      return vk_fail("vkCreateGraphicsPipelines", result, error);
    if (texture_cache && render_pass_key != 0 &&
        make_room_for_graphics_pipeline(texture_cache)) {
      auto [entry, inserted] = texture_cache->graphics_pipelines.emplace(
          std::move(pipeline_key),
          CachedGraphicsPipeline{output->pipeline, texture_cache->frame});
      if (inserted) {
        cached_pipeline_entry = &entry->second;
        output->cached_pipeline_entry = cached_pipeline_entry;
      } else {
        vkDestroyPipeline(device, output->pipeline, nullptr);
        output->pipeline = entry->second.pipeline;
        entry->second.last_used_frame = texture_cache->frame;
        cached_pipeline_entry = &entry->second;
        output->cached_pipeline_entry = cached_pipeline_entry;
      }
    }
  }
  return true;
}

bool create_edram_clear_render_pass(VkDevice device,
                                   VkFormat color_format,
                                   VkSampleCountFlagBits samples,
                                   bool needs_depth,
                                   VkRenderPass* render_pass,
                                   std::string* error) {
    std::array<VkAttachmentDescription, 2> attachments{};
    attachments[0].format = color_format;
    attachments[0].samples = samples;
    attachments[0].loadOp = VK_ATTACHMENT_LOAD_OP_LOAD;
    attachments[0].storeOp = VK_ATTACHMENT_STORE_OP_STORE;
    attachments[0].stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    attachments[0].stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    attachments[0].initialLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    attachments[0].finalLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;

    VkAttachmentReference color_reference{0,
                                          VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};
    VkAttachmentReference depth_reference{};
    if (needs_depth) {
        attachments[1].format = VK_FORMAT_D24_UNORM_S8_UINT;
        attachments[1].samples = samples;
        attachments[1].loadOp = VK_ATTACHMENT_LOAD_OP_LOAD;
        attachments[1].storeOp = VK_ATTACHMENT_STORE_OP_STORE;
        attachments[1].stencilLoadOp = VK_ATTACHMENT_LOAD_OP_LOAD;
        attachments[1].stencilStoreOp = VK_ATTACHMENT_STORE_OP_STORE;
        attachments[1].initialLayout =
            VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
        attachments[1].finalLayout =
            VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
        depth_reference = {1,
                           VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL};
    }

    VkSubpassDescription subpass{};
    subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
    subpass.colorAttachmentCount = 1;
    subpass.pColorAttachments = &color_reference;
    subpass.pDepthStencilAttachment = needs_depth ? &depth_reference : nullptr;
    VkSubpassDependency dependency{};
    dependency.srcSubpass = VK_SUBPASS_EXTERNAL;
    dependency.dstSubpass = 0;
    dependency.srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
                              VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT |
                              VK_PIPELINE_STAGE_LATE_FRAGMENT_TESTS_BIT;
    dependency.dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
                              VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT |
                              VK_PIPELINE_STAGE_LATE_FRAGMENT_TESTS_BIT;
    dependency.srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT |
                               VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;
    dependency.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_READ_BIT |
                               VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT |
                               VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_READ_BIT |
                               VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;
    VkRenderPassCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
    info.attachmentCount = needs_depth ? 2u : 1u;
    info.pAttachments = attachments.data();
    info.subpassCount = 1;
    info.pSubpasses = &subpass;
    info.dependencyCount = 1;
    info.pDependencies = &dependency;
    const VkResult result = vkCreateRenderPass(device, &info, nullptr, render_pass);
    return result == VK_SUCCESS
        ? true
        : vk_fail("vkCreateRenderPass(EDRAM clear)", result, error);
}

bool create_mixed_msaa_render_pass(
    VkDevice device,
    VkFormat color_format,
    bool needs_msaa_depth,
    bool resolve_depth_stencil,
    bool preserve_msaa_color,
    VkRenderPass* render_pass,
    std::string* error) {
    if (resolve_depth_stencil) {
        auto create_render_pass_2 = reinterpret_cast<PFN_vkCreateRenderPass2KHR>(
            vkGetDeviceProcAddr(device, "vkCreateRenderPass2"));
        if (!create_render_pass_2) {
            create_render_pass_2 = reinterpret_cast<PFN_vkCreateRenderPass2KHR>(
                vkGetDeviceProcAddr(device, "vkCreateRenderPass2KHR"));
        }
        if (!create_render_pass_2) {
            return fail("mixed 4x-to-1x depth/stencil preservation requires "
                        "provider-enabled Vulkan 1.2 core or Vulkan 1.1 KHR resolve support",
                        error);
        }

        std::vector<VkAttachmentDescription2> attachments(4);
        for (auto& attachment : attachments) {
            attachment.sType = VK_STRUCTURE_TYPE_ATTACHMENT_DESCRIPTION_2;
        }
        attachments[0].format = color_format;
        attachments[0].samples = VK_SAMPLE_COUNT_4_BIT;
        attachments[0].loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        attachments[0].storeOp = preserve_msaa_color
            ? VK_ATTACHMENT_STORE_OP_STORE : VK_ATTACHMENT_STORE_OP_DONT_CARE;
        attachments[0].stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
        attachments[0].stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        attachments[0].initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        attachments[0].finalLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        attachments[1].format = color_format;
        attachments[1].samples = VK_SAMPLE_COUNT_1_BIT;
        attachments[1].loadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
        attachments[1].storeOp = VK_ATTACHMENT_STORE_OP_STORE;
        attachments[1].stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
        attachments[1].stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        attachments[1].initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        attachments[1].finalLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        attachments[2].format = VK_FORMAT_D24_UNORM_S8_UINT;
        attachments[2].samples = VK_SAMPLE_COUNT_4_BIT;
        attachments[2].loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        attachments[2].storeOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        attachments[2].stencilLoadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        attachments[2].stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        attachments[2].initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        attachments[2].finalLayout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
        attachments[3].format = VK_FORMAT_D24_UNORM_S8_UINT;
        attachments[3].samples = VK_SAMPLE_COUNT_1_BIT;
        attachments[3].loadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
        attachments[3].storeOp = VK_ATTACHMENT_STORE_OP_STORE;
        attachments[3].stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
        attachments[3].stencilStoreOp = VK_ATTACHMENT_STORE_OP_STORE;
        attachments[3].initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        attachments[3].finalLayout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;

        VkAttachmentReference2 color_reference{};
        color_reference.sType = VK_STRUCTURE_TYPE_ATTACHMENT_REFERENCE_2;
        color_reference.attachment = 0;
        color_reference.layout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        color_reference.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        VkAttachmentReference2 color_resolve_reference{};
        color_resolve_reference.sType = VK_STRUCTURE_TYPE_ATTACHMENT_REFERENCE_2;
        color_resolve_reference.attachment = 1;
        color_resolve_reference.layout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        color_resolve_reference.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        VkAttachmentReference2 depth_reference{};
        depth_reference.sType = VK_STRUCTURE_TYPE_ATTACHMENT_REFERENCE_2;
        depth_reference.attachment = 2;
        depth_reference.layout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
        depth_reference.aspectMask = VK_IMAGE_ASPECT_DEPTH_BIT |
                                     VK_IMAGE_ASPECT_STENCIL_BIT;
        VkAttachmentReference2 depth_resolve_reference{};
        depth_resolve_reference.sType = VK_STRUCTURE_TYPE_ATTACHMENT_REFERENCE_2;
        depth_resolve_reference.attachment = 3;
        depth_resolve_reference.layout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
        depth_resolve_reference.aspectMask = VK_IMAGE_ASPECT_DEPTH_BIT |
                                            VK_IMAGE_ASPECT_STENCIL_BIT;
        VkSubpassDescriptionDepthStencilResolve depth_stencil_resolve{};
        depth_stencil_resolve.sType =
            VK_STRUCTURE_TYPE_SUBPASS_DESCRIPTION_DEPTH_STENCIL_RESOLVE;
        depth_stencil_resolve.depthResolveMode = VK_RESOLVE_MODE_SAMPLE_ZERO_BIT;
        depth_stencil_resolve.stencilResolveMode = VK_RESOLVE_MODE_SAMPLE_ZERO_BIT;
        depth_stencil_resolve.pDepthStencilResolveAttachment =
            &depth_resolve_reference;
        VkSubpassDescription2 subpass{};
        subpass.sType = VK_STRUCTURE_TYPE_SUBPASS_DESCRIPTION_2;
        subpass.pNext = &depth_stencil_resolve;
        subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
        subpass.colorAttachmentCount = 1;
        subpass.pColorAttachments = &color_reference;
        subpass.pResolveAttachments = &color_resolve_reference;
        subpass.pDepthStencilAttachment = &depth_reference;

        VkSubpassDependency2 dependencies[2]{};
        for (auto& dependency : dependencies) {
            dependency.sType = VK_STRUCTURE_TYPE_SUBPASS_DEPENDENCY_2;
        }
        dependencies[0].srcSubpass = VK_SUBPASS_EXTERNAL;
        dependencies[0].dstSubpass = 0;
        dependencies[0].srcStageMask = VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT;
        dependencies[0].dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
                                       VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT;
        dependencies[0].dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT |
                                        VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_READ_BIT |
                                        VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;
        dependencies[1].srcSubpass = 0;
        dependencies[1].dstSubpass = VK_SUBPASS_EXTERNAL;
        dependencies[1].srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
                                       VK_PIPELINE_STAGE_LATE_FRAGMENT_TESTS_BIT;
        dependencies[1].dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
                                       VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT;
        dependencies[1].srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT |
                                        VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;
        dependencies[1].dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_READ_BIT |
                                        VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT |
                                        VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_READ_BIT |
                                        VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;

        VkRenderPassCreateInfo2 create_info{};
        create_info.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO_2;
        create_info.attachmentCount = static_cast<uint32_t>(attachments.size());
        create_info.pAttachments = attachments.data();
        create_info.subpassCount = 1;
        create_info.pSubpasses = &subpass;
        create_info.dependencyCount = 2;
        create_info.pDependencies = dependencies;
        const VkResult result = create_render_pass_2(
            device, &create_info, nullptr, render_pass);
        return result == VK_SUCCESS
            ? true : vk_fail("vkCreateRenderPass2KHR(mixed 4x depth resolve)",
                             result, error);
    }

    std::vector<VkAttachmentDescription> attachments(2);
    attachments[0].format = color_format;
    attachments[0].samples = VK_SAMPLE_COUNT_4_BIT;
    attachments[0].loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
    attachments[0].storeOp = preserve_msaa_color
        ? VK_ATTACHMENT_STORE_OP_STORE : VK_ATTACHMENT_STORE_OP_DONT_CARE;
    attachments[0].stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    attachments[0].stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    attachments[0].initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    attachments[0].finalLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    attachments[1].format = color_format;
    attachments[1].samples = VK_SAMPLE_COUNT_1_BIT;
    attachments[1].loadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    attachments[1].storeOp = VK_ATTACHMENT_STORE_OP_STORE;
    attachments[1].stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    attachments[1].stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    attachments[1].initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    attachments[1].finalLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    VkAttachmentReference color_reference{0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};
    VkAttachmentReference resolve_reference{1, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};
    VkAttachmentReference depth_reference{};
    if (needs_msaa_depth) {
        depth_reference.attachment = static_cast<uint32_t>(attachments.size());
        depth_reference.layout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
        VkAttachmentDescription depth_attachment{};
        depth_attachment.format = VK_FORMAT_D24_UNORM_S8_UINT;
        depth_attachment.samples = VK_SAMPLE_COUNT_4_BIT;
        depth_attachment.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        depth_attachment.storeOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        depth_attachment.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        depth_attachment.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        depth_attachment.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        depth_attachment.finalLayout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
        attachments.push_back(depth_attachment);
    }
    VkSubpassDescription subpass{};
    subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
    subpass.colorAttachmentCount = 1;
    subpass.pColorAttachments = &color_reference;
    subpass.pResolveAttachments = &resolve_reference;
    subpass.pDepthStencilAttachment = needs_msaa_depth ? &depth_reference : nullptr;
    VkSubpassDependency dependencies[2]{};
    dependencies[0].srcSubpass = VK_SUBPASS_EXTERNAL;
    dependencies[0].dstSubpass = 0;
    dependencies[0].srcStageMask = VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT;
    dependencies[0].dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
        (needs_msaa_depth ? VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT : 0);
    dependencies[0].dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT |
        (needs_msaa_depth ? VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_READ_BIT |
                                VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT
                          : 0);
    dependencies[1].srcSubpass = 0;
    dependencies[1].dstSubpass = VK_SUBPASS_EXTERNAL;
    dependencies[1].srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
        (needs_msaa_depth ? VK_PIPELINE_STAGE_LATE_FRAGMENT_TESTS_BIT : 0);
    dependencies[1].dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
        (needs_msaa_depth ? VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT : 0);
    dependencies[1].srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT |
        (needs_msaa_depth ? VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT : 0);
    dependencies[1].dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_READ_BIT |
        VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT |
        (needs_msaa_depth ? VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_READ_BIT |
                               VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT
                          : 0);
    VkRenderPassCreateInfo create_info{};
    create_info.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
    create_info.attachmentCount = static_cast<uint32_t>(attachments.size());
    create_info.pAttachments = attachments.data();
    create_info.subpassCount = 1;
    create_info.pSubpasses = &subpass;
    create_info.dependencyCount = 2;
    create_info.pDependencies = dependencies;
    const VkResult result = vkCreateRenderPass(device, &create_info, nullptr, render_pass);
    return result == VK_SUCCESS ? true : vk_fail("vkCreateRenderPass(mixed 4x)",
                                                result, error);
}

bool submit_mixed_sample_copy_frame(
    VkPhysicalDevice physical_device,
    VkDevice device,
    VkQueue queue,
    uint32_t queue_family_index,
    VkImage output_image,
    VkImageView output_view,
    bool output_written_before,
    uint32_t output_width,
    uint32_t output_height,
    const std::vector<CapturedVulkanDraw>& draws,
    std::string* error,
    std::vector<uint32_t>* output_readback,
    bool geometry_shader_enabled,
    const CapturedVulkanCopy& copy,
    bool depth_stencil_resolve_enabled,
    CapturedVulkanSamplerCapabilities sampler_capabilities,
    VkPipelineCache pipeline_cache,
    TextureCacheState* texture_cache,
    CapturedVulkanSourceReadback* source_readback,
    std::vector<CapturedVulkanDrawVisibility>* draw_visibility) {
    if (draws.empty() || draws.front().raster.sample_count != 4 ||
        copy.single_sample_pixel_shader_spirv.empty() ||
        (copy.source_gamma &&
         copy.gamma_single_sample_pixel_shader_spirv.empty())) {
        return fail("mixed captured frame requires 4x-MSAA followed by 1x and a single-sample Copy/Convert shader",
                    error);
    }

    bool needs_msaa_depth = false;
    bool needs_single_depth = false;
    const CapturedRasterState& target = draws.front().raster;
    const bool linear_rgba8_intermediate = frame_has_gamma_color_target(draws);
    const VkFormat target_format = captured_color_format(
        target.color_format, linear_rgba8_intermediate);
    const uint32_t source_width = copy.source_width ? copy.source_width
                                                   : target.width;
    const uint32_t source_height = copy.source_height ? copy.source_height
                                                       : target.height;
    if (target_format == VK_FORMAT_UNDEFINED) {
        std::ostringstream message;
        message << "mixed captured frame has unsupported Xenos color target format "
                << static_cast<unsigned>(target.color_format);
        return fail(message.str(), error);
    }
    if (source_width != target.width || source_height != target.height) {
        std::ostringstream message;
        message << "mixed captured Copy/Convert source extent " << source_width
                << 'x' << source_height << " does not match first render target "
                << target.width << 'x' << target.height;
        return fail(message.str(), error);
    }
    size_t first_single_sample_draw = 0;
    while (first_single_sample_draw < draws.size() &&
           draws[first_single_sample_draw].raster.sample_count == 4) {
        ++first_single_sample_draw;
    }
    if (first_single_sample_draw == draws.size()) {
        return fail("mixed captured frame has no single-sample draw", error);
    }
    const bool has_msaa_color_source = std::any_of(
        draws.begin(), draws.begin() + first_single_sample_draw,
        [](const CapturedVulkanDraw& draw) {
            return !draw.raster.depth_only && draw.raster.color_write_mask != 0;
        });
    const bool alias_transfer_needed = has_msaa_color_source &&
        is_captured_gamma_4x_to_1x_edram_alias(
            target, draws[first_single_sample_draw].raster);
    if (alias_transfer_needed &&
        (copy.edram_alias_transfer_vertex_shader_spirv.empty() ||
         copy.edram_alias_transfer_pixel_shader_spirv.empty())) {
        return fail("mixed captured frame requires the Vulkan 1.1 EDRAM sample-alias transfer shaders",
                    error);
    }
    std::vector<bool> remap_trailing_msaa_to_single(draws.size(), false);
    std::vector<bool> later_single_depth_stencil_use(draws.size(), false);
    bool has_later_single_depth_stencil_use = false;
    for (size_t i = draws.size(); i-- > first_single_sample_draw;) {
        later_single_depth_stencil_use[i] =
            has_later_single_depth_stencil_use;
        const CapturedRasterState& raster = draws[i].raster;
        // Keep a conservative read of the guest's declared DS use here: a
        // later guest operation may observe an earlier stencil side effect,
        // even when its own depth compare is ALWAYS.
        has_later_single_depth_stencil_use |= raster.sample_count == 1 &&
            (raster.depth_test_enabled || raster.depth_write_enabled ||
             raster.stencil_test_enabled);
    }
    std::vector<size_t> rendered_draw_indices;
    rendered_draw_indices.reserve(draws.size());
    for (size_t i = 0; i < draws.size(); ++i) {
        const CapturedVulkanDraw& draw = draws[i];
        const CapturedRasterState& raster = draw.raster;
        const bool depth_only_view =
            is_captured_gamma_depth_only_view_alias(target, raster);
        const bool skip_trailing_msaa_draw =
            i >= first_single_sample_draw && raster.sample_count == 4;
        if (skip_trailing_msaa_draw) {
            const uint32_t stencil_write_mask =
                (raster.stencil_refmask >> 16) & 0xFFu;
            if (raster.color_write_mask != 0) {
                std::ostringstream message;
                message << "mixed captured frame returns to 4x after its 1x draws "
                           "with a color/depth-writing draw " << i
                        << "; color_mask=0x" << std::hex
                        << raster.color_write_mask << std::dec
                        << " depth_write=" << raster.depth_write_enabled
                        << " stencil_write_mask=0x" << std::hex
                        << stencil_write_mask << std::dec;
                return fail(message.str(), error);
            }
            const bool writes_depth_stencil = raster.depth_write_enabled ||
                (raster.stencil_test_enabled && stencil_write_mask != 0);
            if (writes_depth_stencil && later_single_depth_stencil_use[i]) {
                remap_trailing_msaa_to_single[i] = true;
            }
        } else if (raster.sample_count != 1 && raster.sample_count != 4) {
            std::ostringstream message;
            message << "mixed captured frame currently supports a single 4x-MSAA "
                       "to 1x target transition; captured draws=" << draws.size();
            for (size_t j = 0; j < draws.size(); ++j) {
                const CapturedRasterState& state = draws[j].raster;
                message << " draw" << j << "={samples=" << state.sample_count
                        << ",extent=" << state.width << 'x' << state.height
                        << ",pitch=" << state.surface_pitch << ",color_base=0x"
                        << std::hex << state.color_base_tiles << ",depth_base=0x"
                        << state.depth_base_tiles << std::dec << ",color_format="
                        << static_cast<unsigned>(state.color_format)
                        << ",color_mask=0x" << std::hex
                        << state.color_write_mask << std::dec << ",depth={test:"
                        << state.depth_test_enabled << ",write:"
                        << state.depth_write_enabled << ",stencil:"
                        << state.stencil_test_enabled << "}}";
            }
            return fail(message.str(), error);
        }
        if (raster.width != target.width || raster.height != target.height ||
            raster.color_base_tiles != target.color_base_tiles ||
            raster.depth_base_tiles != target.depth_base_tiles ||
            (!depth_only_view &&
             raster.guest_color_format != target.guest_color_format) ||
            (!depth_only_view &&
             captured_color_format(raster.color_format,
                                   linear_rgba8_intermediate) != target_format) ||
            raster.depth_format != target.depth_format) {
            std::ostringstream message;
            message << "mixed captured draw " << i
                    << " changes the guest render target within the frame";
            return fail(message.str(), error);
        }
        if (draw.topology == PrimitiveTopology::RectangleList &&
            !geometry_shader_enabled) {
            return fail("captured rectangle-list draw requires an enabled Vulkan geometry shader",
                        error);
        }
        if (raster.width == 0 || raster.height == 0 ||
            raster.scissor_x1 > raster.width || raster.scissor_y1 > raster.height ||
            raster.scissor_x0 > raster.scissor_x1 ||
            raster.scissor_y0 > raster.scissor_y1) {
            std::ostringstream message;
            message << "mixed captured draw " << i
                    << " has an invalid raster extent or scissor";
            return fail(message.str(), error);
        }
        if (skip_trailing_msaa_draw && !remap_trailing_msaa_to_single[i]) continue;
        rendered_draw_indices.push_back(i);
        const bool render_as_single_sample = raster.sample_count == 1 ||
            remap_trailing_msaa_to_single[i];
        needs_msaa_depth |= !render_as_single_sample &&
            captured_depth_stencil_attachment_used(raster);
        needs_single_depth |= render_as_single_sample &&
            captured_depth_stencil_attachment_used(raster);
    }
    if (needs_msaa_depth && needs_single_depth &&
        !depth_stencil_resolve_enabled) {
        return fail("mixed 4x-to-1x depth/stencil preservation requires a "
                    "provider-confirmed enabled resolve capability",
                    error);
    }
    if (target.width == 0 || target.height == 0 ||
        target.width > static_cast<uint32_t>(std::numeric_limits<int32_t>::max()) ||
        target.height > static_cast<uint32_t>(std::numeric_limits<int32_t>::max()) ||
        copy.state.source_select != 0 || copy.state.sample_select != 0 ||
        copy.state.command != CapturedCopyCommand::Convert ||
        copy.state.destination_pitch != output_width ||
        copy.state.destination_height != output_height ||
        copy.state.destination_format != 6 ||
        !copy.state.destination_swap_red_blue ||
        copy.vertex_shader_spirv.empty()) {
        return fail("mixed captured frame is outside the 4x-to-1x source-0/sample-0 Copy/Convert subset",
                    error);
    }

    VkPhysicalDeviceMemoryProperties memory_properties{};
    vkGetPhysicalDeviceMemoryProperties(physical_device, &memory_properties);
    auto resources_owner = std::make_unique<FrameResources>();
    FrameResources& resources = *resources_owner;
    resources.device = device;
    resources.queue = queue;
    resources.upload_slot = texture_cache ? texture_cache->upload_slot : 0;
    prepare_draw_visibility_queries(device, draws.size(), resources,
                                    draw_visibility);
    std::vector<size_t> draw_resource_indices(
        draws.size(), std::numeric_limits<size_t>::max());
    resources.draws.resize(rendered_draw_indices.size());
    bool source_readback_ready = prepare_source_readback_buffer(
        memory_properties, device, source_width, source_height, target_format,
        1, false, resources, source_readback);
    constexpr VkImageUsageFlags mixed_source_usage =
        VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_SAMPLED_BIT;
    const VkImageUsageFlags mixed_msaa_usage =
        VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT |
        (alias_transfer_needed ? VK_IMAGE_USAGE_SAMPLED_BIT : 0u);
    if (source_readback_ready) {
        std::string optional_error;
        if (!create_render_attachment(
                memory_properties, device, target.width, target.height,
                target_format, mixed_source_usage | VK_IMAGE_USAGE_TRANSFER_SRC_BIT,
                VK_IMAGE_ASPECT_COLOR_BIT, VK_SAMPLE_COUNT_1_BIT,
                &resources.mixed_color, &optional_error)) {
            resources.destroy_image(resources.mixed_color);
            source_readback_ready = false;
            source_readback_unsupported(
                source_readback, "mixed source image transfer readback unavailable: " +
                                     optional_error);
        }
    }
    if ((!resources.mixed_color.image &&
         !create_render_attachment(
             memory_properties, device, target.width, target.height,
             target_format, mixed_source_usage, VK_IMAGE_ASPECT_COLOR_BIT,
             VK_SAMPLE_COUNT_1_BIT, &resources.mixed_color, error)) ||
        !create_render_attachment(
            memory_properties, device, target.width, target.height,
            target_format,
            mixed_msaa_usage,
            VK_IMAGE_ASPECT_COLOR_BIT, VK_SAMPLE_COUNT_4_BIT,
            &resources.mixed_msaa_color, error)) {
        return false;
    }
    if (needs_msaa_depth &&
        !create_render_attachment(
            memory_properties, device, target.width, target.height,
            VK_FORMAT_D24_UNORM_S8_UINT,
            VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT,
            VK_IMAGE_ASPECT_DEPTH_BIT | VK_IMAGE_ASPECT_STENCIL_BIT,
            VK_SAMPLE_COUNT_4_BIT, &resources.mixed_msaa_depth, error)) {
        return false;
    }
    if (needs_single_depth &&
        !create_render_attachment(
            memory_properties, device, target.width, target.height,
            VK_FORMAT_D24_UNORM_S8_UINT,
            VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT,
            VK_IMAGE_ASPECT_DEPTH_BIT | VK_IMAGE_ASPECT_STENCIL_BIT,
            VK_SAMPLE_COUNT_1_BIT, &resources.mixed_single_depth, error)) {
        return false;
    }

    const bool resolve_depth_stencil = needs_msaa_depth && needs_single_depth;
    if (!create_mixed_msaa_render_pass(
            device, target_format, needs_msaa_depth,
            resolve_depth_stencil, alias_transfer_needed,
            &resources.mixed_msaa_render_pass, error)) {
        return false;
    }
    std::vector<VkImageView> msaa_views{resources.mixed_msaa_color.view,
                                        resources.mixed_color.view};
    if (needs_msaa_depth) msaa_views.push_back(resources.mixed_msaa_depth.view);
    if (resolve_depth_stencil) msaa_views.push_back(resources.mixed_single_depth.view);
    VkFramebufferCreateInfo msaa_framebuffer_info{};
    msaa_framebuffer_info.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
    msaa_framebuffer_info.renderPass = resources.mixed_msaa_render_pass;
    msaa_framebuffer_info.attachmentCount = static_cast<uint32_t>(msaa_views.size());
    msaa_framebuffer_info.pAttachments = msaa_views.data();
    msaa_framebuffer_info.width = target.width;
    msaa_framebuffer_info.height = target.height;
    msaa_framebuffer_info.layers = 1;
    VkResult result = vkCreateFramebuffer(device, &msaa_framebuffer_info, nullptr,
                                          &resources.mixed_msaa_framebuffer);
    if (result != VK_SUCCESS) return vk_fail("vkCreateFramebuffer(mixed 4x)", result, error);

    std::vector<VkAttachmentDescription> single_attachments(1);
    single_attachments[0].format = target_format;
    single_attachments[0].samples = VK_SAMPLE_COUNT_1_BIT;
    single_attachments[0].loadOp = VK_ATTACHMENT_LOAD_OP_LOAD;
    single_attachments[0].storeOp = VK_ATTACHMENT_STORE_OP_STORE;
    single_attachments[0].stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    single_attachments[0].stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    single_attachments[0].initialLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    single_attachments[0].finalLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    VkAttachmentReference single_color_reference{0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};
    VkAttachmentReference single_depth_reference{};
    if (needs_single_depth) {
        single_depth_reference.attachment =
            static_cast<uint32_t>(single_attachments.size());
        single_depth_reference.layout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
        VkAttachmentDescription depth_attachment{};
        depth_attachment.format = VK_FORMAT_D24_UNORM_S8_UINT;
        depth_attachment.samples = VK_SAMPLE_COUNT_1_BIT;
        depth_attachment.loadOp = resolve_depth_stencil
            ? VK_ATTACHMENT_LOAD_OP_LOAD : VK_ATTACHMENT_LOAD_OP_CLEAR;
        depth_attachment.storeOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        depth_attachment.stencilLoadOp = resolve_depth_stencil
            ? VK_ATTACHMENT_LOAD_OP_LOAD : VK_ATTACHMENT_LOAD_OP_CLEAR;
        depth_attachment.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        depth_attachment.initialLayout = resolve_depth_stencil
            ? VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL
            : VK_IMAGE_LAYOUT_UNDEFINED;
        depth_attachment.finalLayout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
        single_attachments.push_back(depth_attachment);
    }
    VkSubpassDescription single_subpass{};
    single_subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
    single_subpass.colorAttachmentCount = 1;
    single_subpass.pColorAttachments = &single_color_reference;
    single_subpass.pDepthStencilAttachment =
        needs_single_depth ? &single_depth_reference : nullptr;
    VkSubpassDependency single_dependencies[2]{};
    single_dependencies[0].srcSubpass = VK_SUBPASS_EXTERNAL;
    single_dependencies[0].dstSubpass = 0;
    single_dependencies[0].srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
        (resolve_depth_stencil ? VK_PIPELINE_STAGE_LATE_FRAGMENT_TESTS_BIT : 0);
    single_dependencies[0].dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
        (needs_single_depth ? VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT : 0);
    single_dependencies[0].srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT |
        (resolve_depth_stencil ? VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT : 0);
    single_dependencies[0].dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_READ_BIT |
        VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT |
        (needs_single_depth ? VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_READ_BIT |
                                 VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT
                           : 0);
    single_dependencies[1].srcSubpass = 0;
    single_dependencies[1].dstSubpass = VK_SUBPASS_EXTERNAL;
    single_dependencies[1].srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
    single_dependencies[1].dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
                                          VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT;
    single_dependencies[1].srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
    single_dependencies[1].dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_READ_BIT |
                                            VK_ACCESS_SHADER_READ_BIT;
    VkRenderPassCreateInfo single_pass_info{};
    single_pass_info.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
    single_pass_info.attachmentCount = static_cast<uint32_t>(single_attachments.size());
    single_pass_info.pAttachments = single_attachments.data();
    single_pass_info.subpassCount = 1;
    single_pass_info.pSubpasses = &single_subpass;
    single_pass_info.dependencyCount = 2;
    single_pass_info.pDependencies = single_dependencies;
    result = vkCreateRenderPass(
        device, &single_pass_info, nullptr, &resources.mixed_single_render_pass);
    if (result != VK_SUCCESS) return vk_fail("vkCreateRenderPass(mixed 1x)", result, error);

    std::vector<VkImageView> single_views{resources.mixed_color.view};
    if (needs_single_depth) single_views.push_back(resources.mixed_single_depth.view);
    VkFramebufferCreateInfo single_framebuffer_info{};
    single_framebuffer_info.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
    single_framebuffer_info.renderPass = resources.mixed_single_render_pass;
    single_framebuffer_info.attachmentCount = static_cast<uint32_t>(single_views.size());
    single_framebuffer_info.pAttachments = single_views.data();
    single_framebuffer_info.width = target.width;
    single_framebuffer_info.height = target.height;
    single_framebuffer_info.layers = 1;
    result = vkCreateFramebuffer(device, &single_framebuffer_info, nullptr,
                                 &resources.mixed_single_framebuffer);
    if (result != VK_SUCCESS) return vk_fail("vkCreateFramebuffer(mixed 1x)", result, error);

    VkAttachmentDescription copy_attachment{};
    copy_attachment.format = VK_FORMAT_A2B10G10R10_UNORM_PACK32;
    copy_attachment.samples = VK_SAMPLE_COUNT_1_BIT;
    copy_attachment.loadOp = output_written_before
        ? VK_ATTACHMENT_LOAD_OP_LOAD : VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    copy_attachment.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
    copy_attachment.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    copy_attachment.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    copy_attachment.initialLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    copy_attachment.finalLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    VkAttachmentReference copy_color_reference{0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};
    VkSubpassDescription copy_subpass{};
    copy_subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
    copy_subpass.colorAttachmentCount = 1;
    copy_subpass.pColorAttachments = &copy_color_reference;
    VkSubpassDependency copy_dependencies[2]{};
    copy_dependencies[0].srcSubpass = VK_SUBPASS_EXTERNAL;
    copy_dependencies[0].dstSubpass = 0;
    copy_dependencies[0].srcStageMask = VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT |
                                        VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
    copy_dependencies[0].dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
    copy_dependencies[0].srcAccessMask = VK_ACCESS_SHADER_READ_BIT;
    copy_dependencies[0].dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_READ_BIT |
                                         VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
    copy_dependencies[1].srcSubpass = 0;
    copy_dependencies[1].dstSubpass = VK_SUBPASS_EXTERNAL;
    copy_dependencies[1].srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
    copy_dependencies[1].dstStageMask = VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT |
                                        VK_PIPELINE_STAGE_TRANSFER_BIT;
    copy_dependencies[1].srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
    copy_dependencies[1].dstAccessMask = VK_ACCESS_SHADER_READ_BIT |
                                         VK_ACCESS_TRANSFER_READ_BIT;
    VkRenderPassCreateInfo copy_pass_info{};
    copy_pass_info.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
    copy_pass_info.attachmentCount = 1;
    copy_pass_info.pAttachments = &copy_attachment;
    copy_pass_info.subpassCount = 1;
    copy_pass_info.pSubpasses = &copy_subpass;
    copy_pass_info.dependencyCount = 2;
    copy_pass_info.pDependencies = copy_dependencies;
    result = vkCreateRenderPass(
        device, &copy_pass_info, nullptr, &resources.mixed_copy_render_pass);
    if (result != VK_SUCCESS) return vk_fail("vkCreateRenderPass(mixed Copy/Convert)", result, error);
    VkFramebufferCreateInfo copy_framebuffer_info{};
    copy_framebuffer_info.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
    copy_framebuffer_info.renderPass = resources.mixed_copy_render_pass;
    copy_framebuffer_info.attachmentCount = 1;
    copy_framebuffer_info.pAttachments = &output_view;
    copy_framebuffer_info.width = output_width;
    copy_framebuffer_info.height = output_height;
    copy_framebuffer_info.layers = 1;
    result = vkCreateFramebuffer(device, &copy_framebuffer_info, nullptr,
                                 &resources.mixed_copy_framebuffer);
    if (result != VK_SUCCESS) return vk_fail("vkCreateFramebuffer(mixed Copy/Convert)", result, error);

    for (size_t resource_index = 0;
         resource_index < rendered_draw_indices.size(); ++resource_index) {
        const size_t draw_index = rendered_draw_indices[resource_index];
        CapturedVulkanDraw resource_draw = draws[draw_index];
        if (remap_trailing_msaa_to_single[draw_index]) {
            // The guest switches the same target back to 4x for a
            // depth/stencil-only draw. When a later 1x draw consumes that
            // state, replay it at sample zero in the resolved 1x attachment.
            resource_draw.raster.sample_count = 1;
        }
        const VkRenderPass pass = resource_draw.raster.sample_count == 4
            ? resources.mixed_msaa_render_pass
            : resources.mixed_single_render_pass;
        draw_resource_indices[draw_index] = resource_index;
        if (!create_draw_resources(resource_draw, draw_index, texture_cache,
                                   memory_properties, device, pass,
                                   0,
                                   pipeline_cache,
                                   geometry_shader_enabled, sampler_capabilities,
                                   &resources.draws[resource_index], error,
                                   linear_rgba8_intermediate &&
                                       draws[draw_index].raster.color_format ==
                                           CapturedColorTargetFormat::Rgba8Gamma)) {
            return false;
        }
    }
    if (alias_transfer_needed) {
        CapturedVulkanDraw alias_transfer_draw{};
        alias_transfer_draw.raster = draws[first_single_sample_draw].raster;
        alias_transfer_draw.raster.scissor_x0 = 0;
        alias_transfer_draw.raster.scissor_y0 = 0;
        alias_transfer_draw.raster.scissor_x1 = target.width;
        alias_transfer_draw.raster.scissor_y1 = target.height;
        alias_transfer_draw.raster.scissor_has_area = true;
        alias_transfer_draw.raster.color_write_mask = 0xFu;
        alias_transfer_draw.raster.depth_test_enabled = false;
        alias_transfer_draw.raster.depth_write_enabled = false;
        alias_transfer_draw.raster.stencil_test_enabled = false;
        alias_transfer_draw.raster.depth_control = 0;
        alias_transfer_draw.raster.blend_control_0 = 0x00010001u;
        alias_transfer_draw.vertex_shader_spirv =
            copy.edram_alias_transfer_vertex_shader_spirv;
        alias_transfer_draw.pixel_shader_spirv =
            copy.edram_alias_transfer_pixel_shader_spirv;
        alias_transfer_draw.topology = PrimitiveTopology::TriangleList;
        alias_transfer_draw.auto_index = true;
        alias_transfer_draw.index_count = 3;
        CapturedVulkanTexture alias_source{};
        alias_source.fetch_constant_index = 0;
        alias_source.width = target.width;
        alias_source.height = target.height;
        alias_source.format = CapturedVulkanTexture::Format::Rgba16Unorm;
        alias_source.external_image_view = resources.mixed_msaa_color.view;
        alias_source.sampling.clamps = {
            TextureClamp::ClampToEdge, TextureClamp::ClampToEdge,
            TextureClamp::ClampToEdge};
        alias_source.sampling.mag_filter = TextureFilter::Point;
        alias_source.sampling.min_filter = TextureFilter::Point;
        alias_source.sampling.mip_filter = TextureFilter::Point;
        alias_source.sampling.anisotropy = TextureAnisotropy::Disabled;
        alias_source.sampling.border_color = TextureBorderColor::AbgrBlack;
        alias_source.sampling.border_alpha_known = true;
        alias_transfer_draw.textures.push_back(std::move(alias_source));
        if (!create_draw_resources(
                alias_transfer_draw, std::numeric_limits<size_t>::max(), nullptr,
                memory_properties, device, resources.mixed_single_render_pass, 0,
                pipeline_cache, geometry_shader_enabled, sampler_capabilities,
                &resources.edram_alias_draw, error)) {
            return false;
        }
    }
    CapturedVulkanDraw copy_draw = make_copy_resolve_draw(
        copy, source_width, source_height, output_width, output_height, true);
    if (!create_draw_resources(copy_draw, std::numeric_limits<size_t>::max(), nullptr,
                               memory_properties, device,
                               resources.mixed_copy_render_pass, 0, pipeline_cache,
                               geometry_shader_enabled &&
                                   !copy_draw.geometry_shader_spirv.empty(),
                               sampler_capabilities, &resources.copy_draw, error)) {
        return false;
    }
    VkDescriptorImageInfo source_info{resources.copy_draw.textures[0].sampler,
                                      resources.mixed_color.view,
                                      VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL};
    VkWriteDescriptorSet source_write{};
    source_write.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
    source_write.dstSet = resources.copy_draw.descriptor_sets[1];
    source_write.dstBinding = 0;
    source_write.descriptorCount = 1;
    source_write.descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
    source_write.pImageInfo = &source_info;
    vkUpdateDescriptorSets(device, 1, &source_write, 0, nullptr);
    resources.destroy_image(resources.copy_draw.textures[0].image);
    resources.destroy_buffer(resources.copy_draw.textures[0].upload);

    VkDeviceSize readback_size = 0;
    if (output_readback) {
        const uint64_t pixel_count = static_cast<uint64_t>(output_width) * output_height;
        if (pixel_count > std::numeric_limits<size_t>::max() / sizeof(uint32_t) ||
            pixel_count > std::numeric_limits<VkDeviceSize>::max() / sizeof(uint32_t)) {
            return fail("captured output extent is too large for Vulkan readback", error);
        }
        readback_size = static_cast<VkDeviceSize>(pixel_count * sizeof(uint32_t));
        if (!create_buffer(memory_properties, device, readback_size,
                           VK_BUFFER_USAGE_TRANSFER_DST_BIT, nullptr,
                           &resources.output_readback, error)) {
            return false;
        }
    }
    VkCommandPoolCreateInfo pool_info{};
    pool_info.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
    pool_info.flags = VK_COMMAND_POOL_CREATE_TRANSIENT_BIT;
    pool_info.queueFamilyIndex = queue_family_index;
    result = vkCreateCommandPool(device, &pool_info, nullptr, &resources.command_pool);
    if (result != VK_SUCCESS) return vk_fail("vkCreateCommandPool(mixed frame)", result, error);
    VkCommandBufferAllocateInfo command_info{};
    command_info.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    command_info.commandPool = resources.command_pool;
    command_info.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    command_info.commandBufferCount = 1;
    VkCommandBuffer command = VK_NULL_HANDLE;
    result = vkAllocateCommandBuffers(device, &command_info, &command);
    if (result != VK_SUCCESS) return vk_fail("vkAllocateCommandBuffers(mixed frame)", result, error);
    VkCommandBufferBeginInfo begin_info{};
    begin_info.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    begin_info.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    result = vkBeginCommandBuffer(command, &begin_info);
    if (result != VK_SUCCESS) return vk_fail("vkBeginCommandBuffer(mixed frame)", result, error);
    if (resources.draw_visibility_query_pool) {
        vkCmdResetQueryPool(command, resources.draw_visibility_query_pool, 0,
                            static_cast<uint32_t>(draws.size()));
    }

    std::vector<VkBufferMemoryBarrier> host_barriers;
    host_barriers.reserve(draws.size() * 8);
    for (const DrawResources& draw : resources.draws) {
        const std::array<std::pair<const BufferResource*, VkAccessFlags>, 4> buffers = {{
            {&draw.vertices, VK_ACCESS_VERTEX_ATTRIBUTE_READ_BIT},
            {&draw.indices, VK_ACCESS_INDEX_READ_BIT},
            {&draw.vertex_constants, VK_ACCESS_UNIFORM_READ_BIT},
            {&draw.pixel_constants, VK_ACCESS_UNIFORM_READ_BIT},
        }};
        const auto add_host_barrier = [&](const BufferResource* buffer,
                                          VkAccessFlags access) {
            if (!buffer->buffer) return;
            VkBufferMemoryBarrier barrier{};
            barrier.sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER;
            barrier.srcAccessMask = VK_ACCESS_HOST_WRITE_BIT;
            barrier.dstAccessMask = access;
            barrier.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            barrier.buffer = buffer->buffer;
            barrier.size = VK_WHOLE_SIZE;
            host_barriers.push_back(barrier);
        };
        for (const auto& [buffer, access] : buffers) add_host_barrier(buffer, access);
        for (const DrawTextureResources& texture : draw.textures) {
            if (!texture.guest_copy_source && !texture.external_image)
                add_host_barrier(&texture.upload, VK_ACCESS_TRANSFER_READ_BIT);
        }
    }
    if (resources.edram_alias_draw.pipeline) {
        const std::array<std::pair<const BufferResource*, VkAccessFlags>, 4>
            buffers = {{{&resources.edram_alias_draw.vertices,
                         VK_ACCESS_VERTEX_ATTRIBUTE_READ_BIT},
                        {&resources.edram_alias_draw.indices,
                         VK_ACCESS_INDEX_READ_BIT},
                        {&resources.edram_alias_draw.vertex_constants,
                         VK_ACCESS_UNIFORM_READ_BIT},
                        {&resources.edram_alias_draw.pixel_constants,
                         VK_ACCESS_UNIFORM_READ_BIT}}};
        for (const auto& [buffer, destination_access] : buffers) {
            if (!buffer->buffer) continue;
            VkBufferMemoryBarrier barrier{};
            barrier.sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER;
            barrier.srcAccessMask = VK_ACCESS_HOST_WRITE_BIT;
            barrier.dstAccessMask = destination_access;
            barrier.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            barrier.buffer = buffer->buffer;
            barrier.size = VK_WHOLE_SIZE;
            host_barriers.push_back(barrier);
        }
    }
    if (resources.edram_clear_draw.pipeline) {
        const std::array<std::pair<const BufferResource*, VkAccessFlags>, 4>
            buffers = {{{&resources.edram_clear_draw.vertices,
                         VK_ACCESS_VERTEX_ATTRIBUTE_READ_BIT},
                        {&resources.edram_clear_draw.indices,
                         VK_ACCESS_INDEX_READ_BIT},
                        {&resources.edram_clear_draw.vertex_constants,
                         VK_ACCESS_UNIFORM_READ_BIT},
                        {&resources.edram_clear_draw.pixel_constants,
                         VK_ACCESS_UNIFORM_READ_BIT}}};
        for (const auto& [buffer, destination_access] : buffers) {
            if (!buffer->buffer) continue;
            VkBufferMemoryBarrier barrier{};
            barrier.sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER;
            barrier.srcAccessMask = VK_ACCESS_HOST_WRITE_BIT;
            barrier.dstAccessMask = destination_access;
            barrier.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            barrier.buffer = buffer->buffer;
            barrier.size = VK_WHOLE_SIZE;
            host_barriers.push_back(barrier);
        }
    }
    vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_HOST_BIT,
                         VK_PIPELINE_STAGE_VERTEX_INPUT_BIT |
                             VK_PIPELINE_STAGE_VERTEX_SHADER_BIT |
                             VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT |
                             VK_PIPELINE_STAGE_TRANSFER_BIT,
                         0, 0, nullptr, static_cast<uint32_t>(host_barriers.size()),
                         host_barriers.data(), 0, nullptr);
    for (size_t i = 0; i < resources.draws.size(); ++i) {
        const DrawResources& draw = resources.draws[i];
        for (const DrawTextureResources& texture : draw.textures) {
            if (texture.guest_copy_source || texture.external_image) continue;
            VkImageMemoryBarrier to_upload{};
            to_upload.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
            to_upload.srcAccessMask = texture.upload_old_layout ==
                    VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL
                ? VK_ACCESS_SHADER_READ_BIT : 0;
            to_upload.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
            to_upload.oldLayout = texture.upload_old_layout;
            to_upload.newLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
            to_upload.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            to_upload.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            to_upload.image = texture.image.image;
            to_upload.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            to_upload.subresourceRange.levelCount = 1;
            to_upload.subresourceRange.layerCount = 1;
            vkCmdPipelineBarrier(command,
                                 texture.upload_old_layout ==
                                         VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL
                                     ? VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT
                                     : VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                                 VK_PIPELINE_STAGE_TRANSFER_BIT, 0,
                                 0, nullptr, 0, nullptr, 1, &to_upload);
            VkBufferImageCopy upload{};
            upload.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            upload.imageSubresource.layerCount = 1;
            upload.imageExtent = {texture.width, texture.height, 1};
            vkCmdCopyBufferToImage(command, texture.upload.buffer, texture.image.image,
                                   VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &upload);
            VkImageMemoryBarrier to_sample = to_upload;
            to_sample.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
            to_sample.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
            to_sample.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
            to_sample.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
            vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TRANSFER_BIT,
                                 VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, 0,
                                 0, nullptr, 0, nullptr, 1, &to_sample);
        }
    }

    const auto scaled_edge = [](uint32_t edge, uint32_t source_extent,
                                uint32_t output_extent, bool round_up) {
        const uint64_t numerator = static_cast<uint64_t>(edge) * output_extent;
        const uint64_t quotient = numerator / source_extent;
        return static_cast<uint32_t>(quotient +
            (round_up && numerator % source_extent != 0 ? 1u : 0u));
    };
    const auto record_draw = [&](size_t index) {
        const CapturedVulkanDraw& source = draws[index];
        const size_t resource_index = draw_resource_indices[index];
        if (resource_index == std::numeric_limits<size_t>::max()) return;
        const DrawResources& draw = resources.draws[resource_index];
        VkViewport viewport{};
        if (source.raster.clip_disabled_window_coordinates) {
            viewport.x = 0.0f;
            viewport.y = 0.0f;
            viewport.width = static_cast<float>(target.width);
            viewport.height = static_cast<float>(target.height);
        } else if (source.raster.viewport_width != 0.0f &&
            source.raster.viewport_height != 0.0f && source.raster.width &&
            source.raster.height) {
            const float scale_x = static_cast<float>(target.width) /
                                  source.raster.width;
            const float scale_y = static_cast<float>(target.height) /
                                  source.raster.height;
            viewport.x = source.raster.viewport_x * scale_x;
            viewport.y = source.raster.viewport_y * scale_y;
            viewport.width = source.raster.viewport_width * scale_x;
            viewport.height = source.raster.viewport_height * scale_y;
        } else {
            viewport.x = 0.0f;
            viewport.y = source.raster.viewport_y_flipped
                             ? static_cast<float>(target.height) : 0.0f;
            viewport.width = static_cast<float>(target.width);
            viewport.height = source.raster.viewport_y_flipped
                                  ? -static_cast<float>(target.height)
                                  : static_cast<float>(target.height);
        }
        viewport.minDepth = 0.0f;
        viewport.maxDepth = 1.0f;
        const uint32_t x0 = scaled_edge(source.raster.scissor_x0,
                                        source.raster.width, target.width, false);
        const uint32_t y0 = scaled_edge(source.raster.scissor_y0,
                                        source.raster.height, target.height, false);
        const uint32_t x1 = scaled_edge(source.raster.scissor_x1,
                                        source.raster.width, target.width, true);
        const uint32_t y1 = scaled_edge(source.raster.scissor_y1,
                                        source.raster.height, target.height, true);
        VkRect2D scissor{{static_cast<int32_t>(x0), static_cast<int32_t>(y0)},
                         {x1 - x0, y1 - y0}};
        const VkDeviceSize vertex_offset = 0;
        vkCmdBindPipeline(command, VK_PIPELINE_BIND_POINT_GRAPHICS, draw.pipeline);
        vkCmdSetViewport(command, 0, 1, &viewport);
        vkCmdSetScissor(command, 0, 1, &scissor);
        if (draw.vertices.buffer) {
            vkCmdBindVertexBuffers(command, 0, 1, &draw.vertices.buffer, &vertex_offset);
        }
        vkCmdBindDescriptorSets(command, VK_PIPELINE_BIND_POINT_GRAPHICS,
                                draw.pipeline_layout, 0, 2,
                                draw.descriptor_sets, 0, nullptr);
        if (source.auto_index) {
            vkCmdDraw(command, source.index_count, 1, 0, 0);
        } else {
            vkCmdBindIndexBuffer(command, draw.indices.buffer, 0, VK_INDEX_TYPE_UINT16);
            vkCmdDrawIndexed(command, source.index_count, 1, 0, 0, 0);
        }
    };

    const auto record_alias_transfer = [&] {
        const DrawResources& draw = resources.edram_alias_draw;
        VkViewport viewport{};
        viewport.width = static_cast<float>(target.width);
        viewport.height = static_cast<float>(target.height);
        viewport.minDepth = 0.0f;
        viewport.maxDepth = 1.0f;
        VkRect2D scissor{{0, 0}, {target.width, target.height}};
        vkCmdBindPipeline(command, VK_PIPELINE_BIND_POINT_GRAPHICS,
                          draw.pipeline);
        vkCmdSetViewport(command, 0, 1, &viewport);
        vkCmdSetScissor(command, 0, 1, &scissor);
        vkCmdBindDescriptorSets(command, VK_PIPELINE_BIND_POINT_GRAPHICS,
                                draw.pipeline_layout, 0, 2,
                                draw.descriptor_sets, 0, nullptr);
        vkCmdDraw(command, 3, 1, 0, 0);
    };

    const uint32_t msaa_attachment_count = 2u +
        (needs_msaa_depth ? 1u : 0u) + (resolve_depth_stencil ? 1u : 0u);
    std::vector<VkClearValue> msaa_clears(msaa_attachment_count);
    msaa_clears[0].color.float32[3] = 1.0f;
    if (needs_msaa_depth) {
        msaa_clears[2].depthStencil = {1.0f, 0};
    }
    VkRenderPassBeginInfo msaa_begin{};
    msaa_begin.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
    msaa_begin.renderPass = resources.mixed_msaa_render_pass;
    msaa_begin.framebuffer = resources.mixed_msaa_framebuffer;
    msaa_begin.renderArea.extent = {target.width, target.height};
    msaa_begin.clearValueCount = static_cast<uint32_t>(msaa_clears.size());
    msaa_begin.pClearValues = msaa_clears.data();
    vkCmdBeginRenderPass(command, &msaa_begin, VK_SUBPASS_CONTENTS_INLINE);
    for (size_t i = 0; i < first_single_sample_draw; ++i) {
        record_draw_with_visibility_query(
            resources, command, static_cast<uint32_t>(i), [&] { record_draw(i); });
    }
    vkCmdEndRenderPass(command);

    VkImageMemoryBarrier resolve_to_single{};
    resolve_to_single.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
    resolve_to_single.srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
    resolve_to_single.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_READ_BIT |
                                      VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
    resolve_to_single.oldLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    resolve_to_single.newLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    resolve_to_single.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    resolve_to_single.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    resolve_to_single.image = resources.mixed_color.image;
    resolve_to_single.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    resolve_to_single.subresourceRange.levelCount = 1;
    resolve_to_single.subresourceRange.layerCount = 1;
    vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
                         VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, 0,
                         0, nullptr, 0, nullptr, 1, &resolve_to_single);

    VkImageMemoryBarrier msaa_to_sample{};
    msaa_to_sample.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
    msaa_to_sample.srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
    msaa_to_sample.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
    msaa_to_sample.oldLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    msaa_to_sample.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
    msaa_to_sample.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    msaa_to_sample.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    msaa_to_sample.image = resources.mixed_msaa_color.image;
    msaa_to_sample.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    msaa_to_sample.subresourceRange.levelCount = 1;
    msaa_to_sample.subresourceRange.layerCount = 1;
    if (alias_transfer_needed) {
        vkCmdPipelineBarrier(command,
                             VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
                             VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, 0, 0,
                             nullptr, 0, nullptr, 1, &msaa_to_sample);
    }

    std::vector<VkClearValue> single_clears(single_attachments.size());
    if (needs_single_depth) {
        single_clears[single_depth_reference.attachment].depthStencil = {1.0f, 0};
    }
    VkRenderPassBeginInfo single_begin{};
    single_begin.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
    single_begin.renderPass = resources.mixed_single_render_pass;
    single_begin.framebuffer = resources.mixed_single_framebuffer;
    single_begin.renderArea.extent = {target.width, target.height};
    single_begin.clearValueCount = static_cast<uint32_t>(single_clears.size());
    single_begin.pClearValues = single_clears.data();
    vkCmdBeginRenderPass(command, &single_begin, VK_SUBPASS_CONTENTS_INLINE);
    if (alias_transfer_needed) record_alias_transfer();
    for (size_t i = first_single_sample_draw; i < draws.size(); ++i) {
        if (draws[i].raster.sample_count == 1 ||
            remap_trailing_msaa_to_single[i]) {
            record_draw_with_visibility_query(
                resources, command, static_cast<uint32_t>(i),
                [&] { record_draw(i); });
        }
    }
    vkCmdEndRenderPass(command);

    VkImageMemoryBarrier source_to_sample{};
    source_to_sample.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
    source_to_sample.srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
    source_to_sample.oldLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    source_to_sample.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    source_to_sample.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    source_to_sample.image = resources.mixed_color.image;
    source_to_sample.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    source_to_sample.subresourceRange.levelCount = 1;
    source_to_sample.subresourceRange.layerCount = 1;
    if (source_readback_ready) {
        source_to_sample.dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT;
        source_to_sample.newLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
        vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
                             VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, nullptr,
                             0, nullptr, 1, &source_to_sample);
        VkBufferImageCopy source_copy{};
        source_copy.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        source_copy.imageSubresource.layerCount = 1;
        source_copy.imageExtent = {source_width, source_height, 1};
        vkCmdCopyImageToBuffer(command, resources.mixed_color.image,
                               VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                               resources.source_readback.buffer, 1, &source_copy);
        VkBufferMemoryBarrier source_to_host{};
        source_to_host.sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER;
        source_to_host.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
        source_to_host.dstAccessMask = VK_ACCESS_HOST_READ_BIT;
        source_to_host.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        source_to_host.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        source_to_host.buffer = resources.source_readback.buffer;
        source_to_host.size = resources.source_readback_size;
        vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TRANSFER_BIT,
                             VK_PIPELINE_STAGE_HOST_BIT, 0, 0, nullptr,
                             1, &source_to_host, 0, nullptr);
        source_to_sample.srcAccessMask = VK_ACCESS_TRANSFER_READ_BIT;
        source_to_sample.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
        source_to_sample.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
        source_to_sample.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
        vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TRANSFER_BIT,
                             VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, 0, 0, nullptr,
                             0, nullptr, 1, &source_to_sample);
    } else {
        source_to_sample.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
        source_to_sample.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
        vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
                             VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, 0, 0, nullptr,
                             0, nullptr, 1, &source_to_sample);
    }

    VkImageMemoryBarrier output_to_color{};
    output_to_color.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
    output_to_color.srcAccessMask =
        output_written_before ? VK_ACCESS_SHADER_READ_BIT : 0;
    output_to_color.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_READ_BIT |
                                   VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
    output_to_color.oldLayout = output_written_before
                                    ? VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL
                                    : VK_IMAGE_LAYOUT_UNDEFINED;
    output_to_color.newLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    output_to_color.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    output_to_color.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    output_to_color.image = output_image;
    output_to_color.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    output_to_color.subresourceRange.levelCount = 1;
    output_to_color.subresourceRange.layerCount = 1;
    vkCmdPipelineBarrier(command,
                         output_written_before
                             ? VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT
                             : VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                         VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, 0, 0,
                         nullptr, 0, nullptr, 1, &output_to_color);

    VkRenderPassBeginInfo copy_begin{};
    copy_begin.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
    copy_begin.renderPass = resources.mixed_copy_render_pass;
    copy_begin.framebuffer = resources.mixed_copy_framebuffer;
    copy_begin.renderArea.extent = {output_width, output_height};
    vkCmdBeginRenderPass(command, &copy_begin, VK_SUBPASS_CONTENTS_INLINE);
    record_copy_resolve_draw(command, resources.copy_draw, copy,
                             output_width, output_height);
    vkCmdEndRenderPass(command);

    VkImageMemoryBarrier output_to_read{};
    output_to_read.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
    output_to_read.srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
    output_to_read.dstAccessMask = output_readback ? VK_ACCESS_TRANSFER_READ_BIT
                                                  : VK_ACCESS_SHADER_READ_BIT;
    output_to_read.oldLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    output_to_read.newLayout = output_readback ? VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL
                                               : VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
    output_to_read.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    output_to_read.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    output_to_read.image = output_image;
    output_to_read.subresourceRange = output_to_color.subresourceRange;
    vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
                         output_readback ? VK_PIPELINE_STAGE_TRANSFER_BIT
                                         : VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT,
                         0, 0, nullptr, 0, nullptr, 1, &output_to_read);
    if (output_readback) {
        VkBufferImageCopy readback_copy{};
        readback_copy.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        readback_copy.imageSubresource.layerCount = 1;
        readback_copy.imageExtent = {output_width, output_height, 1};
        vkCmdCopyImageToBuffer(command, output_image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                               resources.output_readback.buffer, 1, &readback_copy);
        VkBufferMemoryBarrier readback_to_host{};
        readback_to_host.sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER;
        readback_to_host.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
        readback_to_host.dstAccessMask = VK_ACCESS_HOST_READ_BIT;
        readback_to_host.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        readback_to_host.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        readback_to_host.buffer = resources.output_readback.buffer;
        readback_to_host.size = readback_size;
        vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TRANSFER_BIT,
                             VK_PIPELINE_STAGE_HOST_BIT, 0,
                             0, nullptr, 1, &readback_to_host, 0, nullptr);
        VkImageMemoryBarrier output_back_to_sample = output_to_read;
        output_back_to_sample.srcAccessMask = VK_ACCESS_TRANSFER_READ_BIT;
        output_back_to_sample.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
        output_back_to_sample.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
        output_back_to_sample.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
        vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TRANSFER_BIT,
                             VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, 0,
                             0, nullptr, 0, nullptr, 1, &output_back_to_sample);
    }
    result = vkEndCommandBuffer(command);
    if (result != VK_SUCCESS) return vk_fail("vkEndCommandBuffer(mixed frame)", result, error);
    VkFenceCreateInfo fence_info{};
    fence_info.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
    result = vkCreateFence(device, &fence_info, nullptr, &resources.completion_fence);
    if (result != VK_SUCCESS) return vk_fail("vkCreateFence(mixed frame)", result, error);
    VkSubmitInfo submit{};
    submit.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
    submit.commandBufferCount = 1;
    submit.pCommandBuffers = &command;
    result = vkQueueSubmit(queue, 1, &submit, resources.completion_fence);
    if (result != VK_SUCCESS) return vk_fail("vkQueueSubmit(mixed frame)", result, error);
    resources.submitted = true;
    finish_texture_cache_frame(texture_cache);
    if (output_readback || source_readback_ready || draw_visibility ||
        !texture_cache) {
        if (!wait_for_frame(resources, error)) return false;
    } else {
        texture_cache->in_flight.push_back(std::move(resources_owner));
        texture_cache->in_flight_frame_count.fetch_add(1, std::memory_order_release);
    }
    collect_draw_visibility_queries(resources, draw_visibility);
    if (output_readback) {
        void* mapped = nullptr;
        result = vkMapMemory(device, resources.output_readback.memory, 0,
                             VK_WHOLE_SIZE, 0, &mapped);
        if (result != VK_SUCCESS) return vk_fail("vkMapMemory(mixed readback)", result, error);
        if ((resources.output_readback.memory_flags &
             VK_MEMORY_PROPERTY_HOST_COHERENT_BIT) == 0) {
            VkMappedMemoryRange range{};
            range.sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE;
            range.memory = resources.output_readback.memory;
            range.size = VK_WHOLE_SIZE;
            result = vkInvalidateMappedMemoryRanges(device, 1, &range);
            if (result != VK_SUCCESS) {
                vkUnmapMemory(device, resources.output_readback.memory);
                return vk_fail("vkInvalidateMappedMemoryRanges(mixed readback)", result, error);
            }
        }
        output_readback->resize(static_cast<size_t>(output_width) * output_height);
        std::memcpy(output_readback->data(), mapped, static_cast<size_t>(readback_size));
        vkUnmapMemory(device, resources.output_readback.memory);
    }
    if (source_readback_ready) {
        void* mapped = nullptr;
        result = vkMapMemory(device, resources.source_readback.memory, 0,
                             VK_WHOLE_SIZE, 0, &mapped);
        if (result != VK_SUCCESS) {
            source_readback_unsupported(
                source_readback, "mixed source buffer map failed with VkResult " +
                                     std::to_string(result));
        } else if ((resources.source_readback.memory_flags &
             VK_MEMORY_PROPERTY_HOST_COHERENT_BIT) == 0) {
            VkMappedMemoryRange range{};
            range.sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE;
            range.memory = resources.source_readback.memory;
            range.size = VK_WHOLE_SIZE;
            result = vkInvalidateMappedMemoryRanges(device, 1, &range);
            if (result != VK_SUCCESS) {
                vkUnmapMemory(device, resources.source_readback.memory);
                source_readback_unsupported(
                    source_readback,
                    "mixed source buffer invalidate failed with VkResult " +
                        std::to_string(result));
                mapped = nullptr;
            }
        }
        if (mapped) {
            source_readback->bytes.resize(
                static_cast<size_t>(resources.source_readback_size));
            std::memcpy(source_readback->bytes.data(), mapped,
                        static_cast<size_t>(resources.source_readback_size));
            vkUnmapMemory(device, resources.source_readback.memory);
            source_readback->status = CapturedVulkanSourceReadback::Status::Captured;
            source_readback->reason.clear();
        }
    }
    if (error) error->clear();
    return true;
}

}  // namespace

std::string describe_captured_vulkan_operations(
    const std::vector<CapturedVulkanOperation>& operations) {
    std::ostringstream message;
    constexpr size_t kMaxLoggedOperations = 64;
    const size_t count = std::min(operations.size(), kMaxLoggedOperations);
    const auto append_draw_raster = [&](const CapturedRasterState& raster) {
        message << ",raster={color_base=0x" << std::hex
                << raster.color_base_tiles << ",depth_base=0x"
                << raster.depth_base_tiles << std::dec
                << ",guest_format=" << raster.guest_color_format
                << ",color_format=" << static_cast<uint32_t>(raster.color_format)
                << ",depth_format=" << static_cast<uint32_t>(raster.depth_format)
                << ",extent=" << raster.width << 'x' << raster.height
                << ",pitch=" << raster.surface_pitch
                << ",samples=" << raster.sample_count
                << ",depth_only=" << raster.depth_only
                << ",color_mask=0x" << std::hex << raster.color_write_mask
                << std::dec << ",depth_test=" << raster.depth_test_enabled
                << ",depth_write=" << raster.depth_write_enabled
                << ",stencil_test=" << raster.stencil_test_enabled
                << ",depth_control=0x" << std::hex << raster.depth_control
                << ",stencil_refmask=0x" << raster.stencil_refmask << std::dec
                << ",scissor=" << raster.scissor_has_area << '['
                << raster.scissor_x0 << ',' << raster.scissor_y0 << ".."
                << raster.scissor_x1 << ',' << raster.scissor_y1 << "]}";
    };
    const auto append_draw_registers =
        [&](const CapturedVulkanOperation& operation) {
            const CapturedRasterRegisters& registers = operation.draw_registers;
            message << ",draw_registers={valid_mask=0x" << std::hex
                    << operation.draw_register_valid_mask << ",surface=0x"
                    << registers.surface_info << ",color=0x"
                    << registers.color_info << ",depth=0x"
                    << registers.depth_info << ",mode=0x"
                    << registers.mode_control << ",depth_control=0x"
                    << registers.depth_control << ",color_mask=0x"
                    << registers.color_mask << ",stencil_refmask=0x"
                    << registers.stencil_refmask << std::dec
                    << ",stencil_refmask_valid="
                    << registers.stencil_refmask_valid << ",screen_scissor=[0x"
                    << std::hex << registers.screen_scissor_tl << ",0x"
                    << registers.screen_scissor_br << "],window_scissor=[0x"
                    << registers.window_scissor_tl << ",0x"
                    << registers.window_scissor_br << "]}" << std::dec;
        };
    for (size_t i = 0; i < count; ++i) {
        if (i) message << ';';
        const CapturedVulkanOperation& operation = operations[i];
        switch (operation.type) {
            case CapturedVulkanOperation::Type::Draw:
                message << "draw(packet=" << operation.packet_index
                        << ",index=" << operation.draw_index;
                if (operation.draw_registers_ready) {
                    append_draw_registers(operation);
                }
                if (operation.draw_raster_ready) {
                    append_draw_raster(operation.draw_raster);
                }
                message << ')';
                break;
            case CapturedVulkanOperation::Type::CopyConvert:
                message << "copy(packet=" << operation.packet_index
                        << ",source=" << operation.source_width << 'x'
                        << operation.source_height << ",source_regs=0x" << std::hex
                        << operation.source_surface_info << "/0x"
                        << operation.source_color_info << "/0x"
                        << operation.source_depth_info << "/0x"
                        << operation.source_mode_control << ",destination=0x"
                        << operation.copy_state.destination_base << std::dec << ','
                        << operation.copy_state.destination_pitch << 'x'
                        << operation.copy_state.destination_height << ",format="
                        << operation.copy_state.destination_format << '/'
                        << operation.copy_state.destination_number_format
                        << ",endian=" << operation.copy_state.destination_endian
                        << ",exp_bias=" << operation.copy_state.destination_exp_bias
                        << ",samples=" << operation.copy_state.sample_select
                        << ",clear=" << operation.copy_state.color_clear_enable
                        << '/' << operation.copy_state.depth_clear_enable
                        << ",clear_registers={ready:"
                        << operation.copy.clear_values_ready << ",color:0x"
                        << std::hex << operation.copy.color_clear
                        << ",color_lo:0x" << operation.copy.color_clear_lo
                        << ",depth:0x" << operation.copy.depth_clear << std::dec
                        << "},source_target={ready:"
                        << operation.source_raster_ready;
                if (operation.source_raster_ready) {
                    message << ",extent=" << operation.source_raster.width << 'x'
                            << operation.source_raster.height << ",samples="
                            << operation.source_raster.sample_count
                            << ",color_base=0x" << std::hex
                            << operation.source_raster.color_base_tiles
                            << ",depth_base=0x"
                            << operation.source_raster.depth_base_tiles << std::dec
                            << ",guest_format="
                            << operation.source_raster.guest_color_format;
                }
                message << "},swap_rb="
                        << operation.copy_state.destination_swap_red_blue
                        << ",shaders="
                        << (operation.copy_shaders_ready ? "prepared" : "missing")
                        << ",source_geometry="
                        << (operation.copy.source_geometry_ready ? "captured" : "missing");
                if (operation.copy.source_geometry_ready) {
                    message << ",topology="
                            << static_cast<uint32_t>(
                                   operation.copy.source_geometry.topology)
                            << ",indices="
                            << operation.copy.source_geometry.index_count
                            << ",auto_index="
                            << operation.copy.source_geometry.auto_index
                            << ",vertex_bytes="
                            << operation.copy.source_geometry.vertices.size()
                            << ",index_bytes="
                            << operation.copy.source_geometry.indices.size();
                }
                message
                        << ')';
                break;
            case CapturedVulkanOperation::Type::UnresolvedDraw:
                message << "unresolved(packet=" << operation.packet_index;
                if (operation.draw_registers_ready) {
                    append_draw_registers(operation);
                }
                if (operation.draw_raster_ready) {
                    append_draw_raster(operation.draw_raster);
                }
                message << ')';
                break;
            case CapturedVulkanOperation::Type::UnresolvedCopy:
                message << "unresolved-copy(packet=" << operation.packet_index << ')';
                break;
        }
    }
    if (count < operations.size()) {
        message << "; omitted operations=" << operations.size() - count;
    }
    return message.str();
}

struct CapturedVulkanTextureCache::Impl {
    TextureCacheState state;
};

struct CapturedVulkanTextureCacheAccess {
    static TextureCacheState& get(CapturedVulkanTextureCache& cache) {
        if (!cache.impl_) cache.impl_ = std::make_unique<CapturedVulkanTextureCache::Impl>();
        return cache.impl_->state;
    }
};

CapturedVulkanTextureCache::CapturedVulkanTextureCache() = default;

CapturedVulkanTextureCache::~CapturedVulkanTextureCache() {
    clear();
}

void CapturedVulkanTextureCache::clear() {
    if (impl_) clear_texture_cache(&impl_->state);
}

bool CapturedVulkanTextureCache::wait_for_guest_memory_coherency(
    std::string* error) {
    if (error) error->clear();
    return !impl_ || !has_in_flight_frames() ||
           wait_for_all_frames(&impl_->state, error);
}

bool CapturedVulkanTextureCache::has_in_flight_frames() const noexcept {
    return impl_ &&
           impl_->state.in_flight_frame_count.load(std::memory_order_acquire) != 0;
}

size_t CapturedVulkanTextureCache::size() const {
    return impl_ ? impl_->state.textures.size() : 0;
}

size_t CapturedVulkanTextureCache::cached_pipeline_count() const {
    return impl_ ? impl_->state.graphics_pipelines.size() : 0;
}

size_t CapturedVulkanTextureCache::cached_sampler_count() const {
    return impl_ ? impl_->state.samplers.size() : 0;
}

size_t CapturedVulkanTextureCache::cached_draw_buffer_count() const {
    if (!impl_) return 0;
    size_t count = 0;
    for (const auto& entry : impl_->state.draw_buffers) {
        const CachedDrawBuffers& buffers = entry.second;
        for (const auto* slots : {&buffers.vertices, &buffers.indices,
                                  &buffers.vertex_constants,
                                  &buffers.pixel_constants}) {
            for (const BufferResource& buffer : *slots) {
                if (buffer.buffer) ++count;
            }
        }
    }
    return count;
}

size_t CapturedVulkanTextureCache::cached_descriptor_layout_count() const {
    return impl_ ? impl_->state.descriptor_layouts.size() : 0;
}

size_t CapturedVulkanTextureCache::descriptor_layout_cache_hits() const {
    return impl_ ? impl_->state.descriptor_layout_cache_hits : 0;
}

size_t CapturedVulkanTextureCache::cached_guest_copy_image_count() const {
    return impl_ ? impl_->state.guest_copy_images.size() : 0;
}

size_t CapturedVulkanTextureCache::cached_guest_edram_target_count() const {
    return impl_ ? impl_->state.edram_targets.size() : 0;
}

bool submit_captured_vulkan_frame(
    VkPhysicalDevice physical_device,
    VkDevice device,
    VkQueue queue,
    uint32_t queue_family_index,
    VkImage output_image,
    VkImageView output_view,
    bool output_written_before,
    uint32_t output_width,
    uint32_t output_height,
    const std::vector<CapturedVulkanDraw>& draws,
    std::string* error,
    std::vector<uint32_t>* output_readback,
    bool geometry_shader_enabled,
    const CapturedVulkanCopy* copy,
    bool depth_stencil_resolve_enabled,
    CapturedVulkanSamplerCapabilities sampler_capabilities,
    VkPipelineCache pipeline_cache,
    CapturedVulkanTextureCache* texture_cache,
    CapturedVulkanSourceReadback* source_readback,
    std::vector<CapturedVulkanDrawVisibility>* draw_visibility,
    const std::vector<CapturedVulkanOperation>* operations,
    bool preserve_edram_target) {
    if (output_readback) output_readback->clear();
    if (draw_visibility) draw_visibility->assign(draws.size(), {});
    if (source_readback) {
        *source_readback = {};
        source_readback_unsupported(
            source_readback, "no captured Copy/Convert source target in this frame");
    }
    if (!physical_device || !device || !queue || !output_image || !output_view ||
        !output_width || !output_height || draws.empty() || queue_family_index == UINT32_MAX) {
        return fail("invalid captured Vulkan frame target or draw list", error);
    }
    if (output_width > static_cast<uint32_t>(std::numeric_limits<int32_t>::max()) ||
        output_height > static_cast<uint32_t>(std::numeric_limits<int32_t>::max())) {
        return fail("Vulkan presenter extent exceeds signed scissor bounds", error);
    }
    if (operations &&
        !validate_captured_operation_stream(*operations, draws.size(), error)) {
        append_captured_operation_stream(error, operations);
        return false;
    }
    const CapturedRasterState& frame_target = draws.front().raster;
    const bool linear_rgba8_intermediate = copy &&
        frame_has_gamma_color_target(draws);
    const VkFormat frame_target_format = captured_color_format(
        frame_target.color_format, linear_rgba8_intermediate);
    for (size_t draw_index = 1; draw_index < draws.size(); ++draw_index) {
        const CapturedRasterState& raster = draws[draw_index].raster;
        const bool depth_only_view =
            is_captured_gamma_depth_only_view_alias(frame_target, raster);
        const bool target_layout_changed =
            raster.color_base_tiles != frame_target.color_base_tiles ||
            (!depth_only_view &&
             raster.guest_color_format != frame_target.guest_color_format) ||
            raster.depth_base_tiles != frame_target.depth_base_tiles ||
            raster.width != frame_target.width ||
            raster.height != frame_target.height ||
            (copy && !depth_only_view &&
             captured_color_format(raster.color_format,
                                           linear_rgba8_intermediate) !=
                         frame_target_format) ||
            raster.depth_format != frame_target.depth_format ||
            (raster.surface_pitch != frame_target.surface_pitch &&
             raster.sample_count == frame_target.sample_count);
        if (target_layout_changed) {
            std::ostringstream message;
            message << "captured Vulkan submission changes Xenos target layout at draw "
                    << draw_index << " (color_base=" << frame_target.color_base_tiles
                    << " -> " << raster.color_base_tiles << ", depth_base="
                    << frame_target.depth_base_tiles << " -> "
                    << raster.depth_base_tiles << ", extent=" << frame_target.width
                    << 'x' << frame_target.height << " -> " << raster.width << 'x'
                    << raster.height << ", color_format="
                    << static_cast<unsigned>(frame_target.color_format) << " -> "
                    << static_cast<unsigned>(raster.color_format)
                    << ", guest_color_format=" << frame_target.guest_color_format
                    << " -> " << raster.guest_color_format << ", pitch="
                    << frame_target.surface_pitch << " -> " << raster.surface_pitch
                    << "); ordered target layouts=";
            constexpr size_t kMaxLoggedTargetLayouts = 64;
            const size_t logged_layout_count =
                std::min(draws.size(), kMaxLoggedTargetLayouts);
            for (size_t layout_index = 0; layout_index < logged_layout_count;
                 ++layout_index) {
                if (layout_index) message << ';';
                const CapturedRasterState& layout = draws[layout_index].raster;
                message << "draw" << layout_index << "{extent=" << layout.width
                        << 'x' << layout.height << ",samples="
                        << layout.sample_count << ",color_base="
                        << layout.color_base_tiles << ",depth_base="
                        << layout.depth_base_tiles << ",color_format="
                        << static_cast<unsigned>(layout.color_format)
                        << ",guest_color_format=" << layout.guest_color_format
                        << ",depth_format="
                        << static_cast<unsigned>(layout.depth_format)
                        << ",pitch=" << layout.surface_pitch << '}';
            }
            if (logged_layout_count < draws.size()) {
                message << "; omitted target layouts="
                        << draws.size() - logged_layout_count;
            }
            CapturedEdramSampleAddress previous_color_sample{};
            CapturedEdramSampleAddress next_color_sample{};
            if (captured_xenos_edram_sample_address(
                    frame_target, false, 0, 0, 0, &previous_color_sample,
                    nullptr) &&
                captured_xenos_edram_sample_address(
                    raster, false, 0, 0, 0, &next_color_sample, nullptr) &&
                previous_color_sample.byte_offset ==
                    next_color_sample.byte_offset) {
                message << "; Xenos color sample 0 aliases at EDRAM byte offset "
                        << previous_color_sample.byte_offset;
            }
            message << "; ordered Xenos EDRAM target persistence and resolve are not implemented";
            if (operations) {
                message << "; ordered operations="
                        << describe_captured_vulkan_operations(*operations);
            }
            return fail(message.str(), error);
        }
    }
    VkPhysicalDeviceMemoryProperties memory_properties{};
    vkGetPhysicalDeviceMemoryProperties(physical_device, &memory_properties);
    TextureCacheState* texture_cache_state = nullptr;
    if (texture_cache) {
        texture_cache_state = &CapturedVulkanTextureCacheAccess::get(*texture_cache);
        if (!begin_texture_cache_frame(texture_cache_state, device, error)) return false;
    }
    const bool persistent_edram_target =
        preserve_edram_target && texture_cache_state;
    if (persistent_edram_target && !copy && output_readback) {
        return fail("persistent EDRAM-only segment cannot provide presenter readback",
                    error);
    }
    auto resources_owner = std::make_unique<FrameResources>();
    FrameResources& resources = *resources_owner;
    resources.device = device;
    resources.queue = queue;
    resources.upload_slot = texture_cache_state ? texture_cache_state->upload_slot : 0;
    prepare_draw_visibility_queries(device, draws.size(), resources,
                                    draw_visibility);
    resources.draws.resize(draws.size());
    const uint32_t samples = draws.front().raster.sample_count;
    const VkSampleCountFlagBits raster_samples = sample_count_flag(samples);
    if (raster_samples == VkSampleCountFlagBits{}) {
        return fail("captured sample count is outside the Vulkan 1.1 subset", error);
    }
    const bool mixed_sample_counts = std::any_of(
        draws.begin() + 1, draws.end(), [samples](const CapturedVulkanDraw& draw) {
            return draw.raster.sample_count != samples;
        });
    const bool single_sample_copy = !mixed_sample_counts && samples == 1;
    const VkFormat copy_destination_format = copy
        ? captured_copy_destination_format(copy->state.destination_format)
        : VK_FORMAT_A2B10G10R10_UNORM_PACK32;
    if (copy) {
        const CapturedCopyState& state = copy->state;
        const bool common_valid =
            (mixed_sample_counts || samples == 1 || samples == 4) &&
            state.source_select == 0 &&
            state.command == CapturedCopyCommand::Convert &&
            state.destination_pitch == output_width &&
            state.destination_height == output_height &&
            copy_destination_format != VK_FORMAT_UNDEFINED &&
            !copy->vertex_shader_spirv.empty();
        const bool rgba8_valid = state.destination_format == 6 &&
            state.sample_select == 0 && state.destination_swap_red_blue &&
            (single_sample_copy
                 ? !copy->single_sample_pixel_shader_spirv.empty()
                 : !copy->pixel_shader_spirv.empty()) &&
            (!copy->source_gamma ||
             (single_sample_copy
                  ? !copy->gamma_single_sample_pixel_shader_spirv.empty()
                  : !copy->gamma_pixel_shader_spirv.empty()));
        const bool all_sample_u16_valid = state.destination_format == 26 &&
            !mixed_sample_counts && samples == 4 && state.sample_select == 6 &&
            state.destination_number_format == 2 &&
            state.destination_endian == 1 && state.destination_exp_bias == 11 &&
            state.color_clear_enable && state.depth_clear_enable &&
            !state.destination_swap_red_blue && !copy->source_gamma &&
            !copy->pixel_shader_spirv.empty();
        const bool sample0_rg16f_valid = state.destination_format == 31 &&
            !mixed_sample_counts && (samples == 1 || samples == 4) &&
            state.sample_select == 0 && state.destination_number_format == 7 &&
            state.destination_endian == 2 && state.destination_exp_bias == 0 &&
            state.color_clear_enable && !state.depth_clear_enable &&
            !state.destination_swap_red_blue && !copy->source_gamma &&
            (single_sample_copy
                 ? !copy->single_sample_pixel_shader_spirv.empty()
                 : !copy->pixel_shader_spirv.empty());
        if (!common_valid ||
            !(rgba8_valid || all_sample_u16_valid || sample0_rg16f_valid)) {
            return fail("captured Copy/Convert is outside the implemented format-6, format-26, and format-31 Vulkan subsets",
                        error);
        }
        if (state.color_clear_enable || state.depth_clear_enable) {
            if (!copy->clear_values_ready ||
                (state.color_clear_enable &&
                 (copy->color_clear != 0 || copy->color_clear_lo != 0)) ||
                (state.depth_clear_enable &&
                 copy->depth_clear != 0xFFFFFF00u)) {
                return fail("captured Copy/Convert clear values are incomplete or outside the verified zero-color/D24S8-one subset",
                            error);
            }
            if (!geometry_shader_enabled || !copy->source_geometry_ready ||
                copy->source_geometry.vertex_shader_spirv.empty() ||
                copy->source_geometry.geometry_shader_spirv.empty() ||
                copy->edram_clear_pixel_shader_spirv.empty()) {
                std::ostringstream message;
                message << "captured Copy/Convert EDRAM clear requires its captured rectangle geometry and translated clear shader (geometry_feature="
                        << geometry_shader_enabled << ",captured_geometry="
                        << copy->source_geometry_ready << ",vertex_shader="
                        << !copy->source_geometry.vertex_shader_spirv.empty()
                        << ",rectangle_shader="
                        << !copy->source_geometry.geometry_shader_spirv.empty()
                        << ",clear_shader="
                        << !copy->edram_clear_pixel_shader_spirv.empty() << ')';
                return fail(message.str(), error);
            }
            if (state.depth_clear_enable &&
                copy->source_geometry.raster.depth_format !=
                    CapturedDepthTargetFormat::D24S8) {
                return fail("captured Copy/Convert depth clear requires the supported D24S8 source target",
                            error);
            }
        }
        if (state.destination_format != 6) {
            VkFormatProperties destination_properties{};
            vkGetPhysicalDeviceFormatProperties(
                physical_device, copy_destination_format,
                &destination_properties);
            constexpr VkFormatFeatureFlags required_features =
                VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT |
                VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT |
                VK_FORMAT_FEATURE_TRANSFER_SRC_BIT;
            if ((destination_properties.optimalTilingFeatures &
                 required_features) != required_features) {
                return fail("captured intermediate Copy/Convert destination format is not color-attachable and sampleable on this Vulkan device",
                            error);
            }
        }
        if (state.destination_format == 26u) {
            VkFormatProperties sampled_properties{};
            vkGetPhysicalDeviceFormatProperties(
                physical_device, VK_FORMAT_R16G16B16A16_UNORM,
                &sampled_properties);
            if ((sampled_properties.optimalTilingFeatures &
                 VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT) == 0) {
                return fail("captured format-26 Copy/Convert sampling requires R16G16B16A16_UNORM image-view support",
                            error);
            }
        }
    }
    if (linear_rgba8_intermediate) {
        VkFormatProperties format_properties{};
        vkGetPhysicalDeviceFormatProperties(
            physical_device, VK_FORMAT_R16G16B16A16_UNORM,
            &format_properties);
        constexpr VkFormatFeatureFlags required_features =
            VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT |
            VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT |
            VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BLEND_BIT;
        if ((format_properties.optimalTilingFeatures & required_features) !=
            required_features) {
            return fail("captured RGBA8_GAMMA target requires sampled, blendable R16G16B16A16_UNORM",
                        error);
        }
    }
    if (mixed_sample_counts) {
        if (!copy) {
            return fail("mixed captured sample counts require a captured Copy/Convert target",
                        error);
        }
        if (copy->state.destination_format != 6) {
            return fail("mixed sample-count Copy/Convert currently supports only format 6",
                        error);
        }
        const bool submitted = submit_mixed_sample_copy_frame(
            physical_device, device, queue, queue_family_index, output_image,
            output_view, output_written_before, output_width, output_height,
            draws, error, output_readback, geometry_shader_enabled, *copy,
            depth_stencil_resolve_enabled, sampler_capabilities, pipeline_cache,
            texture_cache_state, source_readback, draw_visibility);
        if (!submitted) append_captured_operation_stream(error, operations);
        return submitted;
    }
    CachedGuestCopyImage* cached_copy_image = nullptr;
    const bool persistent_copy_target = copy && texture_cache_state &&
        (copy->state.destination_format != 6 || copy->retain_destination);
    VkImage copy_output_image = output_image;
    VkImageView copy_output_view = output_view;
    bool copy_output_written_before = output_written_before;
    if (persistent_copy_target) {
        if (!acquire_guest_copy_image(
                texture_cache_state, memory_properties, device, copy->state,
                output_width, output_height, copy_destination_format,
                &cached_copy_image, error)) {
            return false;
        }
        copy_output_image = cached_copy_image->image.image;
        copy_output_view = cached_copy_image->image.view;
        copy_output_written_before = cached_copy_image->initialized;
    }
    const uint32_t source_width = copy && copy->source_width
                                      ? copy->source_width
                                      : frame_target.width;
    const uint32_t source_height = copy && copy->source_height
                                       ? copy->source_height
                                       : frame_target.height;
    const VkFormat raster_color_format =
        copy || persistent_edram_target
            ? captured_color_format(frame_target.color_format,
                                    linear_rgba8_intermediate)
            : VK_FORMAT_A2B10G10R10_UNORM_PACK32;
    if (copy &&
        (raster_color_format == VK_FORMAT_UNDEFINED ||
         source_width != frame_target.width || source_height != frame_target.height ||
         std::any_of(draws.begin(), draws.end(), [&](const CapturedVulkanDraw& draw) {
             const bool depth_only_view =
                 is_captured_gamma_depth_only_view_alias(frame_target,
                                                        draw.raster);
             return draw.raster.width != frame_target.width ||
                    draw.raster.height != frame_target.height ||
                    (!depth_only_view &&
                     draw.raster.guest_color_format !=
                         frame_target.guest_color_format) ||
                    (!depth_only_view &&
                     captured_color_format(draw.raster.color_format,
                                           linear_rgba8_intermediate) !=
                         raster_color_format);
         }))) {
        std::ostringstream message;
        message << "captured Copy/Convert source " << source_width << 'x'
                << source_height << " does not match raster target 0 "
                << frame_target.width << 'x' << frame_target.height
                << "; draws=" << draws.size();
        for (size_t i = 0; i < draws.size(); ++i) {
            const CapturedRasterState& raster = draws[i].raster;
            message << " draw" << i << "={extent=" << raster.width << 'x'
                    << raster.height << ",pitch=" << raster.surface_pitch
                    << ",samples=" << raster.sample_count << ",color_base=0x"
                    << std::hex << raster.color_base_tiles << std::dec
                    << ",color_format="
                    << static_cast<unsigned>(raster.color_format)
                    << ",depth_base=0x" << std::hex << raster.depth_base_tiles
                    << std::dec << '}';
        }
        std::string diagnostic = message.str();
        append_captured_operation_stream(&diagnostic, operations);
        return fail(diagnostic, error);
    }
    const uint32_t raster_width = copy ? source_width : output_width;
    const uint32_t raster_height = copy ? source_height : output_height;
    const bool needs_depth = std::any_of(
        draws.begin(), draws.end(), [](const CapturedVulkanDraw& draw) {
            return draw.raster.depth_test_enabled ||
                   draw.raster.depth_write_enabled ||
                   draw.raster.stencil_test_enabled;
        }) || (copy && copy->state.depth_clear_enable);
    bool source_readback_ready = copy && prepare_source_readback_buffer(
        memory_properties, device, source_width, source_height,
        raster_color_format, samples, samples > 1, resources, source_readback);
    if (source_readback_ready && samples > 1) {
        std::string optional_error;
        if (!create_render_attachment(
                memory_properties, device, source_width, source_height,
                raster_color_format,
                VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT |
                    VK_IMAGE_USAGE_TRANSFER_DST_BIT |
                    VK_IMAGE_USAGE_TRANSFER_SRC_BIT,
                VK_IMAGE_ASPECT_COLOR_BIT, VK_SAMPLE_COUNT_1_BIT,
                &resources.source_resolve, &optional_error)) {
            resources.destroy_image(resources.source_resolve);
            source_readback_ready = false;
            source_readback_unsupported(
                source_readback, "MSAA source resolve image unavailable: " +
                                     optional_error);
        }
    }
    for (size_t draw_index = 0; draw_index < draws.size(); ++draw_index) {
        const CapturedVulkanDraw& draw = draws[draw_index];
        if (draw.topology == PrimitiveTopology::RectangleList &&
            !geometry_shader_enabled) {
            return fail("captured rectangle-list draw requires an enabled Vulkan geometry shader",
                        error);
        }
        const CapturedRasterState& raster = draw.raster;
        if (raster.sample_count != samples) {
            const CapturedRasterState& frame_raster = draws.front().raster;
            std::ostringstream message;
            message << "captured Vulkan draw " << draw_index << " sample count "
                    << raster.sample_count << " differs from frame sample count "
                    << samples << "; draw 0 surface={color_base_tiles="
                    << frame_raster.color_base_tiles << ",depth_base_tiles="
                    << frame_raster.depth_base_tiles << ",pitch="
                    << frame_raster.surface_pitch << ",color_format="
                    << static_cast<uint32_t>(frame_raster.color_format)
                    << ",extent=" << frame_raster.width << 'x'
                    << frame_raster.height << "}; draw " << draw_index
                    << " surface={color_base_tiles=" << raster.color_base_tiles
                    << ",depth_base_tiles=" << raster.depth_base_tiles
                    << ",pitch=" << raster.surface_pitch << ",color_format="
                    << static_cast<uint32_t>(raster.color_format)
                    << ",extent=" << raster.width << 'x' << raster.height << '}';
            return fail(message.str(), error);
        }
        if (raster.width == 0 || raster.height == 0) {
            std::ostringstream message;
            message << "captured Vulkan draw " << draw_index
                    << " has zero raster extent " << raster.width << 'x'
                    << raster.height;
            return fail(message.str(), error);
        }
        if (raster.scissor_x1 > raster.width || raster.scissor_y1 > raster.height ||
            raster.scissor_x0 > raster.scissor_x1 || raster.scissor_y0 > raster.scissor_y1) {
            std::ostringstream message;
            message << "captured Vulkan draw " << draw_index << " scissor ["
                    << raster.scissor_x0 << ',' << raster.scissor_y0 << ','
                    << raster.scissor_x1 << ',' << raster.scissor_y1
                    << "] is outside raster extent " << raster.width << 'x'
                    << raster.height;
            return fail(message.str(), error);
        }
    }

    CachedEdramTarget* cached_edram_target = nullptr;
    if (persistent_edram_target) {
        if (!acquire_edram_target(
                texture_cache_state, memory_properties, device, frame_target,
                raster_color_format, needs_depth, &cached_edram_target, error)) {
            return false;
        }
        resources.multisample_color = cached_edram_target->color;
        resources.multisample_color.borrowed = true;
        if (needs_depth) {
            resources.depth = cached_edram_target->depth;
            resources.depth.borrowed = true;
        }
    }

    if (samples > 1 || copy || persistent_edram_target) {
        const VkImageUsageFlags raster_color_usage =
            VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT |
            (copy ? VK_IMAGE_USAGE_SAMPLED_BIT : 0);
        if (source_readback_ready && !resources.multisample_color.image) {
            std::string optional_error;
            if (!create_render_attachment(
                    memory_properties, device, raster_width, raster_height,
                    raster_color_format,
                    raster_color_usage | VK_IMAGE_USAGE_TRANSFER_SRC_BIT,
                    VK_IMAGE_ASPECT_COLOR_BIT, raster_samples,
                    &resources.multisample_color, &optional_error)) {
                resources.destroy_image(resources.multisample_color);
                source_readback_ready = false;
                source_readback_unsupported(
                    source_readback, "MSAA source transfer readback unavailable: " +
                                         optional_error);
            }
        }
        if (!resources.multisample_color.image &&
            !create_render_attachment(
                memory_properties, device, raster_width, raster_height,
                raster_color_format, raster_color_usage, VK_IMAGE_ASPECT_COLOR_BIT,
                raster_samples, &resources.multisample_color, error)) {
            return false;
        }
    }

    VkDeviceSize output_readback_size = 0;
    if (output_readback) {
        const uint64_t pixel_count = static_cast<uint64_t>(output_width) * output_height;
        const uint32_t output_bytes_per_pixel = color_format_bytes(
            copy ? copy_destination_format : VK_FORMAT_A2B10G10R10_UNORM_PACK32);
        if (!output_bytes_per_pixel ||
            pixel_count > std::numeric_limits<size_t>::max() /
                              output_bytes_per_pixel ||
            pixel_count > std::numeric_limits<VkDeviceSize>::max() /
                              output_bytes_per_pixel) {
            return fail("captured output extent is too large for Vulkan readback", error);
        }
        output_readback_size = static_cast<VkDeviceSize>(
            pixel_count * output_bytes_per_pixel);
        if (!create_buffer(memory_properties, device, output_readback_size,
                           VK_BUFFER_USAGE_TRANSFER_DST_BIT, nullptr,
                           &resources.output_readback, error)) {
            return false;
        }
    }
    if (needs_depth && !resources.depth.image &&
        !create_render_attachment(
            memory_properties, device, raster_width, raster_height,
            VK_FORMAT_D24_UNORM_S8_UINT,
            VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT,
            VK_IMAGE_ASPECT_DEPTH_BIT | VK_IMAGE_ASPECT_STENCIL_BIT,
            raster_samples, &resources.depth, error)) {
        return false;
    }

    std::vector<VkAttachmentDescription> attachments;
    VkAttachmentDescription color_attachment{};
    color_attachment.format = raster_color_format;
    color_attachment.samples = raster_samples;
    const bool preserve_color = persistent_edram_target &&
        cached_edram_target->color_initialized;
    color_attachment.loadOp = preserve_color ? VK_ATTACHMENT_LOAD_OP_LOAD
                                              : VK_ATTACHMENT_LOAD_OP_CLEAR;
    color_attachment.storeOp = persistent_edram_target || samples == 1 || copy
        ? VK_ATTACHMENT_STORE_OP_STORE
        : VK_ATTACHMENT_STORE_OP_DONT_CARE;
    color_attachment.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    color_attachment.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    color_attachment.initialLayout = persistent_edram_target ||
            (samples == 1 && !copy)
        ? VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL
        : VK_IMAGE_LAYOUT_UNDEFINED;
    color_attachment.finalLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    attachments.push_back(color_attachment);
    VkAttachmentReference color_reference{0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};

    VkAttachmentReference depth_reference{};
    if (needs_depth) {
        depth_reference.attachment = static_cast<uint32_t>(attachments.size());
        depth_reference.layout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
        VkAttachmentDescription depth_attachment{};
        depth_attachment.format = VK_FORMAT_D24_UNORM_S8_UINT;
        depth_attachment.samples = raster_samples;
        const bool preserve_depth = persistent_edram_target &&
            cached_edram_target->depth_initialized;
        depth_attachment.loadOp = preserve_depth ? VK_ATTACHMENT_LOAD_OP_LOAD
                                                  : VK_ATTACHMENT_LOAD_OP_CLEAR;
        depth_attachment.storeOp = persistent_edram_target
            ? VK_ATTACHMENT_STORE_OP_STORE : VK_ATTACHMENT_STORE_OP_DONT_CARE;
        depth_attachment.stencilLoadOp = preserve_depth
            ? VK_ATTACHMENT_LOAD_OP_LOAD : VK_ATTACHMENT_LOAD_OP_CLEAR;
        depth_attachment.stencilStoreOp = persistent_edram_target
            ? VK_ATTACHMENT_STORE_OP_STORE : VK_ATTACHMENT_STORE_OP_DONT_CARE;
        depth_attachment.initialLayout = preserve_depth
            ? VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL
            : VK_IMAGE_LAYOUT_UNDEFINED;
        depth_attachment.finalLayout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
        attachments.push_back(depth_attachment);
    }

    VkAttachmentReference resolve_reference{};
    if (samples > 1 && !copy && !persistent_edram_target) {
        resolve_reference.attachment = static_cast<uint32_t>(attachments.size());
        resolve_reference.layout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        VkAttachmentDescription resolve_attachment{};
        resolve_attachment.format = VK_FORMAT_A2B10G10R10_UNORM_PACK32;
        resolve_attachment.samples = VK_SAMPLE_COUNT_1_BIT;
        resolve_attachment.loadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
        resolve_attachment.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
        resolve_attachment.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
        resolve_attachment.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        resolve_attachment.initialLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        resolve_attachment.finalLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        attachments.push_back(resolve_attachment);
    }

    VkSubpassDescription subpass{};
    subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
    subpass.colorAttachmentCount = 1;
    subpass.pColorAttachments = &color_reference;
    subpass.pDepthStencilAttachment = needs_depth ? &depth_reference : nullptr;
    subpass.pResolveAttachments =
        samples > 1 && !copy && !persistent_edram_target
            ? &resolve_reference
            : nullptr;
    VkRenderPassCreateInfo render_pass_info{};
    render_pass_info.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
    render_pass_info.attachmentCount = static_cast<uint32_t>(attachments.size());
    render_pass_info.pAttachments = attachments.data();
    render_pass_info.subpassCount = 1;
    render_pass_info.pSubpasses = &subpass;
    VkResult result = vkCreateRenderPass(device, &render_pass_info, nullptr,
                                         &resources.render_pass);
    if (result != VK_SUCCESS) return vk_fail("vkCreateRenderPass", result, error);

    VkFramebufferCreateInfo framebuffer_info{};
    framebuffer_info.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
    framebuffer_info.renderPass = resources.render_pass;
    std::vector<VkImageView> framebuffer_views;
    framebuffer_views.push_back(persistent_edram_target || copy || samples > 1
                                    ? resources.multisample_color.view
                                    : output_view);
    if (needs_depth) framebuffer_views.push_back(resources.depth.view);
    if (samples > 1 && !copy && !persistent_edram_target)
        framebuffer_views.push_back(output_view);
    framebuffer_info.attachmentCount = static_cast<uint32_t>(framebuffer_views.size());
    framebuffer_info.pAttachments = framebuffer_views.data();
    framebuffer_info.width = raster_width;
    framebuffer_info.height = raster_height;
    framebuffer_info.layers = 1;
    result = vkCreateFramebuffer(device, &framebuffer_info, nullptr, &resources.framebuffer);
    if (result != VK_SUCCESS) return vk_fail("vkCreateFramebuffer", result, error);

    if (copy) {
        VkAttachmentDescription copy_attachment{};
        copy_attachment.format = copy_destination_format;
        copy_attachment.samples = VK_SAMPLE_COUNT_1_BIT;
        copy_attachment.loadOp = copy_output_written_before
            ? VK_ATTACHMENT_LOAD_OP_LOAD : VK_ATTACHMENT_LOAD_OP_DONT_CARE;
        copy_attachment.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
        copy_attachment.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
        copy_attachment.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        copy_attachment.initialLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        copy_attachment.finalLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        VkAttachmentReference copy_color_reference{0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};
        VkSubpassDescription copy_subpass{};
        copy_subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
        copy_subpass.colorAttachmentCount = 1;
        copy_subpass.pColorAttachments = &copy_color_reference;
        VkRenderPassCreateInfo copy_pass_info{};
        copy_pass_info.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
        copy_pass_info.attachmentCount = 1;
        copy_pass_info.pAttachments = &copy_attachment;
        copy_pass_info.subpassCount = 1;
        copy_pass_info.pSubpasses = &copy_subpass;
        result = vkCreateRenderPass(device, &copy_pass_info, nullptr,
                                    &resources.copy_render_pass);
        if (result != VK_SUCCESS) return vk_fail("vkCreateRenderPass(copy)", result, error);

        VkFramebufferCreateInfo copy_framebuffer_info{};
        copy_framebuffer_info.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
        copy_framebuffer_info.renderPass = resources.copy_render_pass;
        copy_framebuffer_info.attachmentCount = 1;
        copy_framebuffer_info.pAttachments = &copy_output_view;
        copy_framebuffer_info.width = output_width;
        copy_framebuffer_info.height = output_height;
        copy_framebuffer_info.layers = 1;
        result = vkCreateFramebuffer(device, &copy_framebuffer_info, nullptr,
                                     &resources.copy_framebuffer);
        if (result != VK_SUCCESS) return vk_fail("vkCreateFramebuffer(copy)", result, error);

        CapturedVulkanDraw copy_draw = make_copy_resolve_draw(
            *copy, source_width, source_height, output_width, output_height,
            single_sample_copy);
        if (!create_draw_resources(copy_draw, std::numeric_limits<size_t>::max(), nullptr,
                                   memory_properties, device,
                                   resources.copy_render_pass, 0, pipeline_cache,
                                   geometry_shader_enabled &&
                                       !copy_draw.geometry_shader_spirv.empty(),
                                   sampler_capabilities, &resources.copy_draw, error)) {
            return false;
        }
        VkDescriptorImageInfo copy_image_info{
            resources.copy_draw.textures[0].sampler, resources.multisample_color.view,
            VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL};
        VkWriteDescriptorSet copy_image_write{};
        copy_image_write.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
        copy_image_write.dstSet = resources.copy_draw.descriptor_sets[1];
        copy_image_write.dstBinding = 0;
        copy_image_write.descriptorCount = 1;
        copy_image_write.descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
        copy_image_write.pImageInfo = &copy_image_info;
        vkUpdateDescriptorSets(device, 1, &copy_image_write, 0, nullptr);
        resources.destroy_image(resources.copy_draw.textures[0].image);
        resources.destroy_buffer(resources.copy_draw.textures[0].upload);
    }

    if (copy &&
        (copy->state.color_clear_enable || copy->state.depth_clear_enable)) {
        if (!create_edram_clear_render_pass(
                device, raster_color_format, raster_samples, needs_depth,
                &resources.edram_clear_render_pass, error)) {
            return false;
        }
        const std::array<VkImageView, 2> clear_views = {
            resources.multisample_color.view, resources.depth.view};
        VkFramebufferCreateInfo clear_framebuffer_info{};
        clear_framebuffer_info.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
        clear_framebuffer_info.renderPass = resources.edram_clear_render_pass;
        clear_framebuffer_info.attachmentCount = needs_depth ? 2u : 1u;
        clear_framebuffer_info.pAttachments = clear_views.data();
        clear_framebuffer_info.width = raster_width;
        clear_framebuffer_info.height = raster_height;
        clear_framebuffer_info.layers = 1;
        result = vkCreateFramebuffer(device, &clear_framebuffer_info, nullptr,
                                     &resources.edram_clear_framebuffer);
        if (result != VK_SUCCESS) {
            return vk_fail("vkCreateFramebuffer(EDRAM clear)", result, error);
        }

        CapturedVulkanDraw clear_draw = copy->source_geometry;
        clear_draw.pixel_shader_spirv = copy->edram_clear_pixel_shader_spirv;
        clear_draw.pixel_shader_spirv_linear_target.clear();
        clear_draw.raster.sample_count = samples;
        clear_draw.raster.color_write_mask =
            copy->state.color_clear_enable ? 0xFu : 0u;
        clear_draw.raster.blend_control_0 = 0x00010001u;
        clear_draw.raster.depth_test_enabled =
            copy->state.depth_clear_enable;
        clear_draw.raster.depth_write_enabled =
            copy->state.depth_clear_enable;
        clear_draw.raster.stencil_test_enabled =
            copy->state.depth_clear_enable;
        if (copy->state.depth_clear_enable) {
            // D24S8 clear 0xFFFFFF00 is depth 1.0 and stencil 0. The pipeline
            // writes those values only where the captured Copy rectangle lands.
            clear_draw.raster.depth_control = (7u << 4) | (7u << 8) |
                                               (2u << 14);
            clear_draw.raster.stencil_refmask = 0x00FFFF00u;
        } else {
            clear_draw.raster.depth_control = 0;
            clear_draw.raster.stencil_refmask = 0;
        }
        if (!create_draw_resources(
                clear_draw, std::numeric_limits<size_t>::max(),
                texture_cache_state, memory_properties, device,
                resources.edram_clear_render_pass, 0, pipeline_cache,
                geometry_shader_enabled, sampler_capabilities,
                &resources.edram_clear_draw, error)) {
            return false;
        }
    }

    // Pipelines need the render pass compatibility key, so create them after
    // the pass exists. Resource upload and descriptor creation are independent.
    for (size_t i = 0; i < draws.size(); ++i) {
        DrawResources& draw = resources.draws[i];
        const uint64_t pass_key = regular_render_pass_key(
            raster_color_format, raster_samples, needs_depth, copy != nullptr);
        // Recreate just the graphics pipeline with this frame's render pass.
        if (!create_draw_resources(draws[i], i, texture_cache_state,
                                   memory_properties, device, resources.render_pass,
                                   pass_key,
                                   pipeline_cache,
                                   geometry_shader_enabled, sampler_capabilities,
                                   &draw, error,
                                   linear_rgba8_intermediate &&
                                       draws[i].raster.color_format ==
                                           CapturedColorTargetFormat::Rgba8Gamma)) {
            return false;
        }
    }

    VkCommandPoolCreateInfo pool_info{};
    pool_info.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
    pool_info.flags = VK_COMMAND_POOL_CREATE_TRANSIENT_BIT;
    pool_info.queueFamilyIndex = queue_family_index;
    result = vkCreateCommandPool(device, &pool_info, nullptr, &resources.command_pool);
    if (result != VK_SUCCESS) return vk_fail("vkCreateCommandPool", result, error);
    VkCommandBufferAllocateInfo command_info{};
    command_info.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    command_info.commandPool = resources.command_pool;
    command_info.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    command_info.commandBufferCount = 1;
    VkCommandBuffer command = VK_NULL_HANDLE;
    result = vkAllocateCommandBuffers(device, &command_info, &command);
    if (result != VK_SUCCESS) return vk_fail("vkAllocateCommandBuffers", result, error);
    VkCommandBufferBeginInfo begin_info{};
    begin_info.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    begin_info.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    result = vkBeginCommandBuffer(command, &begin_info);
    if (result != VK_SUCCESS) return vk_fail("vkBeginCommandBuffer", result, error);
    if (resources.draw_visibility_query_pool) {
        vkCmdResetQueryPool(command, resources.draw_visibility_query_pool, 0,
                            static_cast<uint32_t>(draws.size()));
    }

    std::vector<VkBufferMemoryBarrier> host_barriers;
    host_barriers.reserve(draws.size() * 8);
    for (const DrawResources& draw : resources.draws) {
        const std::array<std::pair<const BufferResource*, VkAccessFlags>, 4> buffers = {{
            {&draw.vertices, VK_ACCESS_VERTEX_ATTRIBUTE_READ_BIT},
            {&draw.indices, VK_ACCESS_INDEX_READ_BIT},
            {&draw.vertex_constants, VK_ACCESS_UNIFORM_READ_BIT},
            {&draw.pixel_constants, VK_ACCESS_UNIFORM_READ_BIT},
        }};
        const auto add_host_barrier = [&](const BufferResource* buffer,
                                          VkAccessFlags destination_access) {
            if (!buffer->buffer) return;
            VkBufferMemoryBarrier barrier{};
            barrier.sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER;
            barrier.srcAccessMask = VK_ACCESS_HOST_WRITE_BIT;
            barrier.dstAccessMask = destination_access;
            barrier.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            barrier.buffer = buffer->buffer;
            barrier.size = VK_WHOLE_SIZE;
            host_barriers.push_back(barrier);
        };
        for (const auto& [buffer, access] : buffers) add_host_barrier(buffer, access);
        for (const DrawTextureResources& texture : draw.textures) {
            if (!texture.guest_copy_source && !texture.external_image)
                add_host_barrier(&texture.upload, VK_ACCESS_TRANSFER_READ_BIT);
        }
    }
    if (resources.edram_clear_draw.pipeline) {
        const std::array<std::pair<const BufferResource*, VkAccessFlags>, 4>
            buffers = {{{&resources.edram_clear_draw.vertices,
                         VK_ACCESS_VERTEX_ATTRIBUTE_READ_BIT},
                        {&resources.edram_clear_draw.indices,
                         VK_ACCESS_INDEX_READ_BIT},
                        {&resources.edram_clear_draw.vertex_constants,
                         VK_ACCESS_UNIFORM_READ_BIT},
                        {&resources.edram_clear_draw.pixel_constants,
                         VK_ACCESS_UNIFORM_READ_BIT}}};
        for (const auto& [buffer, destination_access] : buffers) {
            if (!buffer->buffer) continue;
            VkBufferMemoryBarrier barrier{};
            barrier.sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER;
            barrier.srcAccessMask = VK_ACCESS_HOST_WRITE_BIT;
            barrier.dstAccessMask = destination_access;
            barrier.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            barrier.buffer = buffer->buffer;
            barrier.size = VK_WHOLE_SIZE;
            host_barriers.push_back(barrier);
        }
    }
    vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_HOST_BIT,
                         VK_PIPELINE_STAGE_VERTEX_INPUT_BIT |
                             VK_PIPELINE_STAGE_VERTEX_SHADER_BIT |
                             VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT |
                             VK_PIPELINE_STAGE_TRANSFER_BIT,
                         0, 0, nullptr, static_cast<uint32_t>(host_barriers.size()),
                         host_barriers.data(), 0, nullptr);

    const bool writes_output_image = copy || !persistent_edram_target;
    VkImageMemoryBarrier output_to_color{};
    output_to_color.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
    output_to_color.srcAccessMask = copy_output_written_before
        ? VK_ACCESS_SHADER_READ_BIT : 0;
    output_to_color.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_READ_BIT |
                                   VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
    output_to_color.oldLayout = copy_output_written_before
        ? VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL
        : VK_IMAGE_LAYOUT_UNDEFINED;
    output_to_color.newLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    output_to_color.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    output_to_color.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    output_to_color.image = copy_output_image;
    output_to_color.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    output_to_color.subresourceRange.levelCount = 1;
    output_to_color.subresourceRange.layerCount = 1;
    if (writes_output_image) {
        vkCmdPipelineBarrier(command,
                             copy_output_written_before
                                 ? VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT
                                 : VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                             VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, 0,
                             0, nullptr, 0, nullptr, 1, &output_to_color);
    }

    for (size_t i = 0; i < resources.draws.size(); ++i) {
        const DrawResources& draw = resources.draws[i];
        for (const DrawTextureResources& texture : draw.textures) {
            if (texture.guest_copy_source || texture.external_image) continue;
            VkImageMemoryBarrier texture_barrier{};
            texture_barrier.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
            texture_barrier.srcAccessMask = texture.upload_old_layout ==
                    VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL
                ? VK_ACCESS_SHADER_READ_BIT : 0;
            texture_barrier.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
            texture_barrier.oldLayout = texture.upload_old_layout;
            texture_barrier.newLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
            texture_barrier.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            texture_barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            texture_barrier.image = texture.image.image;
            texture_barrier.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            texture_barrier.subresourceRange.levelCount = 1;
            texture_barrier.subresourceRange.layerCount = 1;
            vkCmdPipelineBarrier(command,
                                 texture.upload_old_layout ==
                                         VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL
                                     ? VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT
                                     : VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                                 VK_PIPELINE_STAGE_TRANSFER_BIT, 0,
                                 0, nullptr, 0, nullptr, 1, &texture_barrier);
            VkBufferImageCopy copy{};
            copy.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            copy.imageSubresource.layerCount = 1;
            copy.imageExtent = {texture.width, texture.height, 1};
            vkCmdCopyBufferToImage(command, texture.upload.buffer, texture.image.image,
                                   VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &copy);
            VkImageMemoryBarrier texture_to_sample = texture_barrier;
            texture_to_sample.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
            texture_to_sample.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
            texture_to_sample.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
            texture_to_sample.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
            vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TRANSFER_BIT,
                                 VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, 0,
                                 0, nullptr, 0, nullptr, 1, &texture_to_sample);
        }
    }

    if (persistent_edram_target) {
        VkImageMemoryBarrier color_to_attachment{};
        color_to_attachment.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
        color_to_attachment.srcAccessMask = cached_edram_target->color_initialized
            ? VK_ACCESS_SHADER_READ_BIT : 0;
        color_to_attachment.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_READ_BIT |
                                             VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
        color_to_attachment.oldLayout = cached_edram_target->color_initialized
            ? VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL
            : VK_IMAGE_LAYOUT_UNDEFINED;
        color_to_attachment.newLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        color_to_attachment.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        color_to_attachment.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        color_to_attachment.image = resources.multisample_color.image;
        color_to_attachment.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        color_to_attachment.subresourceRange.levelCount = 1;
        color_to_attachment.subresourceRange.layerCount = 1;
        vkCmdPipelineBarrier(
            command,
            cached_edram_target->color_initialized
                ? VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT
                : VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
            VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, 0, 0, nullptr, 0,
            nullptr, 1, &color_to_attachment);

        if (needs_depth && cached_edram_target->depth_initialized) {
            VkImageMemoryBarrier depth_to_attachment{};
            depth_to_attachment.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
            depth_to_attachment.srcAccessMask =
                VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;
            depth_to_attachment.dstAccessMask =
                VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_READ_BIT |
                VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;
            depth_to_attachment.oldLayout =
                VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
            depth_to_attachment.newLayout =
                VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
            depth_to_attachment.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            depth_to_attachment.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            depth_to_attachment.image = resources.depth.image;
            depth_to_attachment.subresourceRange.aspectMask =
                VK_IMAGE_ASPECT_DEPTH_BIT | VK_IMAGE_ASPECT_STENCIL_BIT;
            depth_to_attachment.subresourceRange.levelCount = 1;
            depth_to_attachment.subresourceRange.layerCount = 1;
            vkCmdPipelineBarrier(
                command,
                VK_PIPELINE_STAGE_LATE_FRAGMENT_TESTS_BIT,
                VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT |
                    VK_PIPELINE_STAGE_LATE_FRAGMENT_TESTS_BIT,
                0, 0, nullptr, 0, nullptr, 1, &depth_to_attachment);
        }
    }

    VkClearValue clear{};
    clear.color.float32[3] = 1.0f;
    std::vector<VkClearValue> clear_values(attachments.size());
    clear_values[0] = clear;
    if (needs_depth) {
        const size_t depth_index = depth_reference.attachment;
        clear_values[depth_index].depthStencil.depth = 1.0f;
        clear_values[depth_index].depthStencil.stencil = 0;
    }
    VkRenderPassBeginInfo pass_begin{};
    pass_begin.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
    pass_begin.renderPass = resources.render_pass;
    pass_begin.framebuffer = resources.framebuffer;
    pass_begin.renderArea.extent = {raster_width, raster_height};
    pass_begin.clearValueCount = static_cast<uint32_t>(clear_values.size());
    pass_begin.pClearValues = clear_values.data();
    vkCmdBeginRenderPass(command, &pass_begin, VK_SUBPASS_CONTENTS_INLINE);

    for (size_t i = 0; i < draws.size(); ++i) {
        const CapturedVulkanDraw& source = draws[i];
        const DrawResources& draw = resources.draws[i];
        VkViewport viewport{};
        if (source.raster.clip_disabled_window_coordinates) {
            viewport.x = 0.0f;
            viewport.y = 0.0f;
            viewport.width = static_cast<float>(raster_width);
            viewport.height = static_cast<float>(raster_height);
        } else if (source.raster.viewport_width != 0.0f &&
            source.raster.viewport_height != 0.0f && source.raster.width &&
            source.raster.height) {
            const float scale_x = static_cast<float>(raster_width) /
                                  source.raster.width;
            const float scale_y = static_cast<float>(raster_height) /
                                  source.raster.height;
            viewport.x = source.raster.viewport_x * scale_x;
            viewport.y = source.raster.viewport_y * scale_y;
            viewport.width = source.raster.viewport_width * scale_x;
            viewport.height = source.raster.viewport_height * scale_y;
        } else {
            viewport.x = 0.0f;
            viewport.y = source.raster.viewport_y_flipped
                             ? static_cast<float>(raster_height)
                             : 0.0f;
            viewport.width = static_cast<float>(raster_width);
            viewport.height = source.raster.viewport_y_flipped
                                  ? -static_cast<float>(raster_height)
                                  : static_cast<float>(raster_height);
        }
        viewport.minDepth = 0.0f;
        viewport.maxDepth = 1.0f;
        const auto scaled_edge = [](uint32_t edge, uint32_t source_extent,
                                    uint32_t output_extent, bool round_up) {
            const uint64_t numerator = static_cast<uint64_t>(edge) * output_extent;
            const uint64_t quotient = numerator / source_extent;
            return static_cast<uint32_t>(quotient +
                (round_up && numerator % source_extent != 0 ? 1u : 0u));
        };
        const uint32_t scissor_x0 = scaled_edge(source.raster.scissor_x0,
                                                source.raster.width, raster_width, false);
        const uint32_t scissor_y0 = scaled_edge(source.raster.scissor_y0,
                                                source.raster.height, raster_height, false);
        const uint32_t scissor_x1 = scaled_edge(source.raster.scissor_x1,
                                                source.raster.width, raster_width, true);
        const uint32_t scissor_y1 = scaled_edge(source.raster.scissor_y1,
                                                source.raster.height, raster_height, true);
        VkRect2D scissor{};
        scissor.offset = {static_cast<int32_t>(scissor_x0),
                          static_cast<int32_t>(scissor_y0)};
        scissor.extent = {scissor_x1 - scissor_x0, scissor_y1 - scissor_y0};
        const VkDeviceSize vertex_offset = 0;
        vkCmdBindPipeline(command, VK_PIPELINE_BIND_POINT_GRAPHICS, draw.pipeline);
        vkCmdSetViewport(command, 0, 1, &viewport);
        vkCmdSetScissor(command, 0, 1, &scissor);
        if (draw.vertices.buffer != VK_NULL_HANDLE) {
            vkCmdBindVertexBuffers(command, 0, 1, &draw.vertices.buffer, &vertex_offset);
        }
        vkCmdBindDescriptorSets(command, VK_PIPELINE_BIND_POINT_GRAPHICS,
                                draw.pipeline_layout, 0, 2,
                                draw.descriptor_sets, 0, nullptr);
        record_draw_with_visibility_query(
            resources, command, static_cast<uint32_t>(i), [&] {
                if (source.auto_index) {
                    vkCmdDraw(command, source.index_count, 1, 0, 0);
                } else {
                    vkCmdBindIndexBuffer(command, draw.indices.buffer, 0,
                                         VK_INDEX_TYPE_UINT16);
                    vkCmdDrawIndexed(command, source.index_count, 1, 0, 0, 0);
                }
            });
    }
    vkCmdEndRenderPass(command);

    if (copy) {
        VkImageMemoryBarrier multisample_to_sample{};
        multisample_to_sample.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
        multisample_to_sample.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        multisample_to_sample.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        multisample_to_sample.image = resources.multisample_color.image;
        multisample_to_sample.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        multisample_to_sample.subresourceRange.levelCount = 1;
        multisample_to_sample.subresourceRange.layerCount = 1;
        if (source_readback_ready) {
            multisample_to_sample.srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
            multisample_to_sample.dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT;
            multisample_to_sample.oldLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
            multisample_to_sample.newLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
            vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
                                 VK_PIPELINE_STAGE_TRANSFER_BIT, 0,
                                 0, nullptr, 0, nullptr, 1, &multisample_to_sample);

            VkImageMemoryBarrier resolve_to_destination{};
            resolve_to_destination.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
            resolve_to_destination.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
            resolve_to_destination.oldLayout = VK_IMAGE_LAYOUT_UNDEFINED;
            resolve_to_destination.newLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
            resolve_to_destination.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            resolve_to_destination.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            resolve_to_destination.image = resources.source_resolve.image;
            resolve_to_destination.subresourceRange =
                multisample_to_sample.subresourceRange;
            vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                                 VK_PIPELINE_STAGE_TRANSFER_BIT, 0,
                                 0, nullptr, 0, nullptr, 1, &resolve_to_destination);

            VkImageResolve resolve{};
            resolve.srcSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            resolve.srcSubresource.layerCount = 1;
            resolve.dstSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            resolve.dstSubresource.layerCount = 1;
            resolve.extent = {source_width, source_height, 1};
            vkCmdResolveImage(command, resources.multisample_color.image,
                              VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                              resources.source_resolve.image,
                              VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &resolve);

            VkImageMemoryBarrier resolve_to_read = resolve_to_destination;
            resolve_to_read.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
            resolve_to_read.dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT;
            resolve_to_read.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
            resolve_to_read.newLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
            vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TRANSFER_BIT,
                                 VK_PIPELINE_STAGE_TRANSFER_BIT, 0,
                                 0, nullptr, 0, nullptr, 1, &resolve_to_read);
            VkBufferImageCopy source_copy{};
            source_copy.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            source_copy.imageSubresource.layerCount = 1;
            source_copy.imageExtent = {source_width, source_height, 1};
            vkCmdCopyImageToBuffer(command, resources.source_resolve.image,
                                   VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                                   resources.source_readback.buffer, 1, &source_copy);
            VkBufferMemoryBarrier source_to_host{};
            source_to_host.sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER;
            source_to_host.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
            source_to_host.dstAccessMask = VK_ACCESS_HOST_READ_BIT;
            source_to_host.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            source_to_host.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            source_to_host.buffer = resources.source_readback.buffer;
            source_to_host.size = resources.source_readback_size;
            vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TRANSFER_BIT,
                                 VK_PIPELINE_STAGE_HOST_BIT, 0,
                                 0, nullptr, 1, &source_to_host, 0, nullptr);

            multisample_to_sample.srcAccessMask = VK_ACCESS_TRANSFER_READ_BIT;
            multisample_to_sample.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
            multisample_to_sample.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
            multisample_to_sample.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
            vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TRANSFER_BIT,
                                 VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, 0,
                                 0, nullptr, 0, nullptr, 1, &multisample_to_sample);
        } else {
            multisample_to_sample.srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
            multisample_to_sample.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
            multisample_to_sample.oldLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
            multisample_to_sample.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
            vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
                                 VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, 0,
                                 0, nullptr, 0, nullptr, 1, &multisample_to_sample);
        }

        VkRenderPassBeginInfo copy_begin{};
        copy_begin.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
        copy_begin.renderPass = resources.copy_render_pass;
        copy_begin.framebuffer = resources.copy_framebuffer;
        copy_begin.renderArea.extent = {output_width, output_height};
        vkCmdBeginRenderPass(command, &copy_begin, VK_SUBPASS_CONTENTS_INLINE);
        record_copy_resolve_draw(command, resources.copy_draw, *copy,
                                 output_width, output_height);
        vkCmdEndRenderPass(command);

        if (copy->state.color_clear_enable ||
            copy->state.depth_clear_enable) {
            VkImageMemoryBarrier color_to_attachment{};
            color_to_attachment.sType =
                VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
            color_to_attachment.srcAccessMask = VK_ACCESS_SHADER_READ_BIT;
            color_to_attachment.dstAccessMask =
                VK_ACCESS_COLOR_ATTACHMENT_READ_BIT |
                VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
            color_to_attachment.oldLayout =
                VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
            color_to_attachment.newLayout =
                VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
            color_to_attachment.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            color_to_attachment.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            color_to_attachment.image = resources.multisample_color.image;
            color_to_attachment.subresourceRange.aspectMask =
                VK_IMAGE_ASPECT_COLOR_BIT;
            color_to_attachment.subresourceRange.levelCount = 1;
            color_to_attachment.subresourceRange.layerCount = 1;
            VkImageMemoryBarrier depth_to_attachment{};
            if (copy->state.depth_clear_enable) {
                depth_to_attachment.sType =
                    VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
                depth_to_attachment.srcAccessMask =
                    VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;
                depth_to_attachment.dstAccessMask =
                    VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_READ_BIT |
                    VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;
                depth_to_attachment.oldLayout =
                    VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
                depth_to_attachment.newLayout =
                    VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
                depth_to_attachment.srcQueueFamilyIndex =
                    VK_QUEUE_FAMILY_IGNORED;
                depth_to_attachment.dstQueueFamilyIndex =
                    VK_QUEUE_FAMILY_IGNORED;
                depth_to_attachment.image = resources.depth.image;
                depth_to_attachment.subresourceRange.aspectMask =
                    VK_IMAGE_ASPECT_DEPTH_BIT | VK_IMAGE_ASPECT_STENCIL_BIT;
                depth_to_attachment.subresourceRange.levelCount = 1;
                depth_to_attachment.subresourceRange.layerCount = 1;
            }
            vkCmdPipelineBarrier(
                command,
                VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT |
                    (copy->state.depth_clear_enable
                         ? VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT |
                               VK_PIPELINE_STAGE_LATE_FRAGMENT_TESTS_BIT
                         : 0),
                VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
                    (copy->state.depth_clear_enable
                         ? VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT |
                               VK_PIPELINE_STAGE_LATE_FRAGMENT_TESTS_BIT
                         : 0),
                0, 0, nullptr, 0, nullptr,
                copy->state.depth_clear_enable ? 2u : 1u,
                copy->state.depth_clear_enable
                    ? std::array<VkImageMemoryBarrier, 2>{
                          color_to_attachment, depth_to_attachment}.data()
                    : &color_to_attachment);

            VkRenderPassBeginInfo clear_begin{};
            clear_begin.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
            clear_begin.renderPass = resources.edram_clear_render_pass;
            clear_begin.framebuffer = resources.edram_clear_framebuffer;
            clear_begin.renderArea.extent = {raster_width, raster_height};
            vkCmdBeginRenderPass(command, &clear_begin,
                                 VK_SUBPASS_CONTENTS_INLINE);

            record_copy_resolve_draw(command, resources.edram_clear_draw,
                                     *copy, raster_width, raster_height);
            vkCmdEndRenderPass(command);

            VkImageMemoryBarrier color_to_sample{};
            color_to_sample.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
            color_to_sample.srcAccessMask =
                VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
            color_to_sample.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
            color_to_sample.oldLayout =
                VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
            color_to_sample.newLayout =
                VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
            color_to_sample.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            color_to_sample.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            color_to_sample.image = resources.multisample_color.image;
            color_to_sample.subresourceRange.aspectMask =
                VK_IMAGE_ASPECT_COLOR_BIT;
            color_to_sample.subresourceRange.levelCount = 1;
            color_to_sample.subresourceRange.layerCount = 1;
            vkCmdPipelineBarrier(
                command, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
                VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, 0, 0, nullptr,
                0, nullptr, 1, &color_to_sample);
        }
    }

    if (persistent_edram_target && !copy) {
        VkImageMemoryBarrier color_to_sample{};
        color_to_sample.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
        color_to_sample.srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
        color_to_sample.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
        color_to_sample.oldLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        color_to_sample.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
        color_to_sample.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        color_to_sample.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        color_to_sample.image = resources.multisample_color.image;
        color_to_sample.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        color_to_sample.subresourceRange.levelCount = 1;
        color_to_sample.subresourceRange.layerCount = 1;
        vkCmdPipelineBarrier(command,
                             VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
                             VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, 0, 0,
                             nullptr, 0, nullptr, 1, &color_to_sample);
    }

    if (writes_output_image) {
        VkImageMemoryBarrier output_to_sample{};
        output_to_sample.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
        output_to_sample.srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
        output_to_sample.dstAccessMask = output_readback
            ? VK_ACCESS_TRANSFER_READ_BIT
            : VK_ACCESS_SHADER_READ_BIT;
        output_to_sample.oldLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        output_to_sample.newLayout = output_readback
            ? VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL
            : VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
        output_to_sample.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        output_to_sample.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        output_to_sample.image = copy_output_image;
        output_to_sample.subresourceRange = output_to_color.subresourceRange;
        vkCmdPipelineBarrier(
            command, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
            output_readback ? VK_PIPELINE_STAGE_TRANSFER_BIT
                            : VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT,
            0, 0, nullptr, 0, nullptr, 1, &output_to_sample);
        if (output_readback) {
            VkBufferImageCopy readback_copy{};
            readback_copy.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            readback_copy.imageSubresource.layerCount = 1;
            readback_copy.imageExtent = {output_width, output_height, 1};
            vkCmdCopyImageToBuffer(command, copy_output_image,
                                   VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                                   resources.output_readback.buffer, 1,
                                   &readback_copy);

            VkBufferMemoryBarrier readback_to_host{};
            readback_to_host.sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER;
            readback_to_host.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
            readback_to_host.dstAccessMask = VK_ACCESS_HOST_READ_BIT;
            readback_to_host.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            readback_to_host.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            readback_to_host.buffer = resources.output_readback.buffer;
            readback_to_host.size = output_readback_size;
            vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TRANSFER_BIT,
                                 VK_PIPELINE_STAGE_HOST_BIT, 0, 0, nullptr, 1,
                                 &readback_to_host, 0, nullptr);

            VkImageMemoryBarrier output_to_presenter{};
            output_to_presenter.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
            output_to_presenter.srcAccessMask = VK_ACCESS_TRANSFER_READ_BIT;
            output_to_presenter.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
            output_to_presenter.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
            output_to_presenter.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
            output_to_presenter.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            output_to_presenter.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
            output_to_presenter.image = copy_output_image;
            output_to_presenter.subresourceRange = output_to_color.subresourceRange;
            vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TRANSFER_BIT,
                                 VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, 0,
                                 0, nullptr, 0, nullptr, 1,
                                 &output_to_presenter);
        }
    }
    result = vkEndCommandBuffer(command);
    if (result != VK_SUCCESS) return vk_fail("vkEndCommandBuffer", result, error);
    VkFenceCreateInfo fence_info{};
    fence_info.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
    result = vkCreateFence(device, &fence_info, nullptr, &resources.completion_fence);
    if (result != VK_SUCCESS) return vk_fail("vkCreateFence(captured frame)", result, error);
    VkSubmitInfo submit{};
    submit.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
    submit.commandBufferCount = 1;
    submit.pCommandBuffers = &command;
    result = vkQueueSubmit(queue, 1, &submit, resources.completion_fence);
    if (result != VK_SUCCESS) return vk_fail("vkQueueSubmit(captured frame)", result, error);
    resources.submitted = true;
    finish_texture_cache_frame(texture_cache_state);
    if (output_readback || source_readback_ready || draw_visibility ||
        !texture_cache_state) {
        if (!wait_for_frame(resources, error)) return false;
    } else {
        texture_cache_state->in_flight.push_back(std::move(resources_owner));
        texture_cache_state->in_flight_frame_count.fetch_add(1, std::memory_order_release);
    }
    collect_draw_visibility_queries(resources, draw_visibility);
    if (output_readback) {
        void* mapped = nullptr;
        result = vkMapMemory(device, resources.output_readback.memory, 0,
                             VK_WHOLE_SIZE, 0, &mapped);
        if (result != VK_SUCCESS) return vk_fail("vkMapMemory(output readback)", result, error);
        if ((resources.output_readback.memory_flags &
             VK_MEMORY_PROPERTY_HOST_COHERENT_BIT) == 0) {
            VkMappedMemoryRange range{};
            range.sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE;
            range.memory = resources.output_readback.memory;
            range.offset = 0;
            range.size = VK_WHOLE_SIZE;
            result = vkInvalidateMappedMemoryRanges(device, 1, &range);
            if (result != VK_SUCCESS) {
                vkUnmapMemory(device, resources.output_readback.memory);
                return vk_fail("vkInvalidateMappedMemoryRanges(output readback)", result, error);
            }
        }
        output_readback->resize(static_cast<size_t>(
            output_readback_size / sizeof(uint32_t)));
        std::memcpy(output_readback->data(), mapped,
                    static_cast<size_t>(output_readback_size));
        vkUnmapMemory(device, resources.output_readback.memory);
    }
    if (source_readback_ready) {
        void* mapped = nullptr;
        result = vkMapMemory(device, resources.source_readback.memory, 0,
                             VK_WHOLE_SIZE, 0, &mapped);
        if (result != VK_SUCCESS) {
            source_readback_unsupported(
                source_readback, "source buffer map failed with VkResult " +
                                     std::to_string(result));
        } else if ((resources.source_readback.memory_flags &
             VK_MEMORY_PROPERTY_HOST_COHERENT_BIT) == 0) {
            VkMappedMemoryRange range{};
            range.sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE;
            range.memory = resources.source_readback.memory;
            range.size = VK_WHOLE_SIZE;
            result = vkInvalidateMappedMemoryRanges(device, 1, &range);
            if (result != VK_SUCCESS) {
                vkUnmapMemory(device, resources.source_readback.memory);
                source_readback_unsupported(
                    source_readback, "source buffer invalidate failed with VkResult " +
                                         std::to_string(result));
                mapped = nullptr;
            }
        }
        if (mapped) {
            source_readback->bytes.resize(
                static_cast<size_t>(resources.source_readback_size));
            std::memcpy(source_readback->bytes.data(), mapped,
                        static_cast<size_t>(resources.source_readback_size));
            vkUnmapMemory(device, resources.source_readback.memory);
            source_readback->status = CapturedVulkanSourceReadback::Status::Captured;
            source_readback->reason.clear();
        }
    }
    if (error) error->clear();
    return true;
}

bool submit_captured_vulkan_operation_stream(
    VkPhysicalDevice physical_device,
    VkDevice device,
    VkQueue queue,
    uint32_t queue_family_index,
    VkImage output_image,
    VkImageView output_view,
    bool output_written_before,
    uint32_t output_width,
    uint32_t output_height,
    const std::vector<CapturedVulkanDraw>& draws,
    const std::vector<CapturedVulkanOperation>& operations,
    std::string* error,
    std::vector<uint32_t>* output_readback,
    bool geometry_shader_enabled,
    const CapturedVulkanCopy* presenter_copy,
    bool depth_stencil_resolve_enabled,
    CapturedVulkanSamplerCapabilities sampler_capabilities,
    VkPipelineCache pipeline_cache,
    CapturedVulkanTextureCache* texture_cache,
    CapturedVulkanSourceReadback* source_readback,
    std::vector<CapturedVulkanDrawVisibility>* draw_visibility) {
    if (error) error->clear();
    if (output_readback) output_readback->clear();
    if (draw_visibility) draw_visibility->assign(draws.size(), {});
    if (source_readback) {
        *source_readback = {};
        source_readback_unsupported(
            source_readback, "ordered stream has not reached its presenter copy");
    }
    if (operations.empty()) {
        return fail("ordered Vulkan operation stream has no PM4 operations", error);
    }
    if (!validate_captured_operation_stream(operations, draws.size(), error)) {
        append_captured_operation_stream(error, &operations);
        return false;
    }
    TextureCacheState* texture_cache_state = texture_cache
        ? &CapturedVulkanTextureCacheAccess::get(*texture_cache) : nullptr;
    // Guest render-target codes 3 (k_2_10_10_10_FLOAT) and 12
    // (k_2_10_10_10_FLOAT_AS_16_16_16_16) are the same surface with the same
    // packing and the same stored values; they differ only in blending
    // precision. xenos.h expresses exactly this with GetStorageColorFormat,
    // which maps 12 to 3, and neither is a 64bpp format, so EDRAM tile
    // addressing is byte-identical for both. Comparing the raw register code
    // therefore rejected a draw/copy pair whose formats resolve to one
    // identical storage layout. Normalise through the storage format first.
    // Two descriptions cover the same hardware surface when they select the
    // same EDRAM tiles with the same formats and sample count. Comparing pixel
    // extents as well is too strict: EDRAM addressing is tile-granular, so a
    // 320x243 draw and a 320x248 resolve over the same rows touch exactly the
    // same 4x16 tiles, and rejecting that resolve discards a surface the draw
    // genuinely produced. Pixel extents are still compared when the two
    // descriptions do not land on identical tile footprints, so a real layout
    // conflict is not masked.
    const auto same_edram_tile_footprint = [](const CapturedRasterState& a,
                                              const CapturedRasterState& b) {
        CapturedEdramTileFootprint left{};
        CapturedEdramTileFootprint right{};
        if (!captured_xenos_edram_tile_footprint(a, false, &left, nullptr) ||
            !captured_xenos_edram_tile_footprint(b, false, &right, nullptr)) {
            return false;
        }
        return left.pitch_tiles == right.pitch_tiles &&
            left.tile_rows == right.tile_rows;
    };
    const auto same_target_layout = [&](const CapturedRasterState& a,
                                       const CapturedRasterState& b) {
        const bool same_identity =
            a.color_base_tiles == b.color_base_tiles &&
            edram_storage_guest_color_format(a.guest_color_format) ==
                edram_storage_guest_color_format(b.guest_color_format) &&
            a.depth_base_tiles == b.depth_base_tiles &&
            a.color_format == b.color_format &&
            a.depth_format == b.depth_format &&
            a.sample_count == b.sample_count &&
            a.surface_pitch == b.surface_pitch;
        if (!same_identity) return false;
        if (a.width == b.width && a.height == b.height) return true;
        return same_edram_tile_footprint(a, b);
    };
    // The retail transition packet 24 -> 25 keeps the gamma EDRAM target and
    // extent, changes 4x/pitch-640 to 1x/pitch-1280, then copies the resulting
    // 1x source. Route only this exact target family through the existing
    // mixed-sample executor; other sample/layout reinterpretations remain
    // rejected until their backing-store mapping is captured and implemented.
    const auto is_captured_gamma_4x_to_1x_transition =
        [](const CapturedRasterState& before,
           const CapturedRasterState& after) {
            return is_captured_gamma_4x_to_1x_edram_alias(before, after);
        };
    const auto is_captured_depth_only_view_transition =
        [](const CapturedRasterState& before,
           const CapturedRasterState& after) {
            return is_captured_gamma_depth_only_view_alias(before, after);
        };
    const auto compatible_ordered_target_layout =
        [&](const CapturedRasterState& before,
            const CapturedRasterState& after) {
            return same_target_layout(before, after) ||
                is_captured_gamma_4x_to_1x_transition(before, after) ||
                is_captured_depth_only_view_transition(before, after);
        };
    const auto has_identity_alias_tiles = [](
        const CapturedRasterState& before,
        const CapturedRasterState& after, bool depth_target) {
        std::vector<CapturedEdramTileAlias> aliases;
        if (!captured_xenos_edram_alias_tiles(
                before, after, depth_target, &aliases, nullptr) ||
            aliases.size() != 720) {
            return false;
        }
        return std::all_of(aliases.begin(), aliases.end(),
                           [](const CapturedEdramTileAlias& alias) {
            return alias.source_tile_x == alias.destination_tile_x &&
                   alias.source_tile_y == alias.destination_tile_y;
        });
    };
    const auto is_captured_packet27_alias_layout =
        [&](const CapturedRasterState& before,
            const CapturedRasterState& after) {
            return before.color_base_tiles == after.color_base_tiles &&
                before.depth_base_tiles == after.depth_base_tiles &&
                before.width == 1280 && before.height == 720 &&
                after.width == before.width && after.height == before.height &&
                before.surface_pitch == 640 && after.surface_pitch == 1280 &&
                before.sample_count == 4 && after.sample_count == 1 &&
                before.guest_color_format == 1 &&
                before.color_format == CapturedColorTargetFormat::Rgba8Gamma &&
                after.guest_color_format == 0 &&
                after.color_format == CapturedColorTargetFormat::Rgba8Linear &&
                before.depth_format == after.depth_format &&
                !before.depth_only && !after.depth_only &&
                has_identity_alias_tiles(before, after, false) &&
                has_identity_alias_tiles(before, after, true);
        };
    const auto has_captured_copy_after_alias = [&] (
        size_t draw_operation_index, const CapturedRasterState& next_layout) {
        if (draw_operation_index + 1 >= operations.size() ||
            next_layout.depth_test_enabled || next_layout.depth_write_enabled ||
            next_layout.stencil_test_enabled) {
            return false;
        }
        const CapturedVulkanOperation& next =
            operations[draw_operation_index + 1];
        return next.type == CapturedVulkanOperation::Type::CopyConvert &&
            next.copy_shaders_ready &&
            next.source_raster_ready &&
            same_target_layout(next.source_raster, next_layout) &&
            next.copy_state.command == CapturedCopyCommand::Convert &&
            next.copy_state.source_select == 0 &&
            next.copy_state.sample_select == 0 &&
            next.copy_state.destination_base == 0x0975E000u &&
            next.copy_state.destination_pitch == 1280 &&
            next.copy_state.destination_height == 720 &&
            next.copy_state.destination_format == 6 &&
            next.copy_state.destination_swap_red_blue &&
            !next.copy_state.depth_clear_enable &&
            !next.copy.edram_alias_transfer_vertex_shader_spirv.empty() &&
            !next.copy.edram_alias_transfer_pixel_shader_spirv.empty();
    };
    // Packet 49 in the retail trace uses this source view over the immediately
    // preceding 4x gamma target. The current resolve path can read sample 0
    // from that multisampled image; all other EDRAM reinterpretations stay
    // fail-closed until their physical sample/tile mapping is implemented.
    const auto is_sample0_gamma_4x_to_linear_1x_source =
        [](const CapturedRasterState& draw,
           const CapturedRasterState& source,
           const CapturedCopyState& copy) {
            return copy.source_select == 0 && copy.sample_select == 0 &&
                copy.command == CapturedCopyCommand::Convert &&
                copy.destination_format == 6 && !copy.color_clear_enable &&
                !copy.depth_clear_enable && !draw.depth_only &&
                !source.depth_only && draw.sample_count == 4 &&
                source.sample_count == 1 &&
                draw.color_write_mask != 0 &&
                draw.color_format == CapturedColorTargetFormat::Rgba8Gamma &&
                source.color_format == CapturedColorTargetFormat::Rgba8Linear &&
                draw.guest_color_format == 1 &&
                source.guest_color_format == 0 &&
                draw.color_base_tiles == source.color_base_tiles &&
                draw.depth_base_tiles == source.depth_base_tiles &&
                draw.depth_format == source.depth_format &&
                draw.width == source.width && draw.height == source.height &&
                draw.surface_pitch <= UINT32_MAX / 2u &&
                source.surface_pitch == draw.surface_pitch * 2u;
        };
    const auto is_gamma_1x_to_linear_1x_source =
        [](const CapturedRasterState& draw,
           const CapturedRasterState& source,
           const CapturedCopyState& copy) {
            return copy.source_select == 0 && copy.sample_select == 0 &&
                copy.command == CapturedCopyCommand::Convert &&
                copy.destination_format == 6 && !copy.color_clear_enable &&
                !copy.depth_clear_enable && !draw.depth_only &&
                !source.depth_only && draw.sample_count == 1 &&
                source.sample_count == 1 && draw.color_write_mask != 0 &&
                draw.color_format == CapturedColorTargetFormat::Rgba8Gamma &&
                source.color_format == CapturedColorTargetFormat::Rgba8Linear &&
                draw.guest_color_format == 1 &&
                source.guest_color_format == 0 &&
                draw.color_base_tiles == source.color_base_tiles &&
                draw.depth_base_tiles == source.depth_base_tiles &&
                draw.depth_format == source.depth_format &&
                draw.width == source.width && draw.height == source.height &&
                draw.surface_pitch == source.surface_pitch;
        };
    const auto describe_target_layout = [](const CapturedRasterState& raster) {
        std::ostringstream description;
        description << "{color_base=0x" << std::hex
                    << raster.color_base_tiles << ",depth_base=0x"
                    << raster.depth_base_tiles << std::dec
                    << ",guest_color_format=" << raster.guest_color_format
                    << ",color_format="
                    << static_cast<uint32_t>(raster.color_format)
                    << ",depth_format="
                    << static_cast<uint32_t>(raster.depth_format)
                    << ",extent=" << raster.width << 'x' << raster.height
                    << ",pitch=" << raster.surface_pitch
                    << ",samples=" << raster.sample_count
                    << ",depth_only=" << raster.depth_only << '}';
        return description.str();
    };
    const auto describe_alias_tiles = [](
        const CapturedRasterState& source,
        const CapturedRasterState& destination) {
        const auto describe_raster_tiles = [](
            const CapturedRasterState& raster, bool depth_target) {
            constexpr size_t kTileCount = 2048;
            std::vector<CapturedEdramRasterTile> raster_tiles;
            std::string raster_error;
            if (!captured_xenos_edram_raster_tiles(
                    raster, depth_target, &raster_tiles, &raster_error)) {
                return std::string("invalid: ") + raster_error;
            }
            std::array<uint32_t, kTileCount> use_counts{};
            for (const CapturedEdramRasterTile& tile : raster_tiles) {
                ++use_counts[tile.physical_tile_index];
            }
            const size_t unique_tiles = static_cast<size_t>(std::count_if(
                use_counts.begin(), use_counts.end(),
                [](uint32_t count) { return count != 0; }));
            const size_t repeated_tiles = static_cast<size_t>(std::count_if(
                use_counts.begin(), use_counts.end(),
                [](uint32_t count) { return count > 1; }));
            std::ostringstream summary;
            summary << raster_tiles.size() << " raster tiles -> "
                    << unique_tiles << " physical tiles";
            if (repeated_tiles) {
                const auto first_repeated = std::find_if(
                    use_counts.begin(), use_counts.end(),
                    [](uint32_t count) { return count > 1; });
                const uint32_t tile_index = static_cast<uint32_t>(
                    std::distance(use_counts.begin(), first_repeated));
                const auto first = std::find_if(
                    raster_tiles.begin(), raster_tiles.end(),
                    [tile_index](const CapturedEdramRasterTile& tile) {
                        return tile.physical_tile_index == tile_index;
                    });
                const auto second = std::find_if(
                    first + 1, raster_tiles.end(),
                    [tile_index](const CapturedEdramRasterTile& tile) {
                        return tile.physical_tile_index == tile_index;
                    });
                summary << "; " << repeated_tiles
                        << " physical tiles repeat (tile " << tile_index
                        << " at (" << first->tile_x << ',' << first->tile_y
                        << ") and (" << second->tile_x << ',' << second->tile_y
                        << "))";
            }
            return summary.str();
        };
        std::vector<CapturedEdramTileAlias> color_tiles;
        std::vector<CapturedEdramTileAlias> depth_tiles;
        std::string color_error;
        std::string depth_error;
        const bool color_mapped = captured_xenos_edram_alias_tiles(
            source, destination, false, &color_tiles, &color_error);
        const bool depth_mapped = captured_xenos_edram_alias_tiles(
            source, destination, true, &depth_tiles, &depth_error);
        std::ostringstream description;
        description << "alias tile map={color=";
        if (color_mapped) description << color_tiles.size();
        else {
            description << "unavailable: " << color_error << "; source{"
                        << describe_raster_tiles(source, false)
                        << "}; destination{"
                        << describe_raster_tiles(destination, false) << '}';
        }
        description << ",depth=";
        if (depth_mapped) description << depth_tiles.size();
        else {
            description << "unavailable: " << depth_error << "; source{"
                        << describe_raster_tiles(source, true)
                        << "}; destination{"
                        << describe_raster_tiles(destination, true) << '}';
        }
        description << '}';
        return description.str();
    };

    size_t preflight_draw_count = 0;
    uint32_t preflight_first_draw = std::numeric_limits<uint32_t>::max();
    uint32_t preflight_color_source_draw = std::numeric_limits<uint32_t>::max();
    uint32_t preflight_layout_draw = std::numeric_limits<uint32_t>::max();
    uint32_t preflight_layout_packet = std::numeric_limits<uint32_t>::max();
    // Second, independent diagnostic hatch: an unserviceable Copy/Convert
    // currently costs the whole frame. Dropping just that copy still presents
    // every draw ahead of it, which answers whether the copy is what holds the
    // guest back. Strict by default so real failures are not hidden.
    bool tolerate_missing_copy_source = false;
    if (const char* raw =
            std::getenv("SHIFT_NATIVE_VULKAN_TOLERATE_MISSING_COPY_SOURCE");
        raw && *raw && std::strcmp(raw, "0") != 0) {
        tolerate_missing_copy_source = true;
    }
    std::vector<CapturedRasterState> preflight_targets;
    // Set when a Copy/Convert has consumed the currently active draw layout.
    // The guest resolves a mip level to guest memory and then renders the next
    // level into the head of the same EDRAM tiles, so after a drain the tiles
    // are free to be reused by a smaller layout. Without this the renderer sees
    // two overlapping layouts with no transfer between them and rejects the
    // frame, even though hardware is simply doing a mip chain.
    bool preflight_active_layout_drained = false;
    // Opt-in: let a resolve whose EDRAM source was never created proceed against
    // a freshly allocated, cleared target instead of failing the whole frame.
    const bool allocate_uninitialized_copy_source = [] {
        const char* raw =
            std::getenv("SHIFT_NATIVE_VULKAN_ALLOCATE_UNINITIALIZED_COPY_SOURCE");
        return raw && *raw && std::strcmp(raw, "0") != 0;
    }();
    bool found_presenter_copy = false;
    // Operations the tolerance hatch decided to leave out. Consumed by the
    // replay below so a skipped packet is not executed as a fullscreen
    // substitute.
    std::vector<bool> skipped_operations(operations.size(), false);
    bool skip_operation = false;
    for (size_t i = 0; i < operations.size(); ++i) {
        const CapturedVulkanOperation& operation = operations[i];
        skip_operation = false;
        if (operation.type == CapturedVulkanOperation::Type::Draw) {
            const CapturedRasterState& draw_raster =
                draws[operation.draw_index].raster;
            if (preflight_draw_count != 0 &&
                !compatible_ordered_target_layout(
                    draws[preflight_layout_draw].raster, draw_raster)) {
                const bool alias_transfer =
                    is_captured_packet27_alias_layout(
                        draws[preflight_layout_draw].raster, draw_raster) &&
                    has_captured_copy_after_alias(i, draw_raster);
                bool disjoint = false;
                uint32_t overlap_tile = 2048;
                std::string layout_error;
                if (!captured_xenos_edram_layouts_are_tile_disjoint(
                        draws[preflight_layout_draw].raster, draw_raster,
                        &disjoint, &overlap_tile, &layout_error)) {
                    std::ostringstream message;
                    message << "draw packet " << operation.packet_index
                            << " changes target layout before a Copy/Convert boundary; "
                               "invalid target layout transition: "
                            << layout_error;
                    return fail(message.str(), error);
                }
                bool tile_subset = false;
                if (!disjoint &&
                    preflight_active_layout_drained &&
                    captured_xenos_edram_layout_is_tile_subset(
                        draw_raster, draws[preflight_layout_draw].raster,
                        &tile_subset, nullptr) &&
                    tile_subset) {
                    // Legitimate mip-level reuse: the previous level was
                    // resolved to guest memory, and this smaller level lives in
                    // the head of the same tiles. It gets its own EDRAM target
                    // image at its own extent, so no shared backing is needed;
                    // the drained source is no longer read.
                    disjoint = true;
                }
                if (!disjoint && !alias_transfer) {
                    std::ostringstream message;
                    message << "draw packet " << operation.packet_index
                            << " changes target layout before a Copy/Convert boundary; "
                               "ordered Xenos EDRAM alias transfer is unavailable; prior draw packet "
                            << preflight_layout_packet << " layout="
                            << describe_target_layout(
                                   draws[preflight_layout_draw].raster)
                            << ", next layout=" << describe_target_layout(draw_raster)
                            << ", overlapping tile=" << overlap_tile;
                    message << ", " << describe_alias_tiles(
                        draws[preflight_layout_draw].raster, draw_raster);
                    return fail(message.str(), error);
                }
            }
            if (preflight_draw_count != 0 &&
                !same_target_layout(draws[preflight_layout_draw].raster,
                                    draw_raster)) {
                preflight_layout_draw = operation.draw_index;
                preflight_layout_packet = operation.packet_index;
                const bool already_tracked = std::any_of(
                    preflight_targets.begin(), preflight_targets.end(),
                    [&](const CapturedRasterState& previous) {
                        return same_target_layout(previous, draw_raster);
                    });
                if (!already_tracked) preflight_targets.push_back(draw_raster);
            }
            if (preflight_draw_count == 0) {
                bool known_layout = false;
                for (const CapturedRasterState& previous : preflight_targets) {
                    if (same_target_layout(previous, draw_raster)) {
                        known_layout = true;
                        continue;
                    }
                    bool disjoint = false;
                    uint32_t overlap_tile = 2048;
                    std::string layout_error;
                    if (!captured_xenos_edram_layouts_are_tile_disjoint(
                            previous, draw_raster, &disjoint, &overlap_tile,
                            &layout_error)) {
                        std::ostringstream message;
                        message << "draw packet " << operation.packet_index
                                << " has an invalid Xenos EDRAM layout: "
                                << layout_error;
                        return fail(message.str(), error);
                    }
                    bool drained_subset = false;
                    if (!disjoint && preflight_active_layout_drained &&
                        captured_xenos_edram_layout_is_tile_subset(
                            draw_raster, previous, &drained_subset, nullptr) &&
                        drained_subset) {
                        // Same legitimate mip-level reuse as above: this level
                        // fits inside tiles a resolved level already vacated.
                        disjoint = true;
                    }
                    if (!disjoint) {
                        std::ostringstream message;
                        message << "draw packet " << operation.packet_index
                                << " changes Xenos EDRAM target layout across a Copy/Convert boundary; "
                                   "tile " << overlap_tile
                                << " aliases a cached layout and requires shared physical EDRAM backing";
                        message << "; " << describe_alias_tiles(previous,
                                                                 draw_raster);
                        message << "; active=" << describe_target_layout(previous)
                                << ", next=" << describe_target_layout(draw_raster)
                                << ", packet27_alias="
                                << is_captured_packet27_alias_layout(previous,
                                                                     draw_raster)
                                << ", copy_after_alias="
                                << has_captured_copy_after_alias(i, draw_raster);
                        return fail(message.str(), error);
                    }
                }
                if (!known_layout) preflight_targets.push_back(draw_raster);
                preflight_first_draw = operation.draw_index;
                preflight_layout_draw = operation.draw_index;
                preflight_layout_packet = operation.packet_index;
            }
            if (!draw_raster.depth_only && draw_raster.color_write_mask != 0) {
                preflight_color_source_draw = operation.draw_index;
            }
            // A new draw has written into the active layout, so it is no longer
            // the drained copy of an earlier level.
            preflight_active_layout_drained = false;
            ++preflight_draw_count;
            continue;
        }
        if (operation.type != CapturedVulkanOperation::Type::CopyConvert) {
            continue;
        }
        if (!operation.copy_shaders_ready ||
            !operation.copy.source_geometry_ready ||
            operation.copy.source_geometry.vertex_shader_spirv.empty() ||
            operation.copy.source_geometry.geometry_shader_spirv.empty() ||
            operation.copy.source_geometry.topology !=
                PrimitiveTopology::RectangleList ||
            operation.copy.source_geometry.index_count < 3) {
            std::ostringstream message;
            message << "Copy/Convert packet " << operation.packet_index
                    << " is missing captured PM4 rectangle-list geometry or "
                       "translated resolve shaders; ordered replay refuses a fullscreen substitute";
            return fail(message.str(), error);
        }
        if (preflight_draw_count == 0) {
            CachedEdramTarget* source_target = operation.source_raster_ready
                ? find_initialized_edram_target(texture_cache_state,
                                                operation.source_raster)
                : nullptr;
            // A frame whose first operation is a resolve has no draw of its own
            // to create the source, and the frames that do draw it are the very
            // frames being rejected - so the target is never created and the
            // guest never advances. In that deadlock, admit the frame; replay
            // allocates the target (cleared) so the resolve has defined contents.
            const bool admit_uninitialized =
                !source_target && allocate_uninitialized_copy_source &&
                operation.source_raster_ready;
            if (!source_target && !admit_uninitialized) {
                std::ostringstream message;
                message << "Copy/Convert packet " << operation.packet_index
                        << " has no preceding captured draw segment or initialized "
                           "same-layout Xenos EDRAM source target";
                if (!operation.source_raster_ready) {
                    message << "; source layout registers did not decode";
                } else {
                    message << "; source layout="
                            << describe_target_layout(operation.source_raster)
                            << "; source registers: surface_info=0x" << std::hex
                            << operation.source_surface_info << " (pitch="
                            << std::dec
                            << (operation.source_surface_info & 0x3FFFu)
                            << ",msaa_mode="
                            << ((operation.source_surface_info >> 16) & 0x3u)
                            << "), color_info=0x" << std::hex
                            << operation.source_color_info << ", depth_info=0x"
                            << operation.source_depth_info
                            << ", mode_control=" << std::dec
                            << operation.source_mode_control
                            << "; decoded source extent="
                            << operation.source_width << 'x'
                            << operation.source_height;
                    // Report every cached EDRAM target and how close it came, so
                    // a near-miss on one field is visible instead of hidden.
                    const VkFormat source_color_format = captured_color_format(
                        operation.source_raster.color_format, false);
                    const EdramTargetKey source_key =
                        make_edram_target_key(operation.source_raster,
                                              source_color_format);
                    message << "; cached targets=";
                    if (texture_cache_state->edram_targets.empty()) {
                        message << "none";
                    }
                    bool first_entry = true;
                    for (const auto& [key, target] : texture_cache_state->edram_targets) {
                        if (!first_entry) message << ", ";
                        first_entry = false;
                        message << "{color_base=0x" << std::hex
                                << key.values[0] << ",depth_base=0x"
                                << key.values[1] << std::dec
                                << ",extent=" << key.values[2] << 'x'
                                << key.values[3] << ",pitch=" << key.values[4]
                                << ",guest_color_format=" << key.values[5]
                                << ",color_format=" << key.values[6]
                                << ",samples=" << key.values[7]
                                << ",depth_format=" << key.values[8]
                                << ",depth_only=" << key.values[9]
                                << ",color_init=" << target.color_initialized
                                << ",last_used_frame=" << target.last_used_frame
                                << '}';
                    }
                    message << "; this-frame draw layouts=";
                    for (size_t draw_index = 0; draw_index < draws.size();
                         ++draw_index) {
                        if (draw_index) message << ", ";
                        message << describe_target_layout(draws[draw_index].raster);
                    }
                    message << "; frame=" << texture_cache_state->frame
                            << ",exact_key_match="
                            << (texture_cache_state->edram_targets.find(source_key) !=
                                texture_cache_state->edram_targets.end());
                }
                if (tolerate_missing_copy_source) {
                    skipped_operations[i] = true;
                    continue;
                }
                return fail(message.str(), error);
            }
            bool known_layout = false;
            for (const CapturedRasterState& previous : preflight_targets) {
                if (same_target_layout(previous, operation.source_raster)) {
                    known_layout = true;
                    continue;
                }
                bool disjoint = false;
                uint32_t overlap_tile = 2048;
                std::string layout_error;
                if (!captured_xenos_edram_layouts_are_tile_disjoint(
                        previous, operation.source_raster, &disjoint,
                        &overlap_tile, &layout_error)) {
                    std::ostringstream message;
                    message << "Copy/Convert packet " << operation.packet_index
                            << " has an invalid source EDRAM layout: "
                            << layout_error;
                    return fail(message.str(), error);
                }
                if (!disjoint) {
                    std::ostringstream message;
                    message << "Copy/Convert packet " << operation.packet_index
                            << " reads EDRAM tile " << overlap_tile
                            << " through a different layout; physical alias reinterpretation is unavailable";
                    return fail(message.str(), error);
                }
            }
            if (!known_layout) preflight_targets.push_back(operation.source_raster);
        } else if (operation.source_raster_ready) {
            const uint32_t source_draw_index =
                preflight_color_source_draw != std::numeric_limits<uint32_t>::max()
                    ? preflight_color_source_draw : preflight_first_draw;
            const CapturedRasterState& source_draw =
                draws[source_draw_index].raster;
            if (!same_target_layout(source_draw, operation.source_raster) &&
                !is_sample0_gamma_4x_to_linear_1x_source(
                    source_draw, operation.source_raster, operation.copy_state) &&
                !is_gamma_1x_to_linear_1x_source(
                    source_draw, operation.source_raster, operation.copy_state)) {
                std::ostringstream message;
                message << "Copy/Convert packet " << operation.packet_index
                        << " reinterprets the active draw segment's EDRAM source layout; "
                           "only exact-layout copies are supported; active draw="
                        << describe_target_layout(source_draw)
                        << ", copy source="
                        << describe_target_layout(operation.source_raster);
                return fail(message.str(), error);
            }
        }
        // The copy has read the active draw layout into guest memory, so those
        // EDRAM tiles may now be reused for the next (smaller) mip level.
        preflight_active_layout_drained = true;
        const bool writes_presenter = presenter_copy &&
            operation.copy_state.destination_format ==
                presenter_copy->state.destination_format &&
            operation.copy_state.destination_base ==
                presenter_copy->state.destination_base;
        if (writes_presenter && i + 1 != operations.size()) {
            return fail("presenter Copy/Convert is not the final PM4 operation",
                        error);
        }
        found_presenter_copy |= writes_presenter;
        preflight_draw_count = 0;
        preflight_first_draw = std::numeric_limits<uint32_t>::max();
        preflight_color_source_draw = std::numeric_limits<uint32_t>::max();
        preflight_layout_draw = std::numeric_limits<uint32_t>::max();
        preflight_layout_packet = std::numeric_limits<uint32_t>::max();
    }
    if (presenter_copy && !found_presenter_copy && preflight_draw_count == 0) {
        return fail("presenter Copy/Convert has no preceding captured draw segment",
                    error);
    }

    std::vector<CapturedVulkanDraw> stage_draws;
    std::vector<uint32_t> stage_indices;
    uint32_t stage_layout_draw = std::numeric_limits<uint32_t>::max();
    uint32_t stage_last_packet_index = std::numeric_limits<uint32_t>::max();
    bool presenter_copy_submitted = false;

    const auto submit_stage = [&](const CapturedVulkanCopy* copy,
                                  bool writes_presenter,
                                  bool final_stream_stage,
                                  uint32_t packet_index) {
        if (stage_draws.empty()) {
            std::ostringstream message;
            message << "Copy/Convert packet " << packet_index
                    << " has no preceding captured draw segment; its Xenos EDRAM source is unavailable";
            return fail(message.str(), error);
        }
        const uint32_t stage_width = writes_presenter
            ? output_width
            : copy ? copy->state.destination_pitch
                   : stage_draws.front().raster.width;
        const uint32_t stage_height = writes_presenter
            ? output_height
            : copy ? copy->state.destination_height
                   : stage_draws.front().raster.height;
        const bool final_output_stage = writes_presenter || final_stream_stage;
        std::vector<CapturedVulkanDrawVisibility> stage_visibility;
        std::string stage_error;
        const bool submitted = submit_captured_vulkan_frame(
            physical_device, device, queue, queue_family_index, output_image,
            output_view, final_output_stage && output_written_before,
            stage_width, stage_height, stage_draws, &stage_error,
            final_output_stage ? output_readback : nullptr,
            geometry_shader_enabled, copy, depth_stencil_resolve_enabled,
            sampler_capabilities, pipeline_cache, texture_cache,
            writes_presenter ? source_readback : nullptr,
            draw_visibility ? &stage_visibility : nullptr, nullptr,
            copy != nullptr || !final_output_stage);
        if (!submitted) {
            std::ostringstream message;
            message << "ordered Vulkan segment ending at packet " << packet_index
                    << " failed: " << stage_error;
            return fail(message.str(), error);
        }
        if (draw_visibility) {
            for (size_t i = 0; i < stage_indices.size(); ++i) {
                if (stage_indices[i] < draw_visibility->size()) {
                    (*draw_visibility)[stage_indices[i]] = stage_visibility[i];
                }
            }
        }
        presenter_copy_submitted |= writes_presenter;
        stage_draws.clear();
        stage_indices.clear();
        stage_layout_draw = std::numeric_limits<uint32_t>::max();
        stage_last_packet_index = std::numeric_limits<uint32_t>::max();
        return true;
    };

    for (size_t operation_index = 0; operation_index < operations.size();
         ++operation_index) {
        const CapturedVulkanOperation& operation = operations[operation_index];
        if (skipped_operations[operation_index]) continue;
        if (operation.type == CapturedVulkanOperation::Type::Draw) {
            const CapturedVulkanDraw& draw = draws[operation.draw_index];
            if (!stage_draws.empty() &&
                !compatible_ordered_target_layout(
                    stage_draws[stage_layout_draw].raster, draw.raster)) {
                const CapturedRasterState source_layout =
                    stage_draws[stage_layout_draw].raster;
                const bool alias_transfer =
                    is_captured_packet27_alias_layout(source_layout,
                                                      draw.raster) &&
                    has_captured_copy_after_alias(operation_index,
                                                  draw.raster);
                bool disjoint = false;
                uint32_t overlap_tile = 2048;
                std::string layout_error;
                if (!captured_xenos_edram_layouts_are_tile_disjoint(
                        stage_draws[stage_layout_draw].raster, draw.raster,
                        &disjoint, &overlap_tile, &layout_error)) {
                    std::ostringstream message;
                    message << "draw packet " << operation.packet_index
                            << " changes target layout before a Copy/Convert boundary; "
                               "invalid target layout transition: "
                            << layout_error;
                    return fail(message.str(), error);
                }
                if (!disjoint && !alias_transfer) {
                    std::ostringstream message;
                    message << "draw packet " << operation.packet_index
                            << " changes target layout before a Copy/Convert boundary; "
                               "ordered Xenos EDRAM alias transfer is unavailable; overlapping tile="
                            << overlap_tile;
                    message << ", " << describe_alias_tiles(
                        stage_draws[stage_layout_draw].raster, draw.raster);
                    message << "; active="
                            << describe_target_layout(source_layout)
                            << ", next=" << describe_target_layout(draw.raster)
                            << ", packet27_alias="
                            << is_captured_packet27_alias_layout(source_layout,
                                                                 draw.raster)
                            << ", copy_after_alias="
                            << has_captured_copy_after_alias(operation_index,
                                                             draw.raster);
                    return fail(message.str(), error);
                }
                if (!submit_stage(nullptr, false, false,
                                  stage_last_packet_index)) {
                    return false;
                }
                if (alias_transfer) {
                    const CapturedVulkanOperation& copy_operation =
                        operations[operation_index + 1];
                    CachedEdramTarget* source_target =
                        find_initialized_edram_target(texture_cache_state,
                                                      source_layout);
                    if (!source_target) {
                        std::ostringstream message;
                        message << "draw packet " << operation.packet_index
                                << " has no initialized cached color image for the captured 4x-to-1x EDRAM alias transfer";
                        return fail(message.str(), error);
                    }
                    CapturedVulkanDraw transfer_draw{};
                    transfer_draw.raster = draw.raster;
                    transfer_draw.raster.scissor_x0 = 0;
                    transfer_draw.raster.scissor_y0 = 0;
                    transfer_draw.raster.scissor_x1 = draw.raster.width;
                    transfer_draw.raster.scissor_y1 = draw.raster.height;
                    transfer_draw.raster.scissor_has_area = true;
                    transfer_draw.raster.color_write_mask = 0xFu;
                    transfer_draw.raster.depth_test_enabled = false;
                    transfer_draw.raster.depth_write_enabled = false;
                    transfer_draw.raster.stencil_test_enabled = false;
                    transfer_draw.raster.depth_control = 0;
                    transfer_draw.raster.blend_control_0 = 0x00010001u;
                    transfer_draw.vertex_shader_spirv =
                        copy_operation.copy.edram_alias_transfer_vertex_shader_spirv;
                    transfer_draw.pixel_shader_spirv =
                        copy_operation.copy.edram_alias_transfer_pixel_shader_spirv;
                    transfer_draw.topology = PrimitiveTopology::TriangleList;
                    transfer_draw.auto_index = true;
                    transfer_draw.index_count = 3;
                    transfer_draw.texture_width = 1;
                    transfer_draw.texture_height = 1;
                    transfer_draw.texture_rgba8 = {0, 0, 0, 255};
                    CapturedVulkanTexture source_texture{};
                    source_texture.fetch_constant_index = 0;
                    source_texture.width = source_layout.width;
                    source_texture.height = source_layout.height;
                    source_texture.external_image_view = source_target->color.view;
                    source_texture.sampling.clamps = {
                        TextureClamp::ClampToEdge,
                        TextureClamp::ClampToEdge,
                        TextureClamp::ClampToEdge};
                    source_texture.sampling.mag_filter = TextureFilter::Point;
                    source_texture.sampling.min_filter = TextureFilter::Point;
                    source_texture.sampling.mip_filter = TextureFilter::Point;
                    source_texture.sampling.anisotropy =
                        TextureAnisotropy::Disabled;
                    source_texture.sampling.border_color =
                        TextureBorderColor::AbgrBlack;
                    source_texture.sampling.border_alpha_known = true;
                    transfer_draw.textures.push_back(std::move(source_texture));
                    std::string transfer_error;
                    if (!submit_captured_vulkan_frame(
                            physical_device, device, queue,
                            queue_family_index, output_image, output_view, false,
                            draw.raster.width, draw.raster.height,
                            {transfer_draw}, &transfer_error, nullptr,
                            geometry_shader_enabled, nullptr,
                            depth_stencil_resolve_enabled, sampler_capabilities,
                            pipeline_cache, texture_cache, nullptr, nullptr,
                            nullptr, true)) {
                        std::ostringstream message;
                        message << "captured 4x-to-1x EDRAM color transfer before draw packet "
                                << operation.packet_index << " failed: "
                                << transfer_error;
                        return fail(message.str(), error);
                    }
                }
            }
            if (stage_draws.empty() ||
                !same_target_layout(stage_draws[stage_layout_draw].raster,
                                    draw.raster)) {
                stage_layout_draw = static_cast<uint32_t>(stage_draws.size());
            }
            stage_draws.push_back(draw);
            stage_indices.push_back(operation.draw_index);
            stage_last_packet_index = operation.packet_index;
            continue;
        }
        if (operation.type != CapturedVulkanOperation::Type::CopyConvert) {
            continue;
        }

        CapturedVulkanCopy copy = operation.copy;
        copy.state = operation.copy_state;
        copy.source_width = operation.source_width;
        copy.source_height = operation.source_height;
        if (stage_draws.empty()) {
            CachedEdramTarget* source_target = operation.source_raster_ready
                ? find_initialized_edram_target(texture_cache_state,
                                                operation.source_raster)
                : nullptr;
            if (!source_target && allocate_uninitialized_copy_source &&
                operation.source_raster_ready) {
                // Allocate the missing source so this resolve has a defined
                // (cleared) image. acquire_edram_target creates and clears the
                // target, which also makes it available to later frames - the
                // deadlock was that nothing ever created it because every frame
                // that would have was rejected first.
                const VkFormat allocate_format =
                    captured_color_format(operation.source_raster.color_format, false);
                VkPhysicalDeviceMemoryProperties local_memory_properties{};
                vkGetPhysicalDeviceMemoryProperties(physical_device,
                                                   &local_memory_properties);
                if (!acquire_edram_target(
                        texture_cache_state, local_memory_properties, device,
                        operation.source_raster, allocate_format, false,
                        &source_target, error)) {
                    return false;
                }
                if (source_target) {
                    source_target->color_initialized = true;
                    source_target->last_used_frame = texture_cache_state->frame;
                }
            }
            if (!source_target) {
                std::ostringstream message;
                message << "Copy/Convert packet " << operation.packet_index
                        << " lost its initialized same-layout Xenos EDRAM source target before submission";
                return fail(message.str(), error);
            }
            const auto source_draw = std::find_if(
                draws.begin(), draws.end(), [](const CapturedVulkanDraw& draw) {
                    return !draw.vertex_shader_spirv.empty() &&
                           !draw.pixel_shader_spirv.empty();
                });
            CapturedVulkanDraw no_op_draw{};
            if (source_draw != draws.end()) {
                no_op_draw = *source_draw;
            } else {
                no_op_draw.vertex_shader_spirv = copy.vertex_shader_spirv;
                no_op_draw.pixel_shader_spirv = copy.source_gamma
                    ? (operation.source_raster.sample_count == 1
                           ? copy.gamma_single_sample_pixel_shader_spirv
                           : copy.gamma_pixel_shader_spirv)
                    : (operation.source_raster.sample_count == 1
                           ? copy.single_sample_pixel_shader_spirv
                           : copy.pixel_shader_spirv);
                no_op_draw.texture_width = 1;
                no_op_draw.texture_height = 1;
                no_op_draw.texture_rgba8 = {0, 0, 0, 255};
                no_op_draw.texture_sampling.clamps = {
                    TextureClamp::ClampToEdge, TextureClamp::ClampToEdge,
                    TextureClamp::ClampToEdge};
                no_op_draw.texture_sampling.mag_filter = TextureFilter::Point;
                no_op_draw.texture_sampling.min_filter = TextureFilter::Point;
                no_op_draw.texture_sampling.mip_filter = TextureFilter::Point;
                no_op_draw.texture_sampling.anisotropy =
                    TextureAnisotropy::Disabled;
                no_op_draw.texture_sampling.border_color =
                    TextureBorderColor::AbgrBlack;
            }
            if (no_op_draw.vertex_shader_spirv.empty() ||
                no_op_draw.pixel_shader_spirv.empty()) {
                return fail("cached-source Copy/Convert has no zero-vertex Vulkan shader pair",
                            error);
            }
            no_op_draw.raster = operation.source_raster;
            no_op_draw.raster.color_write_mask = 0;
            no_op_draw.raster.depth_test_enabled = false;
            no_op_draw.raster.depth_write_enabled = false;
            no_op_draw.raster.stencil_test_enabled = false;
            no_op_draw.raster.depth_control = 0;
            no_op_draw.raster.scissor_x0 = 0;
            no_op_draw.raster.scissor_y0 = 0;
            no_op_draw.raster.scissor_x1 = 0;
            no_op_draw.raster.scissor_y1 = 0;
            no_op_draw.raster.scissor_has_area = false;
            no_op_draw.topology = PrimitiveTopology::TriangleList;
            no_op_draw.auto_index = true;
            no_op_draw.index_count = 3;
            no_op_draw.vertex_stride_bytes = 0;
            no_op_draw.vertices.clear();
            no_op_draw.indices.clear();
            no_op_draw.vertex_input_attributes.clear();
            no_op_draw.geometry_shader_spirv.clear();
            set_copy_resolution_constants(
                &no_op_draw, copy.source_width, copy.source_height,
                copy.state.destination_pitch, copy.state.destination_height);
            stage_draws.push_back(std::move(no_op_draw));
            stage_indices.push_back(std::numeric_limits<uint32_t>::max());
        }
        const bool writes_presenter = presenter_copy &&
            copy.state.destination_format == presenter_copy->state.destination_format &&
            copy.state.destination_base == presenter_copy->state.destination_base;
        if (writes_presenter && operation_index + 1 != operations.size()) {
            return fail("presenter Copy/Convert is not the final PM4 operation",
                        error);
        }
        if (!writes_presenter) copy.retain_destination = true;
        if (!submit_stage(&copy, writes_presenter, false,
                          operation.packet_index)) {
            return false;
        }
    }

    if (!stage_draws.empty()) {
        if (!submit_stage(presenter_copy, presenter_copy != nullptr, true,
                operations.back().packet_index)) {
            return false;
        }
    } else if (presenter_copy && !presenter_copy_submitted) {
        return fail("presenter Copy/Convert has no preceding captured draw segment",
                    error);
    }
    if (error) error->clear();
    return true;
}

}  // namespace shift::xbox
