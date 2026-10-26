#include "shift_xbox_draw_input.hpp"
#include "shift_xbox_guest_ring.hpp"
#include "shift_xbox_shader_translate.hpp"
#include "shift_native_r8_upload_scratch.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <bit>
#include <charconv>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <fstream>
#include <limits>
#include <map>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <unordered_map>
#include <utility>
#include <vector>

#ifndef SHIFT_NATIVE_VULKAN_DEBUG_READBACK_FRAME
#define SHIFT_NATIVE_VULKAN_DEBUG_READBACK_FRAME 500
#endif
#ifndef SHIFT_NATIVE_VULKAN_DEBUG_READBACK_PATH
#define SHIFT_NATIVE_VULKAN_DEBUG_READBACK_PATH ""
#endif

#include <SPIRV/GlslangToSpv.h>
#include <StandAlone/ResourceLimits.h>
#include <glslang/Public/ShaderLang.h>
#include <rex/logging.h>
#include <rex/chrono/clock.h>
#include <rex/graphics/registers.h>
#include <rex/graphics/xenos.h>
#include <rex/kernel/xboxkrnl/video.h>
#include <rex/memory.h>
#include <rex/system/function_dispatcher.h>
#include <rex/system/gpu_plugin.h>
#include <rex/system/interfaces/graphics.h>
#include <rex/system/mmio_handler.h>
#include <rex/system/xthread.h>
#include <rex/system/xtypes.h>
#include <rex/ui/presenter.h>
#include <rex/ui/vulkan/presenter.h>
#include <rex/ui/vulkan/provider.h>
#include <rex/ui/windowed_app_context.h>

#include "shift_xbox_live_vulkan_renderer.hpp"

namespace {

using rex::X_STATUS;

constexpr uint32_t kGpuMmioBase = 0x7FC80000u;
constexpr uint32_t kGpuMmioMask = 0xFFFF0000u;
constexpr uint32_t kGpuMmioSize = 0x0000FFFFu;
constexpr uint32_t kRingWritePointerRegister = 0x01C5u;
constexpr uint32_t kRingReadPointerRegister = 0x01C4u;
constexpr uint32_t kVblankStatusRegister = 0x1951u;
constexpr uint32_t kCoherSizeHostRegister = 0x0A2Fu;
constexpr uint32_t kCoherBaseHostRegister = 0x0A30u;
constexpr uint32_t kCoherStatusHostRegister = 0x0A31u;
constexpr uint32_t kCoherStatusHostDirty = 0x80000000u;
constexpr uint32_t kVgtEventInitiatorRegister =
    rex::graphics::XE_GPU_REG_VGT_EVENT_INITIATOR;
constexpr uint32_t kPhysicalAddressMask = 0x1FFFFFFFu;
constexpr uint32_t kRectangleListInterpolatorCount = 16;

bool parse_positive_environment_frame(const char* text, uint32_t* frame) {
  if (!text || !*text || !frame) return false;
  const char* end = text + std::char_traits<char>::length(text);
  uint32_t parsed = 0;
  const auto result = std::from_chars(text, end, parsed, 10);
  if (result.ec != std::errc{} || result.ptr != end || parsed == 0) return false;
  *frame = parsed;
  return true;
}

bool GuestRingTraceEnabled() {
  static const bool enabled = [] {
    const char* value = std::getenv("SHIFT_NATIVE_VULKAN_TRACE_RING");
    if (value) return std::string(value) == "1";
#if defined(SHIFT_NATIVE_VULKAN_TRACE_RING_DEFAULT_ON)
    return true;
#else
    return false;
#endif
  }();
  return enabled;
}

bool IsGuestMemoryWriteCandidateOpcode(uint32_t opcode) {
  switch (opcode) {
    case 0x3Du:  // MEM_WRITE
    case 0x3Eu:  // REG_TO_MEM
    case 0x40u:  // COPY_DATA
    case 0x45u:  // COND_WRITE
    case 0x46u:  // EVENT_WRITE
    case 0x58u:  // EVENT_WRITE_SHD
    case 0x4Fu:  // MEM_WRITE_CNTR
    case 0x59u:  // EVENT_WRITE_CFL
    case 0x5Au:  // EVENT_WRITE_EXT
    case 0x5Bu:  // EVENT_WRITE_ZPD
      return true;
    default:
      return false;
  }
}

uint32_t NextGuestRingTraceRecord() {
  static std::atomic<uint32_t> record{0};
  return record.fetch_add(1, std::memory_order_relaxed);
}

constexpr uint32_t kMaxGuestRingTraceRecords = 32768;

const std::string kDebugFragmentColorShader =
    "#version 450\n"
    "layout(location=0) out vec4 shift_color0;\n"
    "void main() { shift_color0 = vec4(1.0, 0.0, 1.0, 1.0); }\n";
std::string rectangle_list_geometry_shader() {
  std::ostringstream source;
  source << "#version 450\n"
         << "layout(triangles) in;\n"
         << "layout(triangle_strip, max_vertices=4) out;\n";
  for (uint32_t index = 0; index < kRectangleListInterpolatorCount; ++index) {
    source << "layout(location=" << index << ") in vec4 shift_interpolator"
           << index << "_in[];\n";
  }
  for (uint32_t index = 0; index < kRectangleListInterpolatorCount; ++index) {
    source << "layout(location=" << index << ") out vec4 shift_interpolator"
           << index << ";\n";
  }
  source << "void main() {\n"
         << "  vec2 p0=gl_in[0].gl_Position.xy;\n"
         << "  vec2 p1=gl_in[1].gl_Position.xy;\n"
         << "  vec2 p2=gl_in[2].gl_Position.xy;\n"
         << "  float d01=dot(p1-p0,p1-p0);\n"
         << "  float d12=dot(p2-p1,p2-p1);\n"
         << "  float d20=dot(p0-p2,p0-p2);\n"
         << "  int a; int b; int c;\n"
         << "  if (d12>d20 && d12>d01) { a=0; b=1; c=2; }\n"
         << "  else if (d20>d01) { a=1; b=2; c=0; }\n"
         << "  else { a=2; b=0; c=1; }\n"
         << "  for (int i=0; i<3; ++i) {\n"
         << "    int v=i==0 ? a : (i==1 ? b : c);\n"
         << "    gl_Position=gl_in[v].gl_Position;\n";
  for (uint32_t index = 0; index < kRectangleListInterpolatorCount; ++index) {
    source << "    shift_interpolator" << index << "=shift_interpolator"
           << index << "_in[v];\n";
  }
  source << "    EmitVertex();\n"
         << "  }\n"
         << "  gl_Position=-gl_in[a].gl_Position+gl_in[b].gl_Position+gl_in[c].gl_Position;\n";
  for (uint32_t index = 0; index < kRectangleListInterpolatorCount; ++index) {
    source << "  shift_interpolator" << index << "=-shift_interpolator" << index
           << "_in[a]+shift_interpolator" << index << "_in[b]+shift_interpolator"
           << index << "_in[c];\n";
  }
  source << "  EmitVertex();\n"
         << "  EndPrimitive();\n"
         << "}\n";
  return source.str();
}
const std::string kCopyResolveVertexShader =
    "#version 450\n"
    "void main() {\n"
    "  const vec2 p[3] = vec2[3](vec2(-1.0, -1.0), vec2(3.0, -1.0),\n"
    "                           vec2(-1.0, 3.0));\n"
    "  gl_Position = vec4(p[gl_VertexIndex], 0.0, 1.0);\n"
    "}\n";
// The captured destination R/B swap describes guest memory packing. The
// Vulkan render target is already normalized to canonical RGBA channels, so
// another swizzle here would turn SHIFT's orange loading fill blue.
const std::string kCopyResolvePixelShader =
    "#version 450\n"
    "layout(set=0,binding=15) uniform PixelConstants { vec4 c[256]; } pc;\n"
    "layout(set=1,binding=0) uniform sampler2DMS source_image;\n"
    "layout(location=0) out vec4 shift_color0;\n"
    "void main() {\n"
    "  ivec2 p = ivec2(gl_FragCoord.xy * pc.c[0].xy);\n"
    "  vec4 color = texelFetch(source_image, p, 0);\n"
    "  color = floor(clamp(color, 0.0, 1.0) * 255.0 + 0.5) / 255.0;\n"
    "  shift_color0 = color;\n"
    "}\n";
const std::string kCopyResolveSingleSamplePixelShader =
    "#version 450\n"
    "layout(set=0,binding=15) uniform PixelConstants { vec4 c[256]; } pc;\n"
    "layout(set=1,binding=0) uniform sampler2D source_image;\n"
    "layout(location=0) out vec4 shift_color0;\n"
    "void main() {\n"
    "  ivec2 p = ivec2(gl_FragCoord.xy * pc.c[0].xy);\n"
    "  vec4 color = texelFetch(source_image, p, 0);\n"
    "  color = floor(clamp(color, 0.0, 1.0) * 255.0 + 0.5) / 255.0;\n"
    "  shift_color0 = color;\n"
    "}\n";
std::string copy_resolve_gamma_pixel_shader(bool multisampled) {
  std::ostringstream source;
  source << "#version 450\n"
         << "layout(set=0,binding=15) uniform PixelConstants { vec4 c[256]; } pc;\n"
         << "layout(set=1,binding=0) uniform "
         << (multisampled ? "sampler2DMS" : "sampler2D")
         << " source_image;\n"
         << "layout(location=0) out vec4 shift_color0;\n"
         << "vec3 linear_to_xenos_gamma(vec3 linear_rgb) {\n"
         << "  linear_rgb=clamp(linear_rgb,0.0,1.0);\n"
         << "  vec3 gamma_scale=mix(vec3(1023.0),vec3(1023.0/2.0),"
            "step(vec3(64.0/1023.0),linear_rgb));\n"
         << "  gamma_scale=mix(gamma_scale,vec3(1023.0/4.0),"
            "step(vec3(128.0/1023.0),linear_rgb));\n"
         << "  gamma_scale=mix(gamma_scale,vec3(1023.0/8.0),"
            "step(vec3(512.0/1023.0),linear_rgb));\n"
         << "  vec3 gamma_offset=mix(vec3(0.0),vec3(32.0),"
            "step(vec3(64.0/1023.0),linear_rgb));\n"
         << "  gamma_offset=mix(gamma_offset,vec3(64.0),"
            "step(vec3(128.0/1023.0),linear_rgb));\n"
         << "  gamma_offset=mix(gamma_offset,vec3(128.0),"
            "step(vec3(512.0/1023.0),linear_rgb));\n"
         << "  return (trunc(linear_rgb*gamma_scale)+gamma_offset)/255.0;\n"
         << "}\n"
         << "void main() {\n"
         << "  ivec2 p = ivec2(gl_FragCoord.xy * pc.c[0].xy);\n"
         << "  vec4 color = texelFetch(source_image, p, 0);\n"
         << "  color.rgb = linear_to_xenos_gamma(color.rgb);\n"
         << "  color = floor(clamp(color, 0.0, 1.0) * 255.0 + 0.5) / 255.0;\n"
         << "  shift_color0 = color;\n"
         << "}\n";
  return source.str();
}

bool DebugFragmentColorEnabled() {
  static const bool enabled = [] {
    const char* value = std::getenv("SHIFT_NATIVE_VULKAN_DEBUG_FRAGMENT_COLOR");
    return value && std::string(value) == "magenta";
  }();
  return enabled;
}

bool CapturedDrawDumpEnabled() {
#if defined(__ANDROID__) && !defined(NDEBUG)
  return true;
#else
  static const bool enabled = [] {
    const char *value = std::getenv("SHIFT_NATIVE_VULKAN_DUMP_FIRST_DRAW");
    if (value && std::string(value) == "1") return true;
    const char* frame = std::getenv("SHIFT_NATIVE_VULKAN_DUMP_DRAW_FRAME");
    uint32_t parsed_frame = 0;
    return parse_positive_environment_frame(frame, &parsed_frame);
  }();
  return enabled;
#endif
}

uint64_t Fnv1a64(const uint8_t *bytes, size_t byte_length) {
  uint64_t hash = 14695981039346656037ull;
  for (size_t i = 0; i < byte_length; ++i) {
    hash ^= bytes[i];
    hash *= 1099511628211ull;
  }
  return hash;
}

void AppendShaderConstantDump(
    std::ostringstream *output,
    const shift::xbox::CapturedShaderConstants &constants,
    const std::vector<uint32_t> &registers, bool vertex_stage) {
  if (!output)
    return;
  const auto &stage_constants = vertex_stage ? constants.vertex_float_constants
                                             : constants.pixel_float_constants;
  *output << (vertex_stage ? "vertex" : "pixel") << " constants:";
  if (registers.empty()) {
    *output << " none\n";
    return;
  }
  *output << '\n';
  for (const uint32_t reg : registers) {
    *output << "  c[" << reg << "]=";
    for (size_t lane = 0; lane < 4; ++lane) {
      const uint32_t bits = stage_constants[reg][lane];
      *output << (lane ? ", " : "") << std::hex << bits << std::dec << '('
              << std::bit_cast<float>(bits) << ')';
    }
    *output << '\n';
  }
}

uint32_t ReadGuestDword(const uint8_t* bytes) {
  return (static_cast<uint32_t>(bytes[0]) << 24) |
         (static_cast<uint32_t>(bytes[1]) << 16) |
         (static_cast<uint32_t>(bytes[2]) << 8) | bytes[3];
}

bool CompileVulkanShader(
    const char* stage_name,
    EShLanguage language,
    const std::string& source,
    std::vector<uint32_t>* spirv,
    std::string* error) {
  if (!spirv || source.empty()) return false;
  static std::once_flag initialize_once;
  static std::mutex cache_mutex;
  static std::unordered_map<std::string, std::vector<uint32_t>> cache;
  const std::string key = std::string(stage_name) + '\0' + source;
  std::lock_guard<std::mutex> lock(cache_mutex);
  if (const auto it = cache.find(key); it != cache.end()) {
    *spirv = it->second;
    return true;
  }
  std::call_once(initialize_once, [] { glslang::InitializeProcess(); });

  const char* source_ptr = source.data();
  const int source_length = static_cast<int>(source.size());
  glslang::TShader shader(language);
  shader.setStringsWithLengths(&source_ptr, &source_length, 1);
  shader.setEnvInput(glslang::EShSourceGlsl, language, glslang::EShClientVulkan, 450);
  shader.setEnvClient(glslang::EShClientVulkan, glslang::EShTargetVulkan_1_1);
  shader.setEnvTarget(glslang::EShTargetSpv, glslang::EShTargetSpv_1_3);
  constexpr EShMessages messages = EShMessages(EShMsgSpvRules | EShMsgVulkanRules);
  if (!shader.parse(&glslang::DefaultTBuiltInResource, 450, false, messages)) {
    if (error) *error = std::string("glslang parse failed: ") + shader.getInfoLog();
    return false;
  }
  glslang::TProgram program;
  program.addShader(&shader);
  if (!program.link(messages)) {
    if (error) *error = std::string("glslang link failed: ") + program.getInfoLog();
    return false;
  }
  const glslang::TIntermediate* intermediate = program.getIntermediate(language);
  if (!intermediate) {
    if (error) *error = "glslang produced no captured shader intermediate";
    return false;
  }
  std::vector<uint32_t> compiled;
  glslang::SpvOptions options{};
  options.disableOptimizer = true;
  glslang::GlslangToSpv(*intermediate, compiled, &options);
  if (compiled.empty()) {
    if (error) *error = "glslang produced empty captured SPIR-V";
    return false;
  }
  cache.emplace(key, compiled);
  *spirv = std::move(compiled);
  if (error) error->clear();
  return true;
}

bool CompileCapturedCopyResolveShaders(
    shift::xbox::CapturedVulkanCopy* copy,
    std::string* error) {
  return copy &&
         CompileVulkanShader("copy-resolve-vertex", EShLangVertex,
                             kCopyResolveVertexShader,
                             &copy->vertex_shader_spirv, error) &&
         CompileVulkanShader("copy-resolve-pixel", EShLangFragment,
                             kCopyResolvePixelShader,
                             &copy->pixel_shader_spirv, error) &&
         CompileVulkanShader("copy-resolve-single-sample-pixel", EShLangFragment,
                             kCopyResolveSingleSamplePixelShader,
                             &copy->single_sample_pixel_shader_spirv, error) &&
         CompileVulkanShader("copy-resolve-gamma-pixel", EShLangFragment,
                             copy_resolve_gamma_pixel_shader(true),
                             &copy->gamma_pixel_shader_spirv, error) &&
         CompileVulkanShader("copy-resolve-gamma-single-sample-pixel",
                             EShLangFragment,
                             copy_resolve_gamma_pixel_shader(false),
                             &copy->gamma_single_sample_pixel_shader_spirv,
                             error);
}

class R8ScratchPayloadReleaseGuard {
 public:
  R8ScratchPayloadReleaseGuard(
      shift::xbox::plugin::R8UploadScratchCache& cache, size_t draw_slot,
      std::vector<shift::xbox::CapturedVulkanTexture>& textures)
      : cache_(cache), draw_slot_(draw_slot), textures_(textures) {}

  ~R8ScratchPayloadReleaseGuard() {
    if (!active_) return;
    release();
  }

  void release() {
    for (auto& texture : textures_) {
      if (texture.format != shift::xbox::CapturedVulkanTexture::Format::R8) {
        continue;
      }
      cache_.release({draw_slot_, texture.fetch_constant_index,
                      texture.width, texture.height},
                     &texture.pixels);
    }
    active_ = false;
  }

  void dismiss() { active_ = false; }

 private:
  shift::xbox::plugin::R8UploadScratchCache& cache_;
  size_t draw_slot_;
  std::vector<shift::xbox::CapturedVulkanTexture>& textures_;
  bool active_ = true;
};

std::unique_ptr<rex::ui::vulkan::VulkanProvider> CreateShiftVulkanProvider(
    const bool with_presentation) {
  // Keep Xenos GPU emulation disabled. Request native renderer capabilities
  // independently when the provider API exposes them.
#if defined(SHIFT_REXGLUE_OPTIONAL_SAMPLER_ANISOTROPY_PROVIDER)
  return rex::ui::vulkan::VulkanProvider::Create(false, with_presentation, true, true, true);
#elif defined(SHIFT_REXGLUE_OPTIONAL_DEPTH_STENCIL_RESOLVE_PROVIDER) && \
    defined(SHIFT_REXGLUE_OPTIONAL_GEOMETRY_SHADER_PROVIDER)
  return rex::ui::vulkan::VulkanProvider::Create(false, with_presentation, true, true);
#elif defined(SHIFT_REXGLUE_OPTIONAL_DEPTH_STENCIL_RESOLVE_PROVIDER)
  return rex::ui::vulkan::VulkanProvider::Create(false, with_presentation, false, true);
#elif defined(SHIFT_REXGLUE_OPTIONAL_GEOMETRY_SHADER_PROVIDER)
  return rex::ui::vulkan::VulkanProvider::Create(false, with_presentation, true);
#else
  return rex::ui::vulkan::VulkanProvider::Create(false, with_presentation);
#endif
}

class ShiftNativeGraphicsSystem final : public rex::system::IGraphicsSystem {
 public:
  ~ShiftNativeGraphicsSystem() override { Shutdown(); }

  X_STATUS SetupPresentation(rex::ui::WindowedAppContext* app_context) override {
    if (presenter_) return X_STATUS_SUCCESS;
    if (!provider_) {
      provider_ = CreateShiftVulkanProvider(true);
    }
    if (!provider_) {
      REXLOG_ERROR("shift-native: unable to create the Vulkan presentation provider");
      return X_STATUS_UNSUCCESSFUL;
    }

    app_context_ = app_context;
    const auto create_presenter = [this]() {
      presenter_ = provider_->CreatePresenter(
          [](bool is_responsible, bool) {
            if (is_responsible) {
              REXLOG_ERROR("shift-native: Vulkan host device was lost");
            }
          });
    };
    if (app_context_) {
      if (!app_context_->CallInUIThreadSynchronous(create_presenter)) {
        return X_STATUS_UNSUCCESSFUL;
      }
    } else {
      create_presenter();
    }
    if (!presenter_) {
      REXLOG_ERROR("shift-native: unable to create the Vulkan presenter");
      return X_STATUS_UNSUCCESSFUL;
    }
    return X_STATUS_SUCCESS;
  }

  X_STATUS SetupGuestGpu(rex::runtime::FunctionDispatcher* function_dispatcher,
                         rex::system::KernelState* kernel_state) override {
    if (!function_dispatcher) return X_STATUS_UNSUCCESSFUL;
    function_dispatcher_ = function_dispatcher;
    kernel_state_ = kernel_state;
    memory_ = function_dispatcher->memory();
    if (!memory_) return X_STATUS_UNSUCCESSFUL;
    if (!provider_) {
      // Headless Vulkan device for callers that deliberately skip presentation.
      provider_ = CreateShiftVulkanProvider(false);
    }
    if (!provider_) return X_STATUS_UNSUCCESSFUL;

    if (DebugFragmentColorEnabled()) {
      REXLOG_WARN("shift-native: diagnostic fragment override is active; "
                  "submitted draws will be magenta");
    }

    if (!memory_->AddVirtualMappedRange(kGpuMmioBase, kGpuMmioMask, kGpuMmioSize, this,
                                        ReadRegisterThunk, WriteRegisterThunk)) {
      REXLOG_ERROR("shift-native: unable to register the guest GPU MMIO range");
      return X_STATUS_UNSUCCESSFUL;
    }
    try {
      if (kernel_state_) {
        ring_host_worker_ = rex::system::object_ref<rex::system::XHostThread>(
            new rex::system::XHostThread(kernel_state_, 128 * 1024, 0, [this] {
              RingWorkerLoop();
              return 0;
            }));
        ring_host_worker_->set_name("SHIFT Native GPU");
        if (XFAILED(ring_host_worker_->Create())) {
          ring_host_worker_.reset();
          return X_STATUS_UNSUCCESSFUL;
        }
      } else {
        // The isolated presenter smoke has no KernelState or guest interrupt
        // callback; keep that ABI-only path independent of the guest scheduler.
        ring_worker_ = std::thread([this] { RingWorkerLoop(); });
      }
      if (kernel_state_) {
        vblank_worker_running_.store(true, std::memory_order_release);
        vblank_host_worker_ = rex::system::object_ref<rex::system::XHostThread>(
            new rex::system::XHostThread(kernel_state_, 128 * 1024, 0, [this] {
              VblankWorkerLoop();
              return 0;
            }));
        vblank_host_worker_->set_name("SHIFT Native VSync");
        if (XFAILED(vblank_host_worker_->Create())) {
          vblank_worker_running_.store(false, std::memory_order_release);
          vblank_host_worker_.reset();
          REXLOG_ERROR("shift-native: unable to start guest vblank worker");
          return X_STATUS_UNSUCCESSFUL;
        }
        REXLOG_INFO("shift-native: guest vblank worker started");
      }
    } catch (const std::exception& e) {
      REXLOG_ERROR("shift-native: unable to start PM4 input worker: {}", e.what());
      return X_STATUS_UNSUCCESSFUL;
    }
    REXLOG_INFO("shift-native: installed emulator-free Vulkan frontend; waiting for guest PM4");
    return X_STATUS_SUCCESS;
  }

  bool has_presentation() const override { return presenter_ != nullptr; }
  rex::ui::GraphicsProvider* provider() const override { return provider_.get(); }
  rex::ui::Presenter* presenter() const override { return presenter_.get(); }

  void SetInterruptCallback(uint32_t callback, uint32_t user_data) override {
    std::lock_guard<std::mutex> lock(interrupt_mutex_);
    interrupt_callback_ = callback;
    interrupt_callback_data_ = user_data;
    REXLOG_INFO("shift-native: guest GPU interrupt callback set to {:08X}", callback);
  }

  void InitializeRingBuffer(uint32_t guest_address, uint32_t size_log2) override {
    size_t byte_length = 0;
    std::string error;
    if (!shift::xbox::guest_ring_byte_length_from_size_log2(size_log2, &byte_length, &error) ||
        !physical_span_valid(guest_address, byte_length)) {
      REXLOG_ERROR("shift-native: rejected guest ring setup ({})", error);
      return;
    }

    std::lock_guard<std::mutex> lock(ring_mutex_);
    ring_guest_address_ = guest_address;
    ring_byte_length_ = byte_length;
    ring_read_pointer_ = 0;
    ring_write_pointer_ = 0;
    ring_initialized_ = true;
    ++ring_generation_;
    REXLOG_INFO("shift-native: guest PM4 ring at {:08X}, {} bytes", guest_address,
                byte_length);
    ring_changed_.notify_one();
  }

  void EnableReadPointerWriteBack(uint32_t guest_address,
                                  uint32_t block_size_log2) override {
    const bool valid = physical_span_valid(guest_address, sizeof(uint32_t));
    auto *writeback_word =
        valid ? memory_->TranslatePhysical<uint32_t *>(guest_address) : nullptr;
    const uint32_t initial_value =
        writeback_word ? rex::memory::load_and_swap<uint32_t>(writeback_word)
                       : 0;
    std::lock_guard<std::mutex> lock(ring_mutex_);
    read_pointer_writeback_address_ = guest_address;
    REXLOG_INFO(
        "shift-native: RPTR writeback enabled guest={:08X}, block_log2={}, "
        "physical_valid={}, translated={:p}, initial={:08X}",
        guest_address, block_size_log2, valid,
        static_cast<void *>(writeback_word), initial_value);
  }

  void Shutdown() override {
    vblank_worker_running_.store(false, std::memory_order_release);
    if (vblank_host_worker_) {
      vblank_host_worker_->Wait(0, 0, 0, nullptr);
      vblank_host_worker_.reset();
    }
    {
      std::lock_guard<std::mutex> lock(ring_mutex_);
      ring_initialized_ = false;
      ring_worker_shutdown_ = true;
    }
    ring_changed_.notify_all();
    if (ring_host_worker_) {
      ring_host_worker_->Wait(0, 0, 0, nullptr);
      ring_host_worker_.reset();
    }
    if (ring_worker_.joinable()) ring_worker_.join();
    texture_cache_.clear();
    r8_upload_scratch_.clear();
    shader_translation_cache_.clear();
    if (pipeline_cache_ && provider_) {
      if (auto* device = provider_->vulkan_device(); device) {
        if (destroy_pipeline_cache_) {
          destroy_pipeline_cache_(device->device(), pipeline_cache_, nullptr);
        }
      }
      pipeline_cache_ = VK_NULL_HANDLE;
      destroy_pipeline_cache_ = nullptr;
    }
    if (presenter_ && app_context_) {
      app_context_->CallInUIThreadSynchronous([this]() { presenter_.reset(); });
    } else {
      presenter_.reset();
    }
    provider_.reset();
    app_context_ = nullptr;
    memory_ = nullptr;
    function_dispatcher_ = nullptr;
    kernel_state_ = nullptr;
  }

 private:
  struct ReadPointerWriteback {
    bool published = false;
    uint32_t guest_address = 0;
    uint32_t previous_value = 0;
    uint32_t stored_value = 0;
    void* translated_address = nullptr;
  };

  static uint32_t ReadRegisterThunk(void*, void* context, uint32_t address) {
    return static_cast<ShiftNativeGraphicsSystem*>(context)->ReadRegister(address);
  }

  static void WriteRegisterThunk(void*, void* context, uint32_t address, uint32_t value) {
    try {
      static_cast<ShiftNativeGraphicsSystem*>(context)->NotifyWriteRegister(address, value);
    } catch (const std::exception& e) {
      REXLOG_ERROR("shift-native: guest PM4 batch failed: {}", e.what());
    } catch (...) {
      REXLOG_ERROR("shift-native: guest PM4 batch failed with an unknown exception");
    }
  }

  bool physical_span_valid(uint32_t guest_address, size_t byte_length) const {
    const uint64_t physical_offset = guest_address & kPhysicalAddressMask;
    const uint64_t physical_limit = uint64_t{kPhysicalAddressMask} + 1u;
    return memory_ && byte_length != 0 &&
           physical_offset + static_cast<uint64_t>(byte_length) <= physical_limit;
  }

  ReadPointerWriteback PublishReadPointer(uint64_t generation,
                                          uint32_t expected_read_pointer,
                                          uint32_t next_read_pointer,
                                          const char* phase) {
    ReadPointerWriteback result{};
    bool writeback_outside_memory = false;
    bool writeback_untranslated = false;
    {
      std::lock_guard<std::mutex> lock(ring_mutex_);
      if (ring_generation_ != generation ||
          ring_read_pointer_ != expected_read_pointer) {
        return result;
      }
      ring_read_pointer_ = next_read_pointer;
      result.guest_address = read_pointer_writeback_address_;
      result.published = true;
      if (result.guest_address) {
        writeback_outside_memory =
            !physical_span_valid(result.guest_address, sizeof(uint32_t));
        if (!writeback_outside_memory) {
          auto* writeback_word =
              memory_->TranslatePhysical<uint32_t*>(result.guest_address);
          writeback_untranslated = writeback_word == nullptr;
          if (writeback_word) {
            result.translated_address = writeback_word;
            result.previous_value =
                rex::memory::load_and_swap<uint32_t>(writeback_word);
            rex::memory::store_and_swap<uint32_t>(writeback_word,
                                                   next_read_pointer);
            result.stored_value =
                rex::memory::load_and_swap<uint32_t>(writeback_word);
          }
        }
      }
    }

    if (writeback_outside_memory) {
      REXLOG_ERROR("shift-native: RPTR writeback address {:08X} is outside "
                   "physical memory",
                   result.guest_address);
    } else if (writeback_untranslated) {
      REXLOG_ERROR("shift-native: could not translate RPTR writeback address "
                   "{:08X}", result.guest_address);
    } else if (result.guest_address) {
      static std::atomic<uint32_t> writeback_log_count{0};
      const uint32_t log_index =
          writeback_log_count.fetch_add(1, std::memory_order_relaxed);
      if (log_index < 8u || result.stored_value != next_read_pointer) {
        REXLOG_INFO(
            "shift-native: RPTR writeback #{} guest={:08X}, translated={:p}, "
            "value={:08X}, memory={:08X}->{:08X} phase={}",
            log_index, result.guest_address, result.translated_address,
            next_read_pointer,
            result.previous_value, result.stored_value, phase);
      }
    }
    return result;
  }

  static bool ReadGuestMemory(void* context, uint32_t guest_address, size_t byte_length,
                              const uint8_t** bytes, size_t* available_bytes) {
    auto* self = static_cast<ShiftNativeGraphicsSystem*>(context);
    if (!bytes || !available_bytes || !self->physical_span_valid(guest_address, byte_length)) {
      return false;
    }
    *bytes = self->memory_->TranslatePhysical<const uint8_t*>(guest_address);
    *available_bytes = byte_length;
    return *bytes != nullptr;
  }

  bool PrepareCapturedDrawResources(
      const shift::xbox::DecodedIndexedDraw& draw,
      size_t draw_slot,
      const shift::xbox::CapturedRasterState& raster_state,
      const shift::xbox::CapturedXboxShaderRegisterState& shader_state,
      const std::vector<uint8_t>& vertex_program,
      const std::vector<uint8_t>& pixel_program,
      uint32_t diagnostic_submitted_frame,
      shift::xbox::CapturedVulkanDraw* prepared_draw,
      bool* inputs_ready,
      bool* shaders_translated,
      std::string* error) {
    if (!prepared_draw || !inputs_ready || !shaders_translated) return false;
    *inputs_ready = false;
    *shaders_translated = false;

    if (raster_state.color_format !=
            shift::xbox::CapturedColorTargetFormat::Rgba8Gamma &&
        raster_state.color_format !=
            shift::xbox::CapturedColorTargetFormat::Rgba8Linear &&
        raster_state.color_format !=
            shift::xbox::CapturedColorTargetFormat::Rgb10A2Unorm &&
        raster_state.color_format !=
            shift::xbox::CapturedColorTargetFormat::Rgb10A2Float &&
        raster_state.color_format !=
            shift::xbox::CapturedColorTargetFormat::Rg16Float) {
      if (error) *error = "unsupported captured Vulkan color-target format";
      return false;
    }

    shift::xbox::CapturedShaderConstants constants{};
    std::array<uint32_t, 2> vertex_descriptor{};
    shift::xbox::CapturedVertexFetch vertex_fetch{};
    shift::xbox::CapturedTextureFetch texture_fetch{};
    shift::xbox::CapturedTextureSampling texture_sampling{};
    struct ResolvedTexture {
      std::array<uint32_t, 6> descriptor{};
      shift::xbox::CapturedTextureFetch fetch{};
      shift::xbox::CapturedTextureSampling sampling{};
    };
    std::vector<ResolvedTexture> resolved_textures;
    if (vertex_program.empty() || pixel_program.empty() ||
        !shader_state.snapshot_constants(&constants, error)) {
      return false;
    }

    if (!constants.pixel_boolean_constants_valid) {
      std::vector<shift::xbox::CapturedShaderControlFlow> pixel_control_flow;
      if (!shift::xbox::decode_captured_shader_control_flow(
              pixel_program.data(), pixel_program.size(), &pixel_control_flow,
              error)) {
        return false;
      }
      const bool reads_missing_boolean = std::any_of(
          pixel_control_flow.begin(), pixel_control_flow.end(),
          [](const shift::xbox::CapturedShaderControlFlow &entry) {
            return entry.opcode ==
                       shift::xbox::ShaderControlFlowOpcode::ConditionalJump &&
                   (entry.bool_constant == 128u || entry.bool_constant == 129u);
          });
      if (reads_missing_boolean) {
        if (error) {
          *error = "captured pixel shader reads unloaded boolean constants "
                   "b128/b129";
        }
        return false;
      }
    }

    shift::xbox::CapturedShaderTranslationOptions options{};
    options.pixel_b128 = constants.pixel_b128;
    options.pixel_b129 = constants.pixel_b129;
    options.gamma_color_target =
        raster_state.color_format ==
        shift::xbox::CapturedColorTargetFormat::Rgba8Gamma;
    if (raster_state.clip_disabled_window_coordinates) {
      const uint32_t vte = raster_state.viewport_transform_control;
      const float captured_x_scale = raster_state.viewport_width * 0.5f;
      const float captured_y_scale = raster_state.viewport_height * 0.5f;
      options.clip_disabled_window_coordinates = true;
      options.window_coordinate_width = raster_state.width;
      options.window_coordinate_height = raster_state.height;
      options.window_coordinate_x_scale = (vte & 0x1u) ? captured_x_scale : 1.0f;
      options.window_coordinate_y_scale = (vte & 0x4u) ? captured_y_scale : 1.0f;
      options.window_coordinate_x_offset = (vte & 0x2u)
          ? raster_state.viewport_x + captured_x_scale : 0.0f;
      options.window_coordinate_y_offset = (vte & 0x8u)
          ? raster_state.viewport_y + captured_y_scale : 0.0f;
    }
    shift::xbox::CapturedShaderTranslation vertex_translation{};
    shift::xbox::CapturedShaderTranslation pixel_translation{};
    if (!shader_translation_cache_.translate(
            shift::xbox::CapturedShaderStage::Vertex, vertex_program.data(),
            vertex_program.size(), options, &vertex_translation, error)) {
      if (error) *error = "captured vertex shader: " + *error;
      return false;
    }
    if (!shader_translation_cache_.translate(
            shift::xbox::CapturedShaderStage::Pixel, pixel_program.data(),
            pixel_program.size(), options, &pixel_translation, error)) {
      if (error) *error = "captured pixel shader: " + *error;
      return false;
    }
    if (!shader_state.validate_float_constants(
            shift::xbox::GuestShaderStage::Vertex,
            vertex_translation.float_constant_registers,
            vertex_translation.uses_relative_float_constant_index, error) ||
        !shader_state.validate_float_constants(
            shift::xbox::GuestShaderStage::Pixel,
            pixel_translation.float_constant_registers,
            pixel_translation.uses_relative_float_constant_index, error)) {
      return false;
    }

    if (vertex_translation.has_vertex_fetch_constant) {
      if (vertex_translation.vertex_input_attributes.empty() ||
          !shader_state.snapshot_vertex_fetch_descriptor(
              vertex_translation.vertex_fetch_constant_index,
              &vertex_descriptor, error) ||
          !shift::xbox::decode_captured_vertex_fetch(
              vertex_descriptor.data(), &vertex_fetch, error)) {
        return false;
      }
    } else if (!vertex_translation.vertex_input_attributes.empty()) {
      if (error) *error = "captured vertex shader has inputs without a fetch constant";
      return false;
    }

    if (pixel_translation.uses_texture) {
      const std::vector<uint32_t> expected_texture_indices =
          pixel_translation.texture_fetch_constant_indices;
      for (uint32_t fetch_index : pixel_translation.texture_fetch_constant_indices) {
        ResolvedTexture resolved{};
        if (!shader_state.snapshot_texture_fetch_descriptor(
                fetch_index, &resolved.descriptor, error) ||
            !shift::xbox::decode_captured_texture_fetch(
                resolved.descriptor.data(), &resolved.fetch, error) ||
            !shift::xbox::decode_captured_texture_sampling(
                resolved.fetch, &resolved.sampling, error)) {
          if (error) {
            std::ostringstream detail;
            detail << *error << " fetch_constant=" << fetch_index
                   << " descriptor_words=[";
            for (size_t word = 0; word < resolved.descriptor.size(); ++word) {
              if (word) detail << ',';
              detail << "0x" << std::hex << resolved.descriptor[word] << std::dec;
            }
            detail << ']';
            *error = detail.str();
          }
          return false;
        }
        for (size_t i = 0; i < options.textures[fetch_index].swizzle.size(); ++i) {
          options.textures[fetch_index].swizzle[i] =
              static_cast<uint32_t>(resolved.sampling.swizzle[i]);
        }
        options.textures[fetch_index].signs = resolved.sampling.signs;
        if (resolved_textures.empty()) {
          texture_fetch = resolved.fetch;
          texture_sampling = resolved.sampling;
        }
        resolved_textures.push_back(std::move(resolved));
      }
      if (!shader_translation_cache_.translate(
              shift::xbox::CapturedShaderStage::Pixel, pixel_program.data(),
              pixel_program.size(), options, &pixel_translation, error)) {
        if (error) *error = "captured pixel shader: " + *error;
        return false;
      }
      if (!pixel_translation.uses_texture ||
          pixel_translation.texture_fetch_constant_indices !=
              expected_texture_indices ||
          pixel_translation.texture_fetch_constant_indices.size() != resolved_textures.size()) {
        if (error) *error = "captured pixel texture fetch set changed during translation";
        return false;
      }
    } else {
      texture_sampling = shift::xbox::CapturedTextureSampling{
          {shift::xbox::TextureComponent::X, shift::xbox::TextureComponent::Y,
           shift::xbox::TextureComponent::Z, shift::xbox::TextureComponent::W},
          {shift::xbox::TextureSign::Unsigned, shift::xbox::TextureSign::Unsigned,
           shift::xbox::TextureSign::Unsigned, shift::xbox::TextureSign::Unsigned},
          {shift::xbox::TextureClamp::ClampToEdge,
           shift::xbox::TextureClamp::ClampToEdge,
           shift::xbox::TextureClamp::ClampToEdge},
          shift::xbox::TextureFilter::Linear,
          shift::xbox::TextureFilter::Linear,
          shift::xbox::TextureFilter::Point,
          shift::xbox::TextureAnisotropy::Disabled,
          shift::xbox::TextureBorderColor::AbgrBlack,
          true};
      texture_fetch.width = 1;
      texture_fetch.height = 1;
      texture_fetch.byte_length = 4;
    }
    *inputs_ready = true;
    *shaders_translated = true;

    if (DebugFragmentColorEnabled()) {
      static std::atomic<uint32_t> debug_vertex_shader_log_mask{0};
      const uint32_t shader_log_bit = vertex_program.size() == 96 ? 1u
                                      : vertex_program.size() == 108 ? 2u
                                                                     : 4u;
      const uint32_t previous = debug_vertex_shader_log_mask.fetch_or(
          shader_log_bit, std::memory_order_relaxed);
      if ((previous & shader_log_bit) == 0) {
        REXLOG_DEBUG(
            "shift-native: first translated captured vertex shader ({} bytes):\n{}",
            vertex_program.size(), vertex_translation.glsl);
      }
    }

    const std::string& pixel_shader_source = DebugFragmentColorEnabled()
                                                 ? kDebugFragmentColorShader
                                                 : pixel_translation.glsl;
    shift::xbox::CapturedVulkanDraw prepared{};
    prepared.raster = raster_state;
    prepared.constants = constants;
    prepared.texture_sampling = texture_sampling;
    prepared.index_count = draw.index_count;
    prepared.topology = draw.topology;
    prepared.auto_index = draw.auto_index;
    prepared.texture_width = texture_fetch.width;
    prepared.texture_height = texture_fetch.height;
    prepared.vertex_input_attributes = vertex_translation.vertex_input_attributes;
    if (!CompileVulkanShader("vertex", EShLangVertex, vertex_translation.glsl,
                             &prepared.vertex_shader_spirv, error) ||
        !CompileVulkanShader("pixel", EShLangFragment, pixel_shader_source,
                             &prepared.pixel_shader_spirv, error)) {
      return false;
    }
    if (raster_state.color_format ==
        shift::xbox::CapturedColorTargetFormat::Rgba8Gamma) {
      auto linear_target_options = options;
      linear_target_options.gamma_color_target = false;
      shift::xbox::CapturedShaderTranslation linear_target_translation{};
      if (!shader_translation_cache_.translate(
              shift::xbox::CapturedShaderStage::Pixel, pixel_program.data(),
              pixel_program.size(), linear_target_options,
              &linear_target_translation, error)) {
        if (error) *error = "captured linear-blend pixel shader: " + *error;
        return false;
      }
      const std::string& linear_target_source = DebugFragmentColorEnabled()
          ? kDebugFragmentColorShader
          : linear_target_translation.glsl;
      if (!CompileVulkanShader("pixel-linear-gamma-target", EShLangFragment,
                               linear_target_source,
                               &prepared.pixel_shader_spirv_linear_target,
                               error)) {
        return false;
      }
    }
    if (draw.topology == shift::xbox::PrimitiveTopology::RectangleList) {
      auto* device = provider_ ? provider_->vulkan_device() : nullptr;
      if (!device || !device->properties().geometryShader) {
        if (error) *error = "captured rectangle-list draw requires Vulkan geometryShader";
        return false;
      }
      if (!CompileVulkanShader("rectangle-list-geometry", EShLangGeometry,
                               rectangle_list_geometry_shader(),
                               &prepared.geometry_shader_spirv, error)) {
        return false;
      }
    }

    constexpr uint32_t kMaxLiveIndexBytes = 2u * 1024u * 1024u;
    constexpr uint32_t kMaxLiveVertexBytes = 4u * 1024u * 1024u;
    constexpr uint32_t kMaxLiveTextureBytes = 16u * 1024u * 1024u;
    const uint8_t* guest_bytes = nullptr;
    size_t guest_byte_length = 0;
    uint32_t maximum_vertex_index = 0;
    if (draw.auto_index) {
      if (draw.topology != shift::xbox::PrimitiveTopology::PointList &&
          draw.topology != shift::xbox::PrimitiveTopology::RectangleList &&
          draw.topology != shift::xbox::PrimitiveTopology::TriangleList &&
          draw.topology != shift::xbox::PrimitiveTopology::TriangleStrip) {
        if (error) *error = "captured AutoIndex primitive expansion is unsupported";
        return false;
      }
      maximum_vertex_index = draw.index_count - 1;
    } else {
      if (draw.index_byte_length > kMaxLiveIndexBytes ||
          !ReadGuestMemory(this, draw.index_guest_address,
                           draw.index_byte_length, &guest_bytes,
                           &guest_byte_length) ||
          guest_byte_length < draw.index_byte_length ||
          !shift::xbox::decode_captured_index_data(
              draw, guest_bytes, draw.index_byte_length, &prepared.indices,
              &maximum_vertex_index, error)) {
        return false;
      }
    }
    uint32_t vertex_stride_bytes = 0;
    if (!vertex_translation.vertex_input_attributes.empty()) {
      uint32_t maximum_attribute_end = 0;
      for (const auto& attribute : vertex_translation.vertex_input_attributes) {
        const uint32_t attribute_size = attribute.vertex_format == 6  ? 4u
                                        : attribute.vertex_format == 37 ? 8u
                                        : attribute.vertex_format == 57 ? 12u
                                        : attribute.vertex_format == 38 ? 16u
                                                                        : 0u;
        if (attribute_size == 0 || attribute.stride_dwords == 0 ||
            attribute.offset_dwords < 0) {
          if (error) *error = "captured vertex input layout is unsupported";
          return false;
        }
        const uint64_t stride_bytes = uint64_t{attribute.stride_dwords} * 4u;
        const uint64_t offset_bytes =
            static_cast<uint64_t>(attribute.offset_dwords) * 4u;
        if (stride_bytes > UINT32_MAX || offset_bytes + attribute_size > stride_bytes ||
            (vertex_stride_bytes != 0 && vertex_stride_bytes != stride_bytes)) {
          if (error) *error = "captured vertex input attributes disagree on stride";
          return false;
        }
        vertex_stride_bytes = static_cast<uint32_t>(stride_bytes);
        maximum_attribute_end = std::max(
            maximum_attribute_end,
            static_cast<uint32_t>(offset_bytes + attribute_size));
      }
      uint32_t required_vertex_bytes = 0;
      if (!shift::xbox::captured_vertex_required_bytes(
              maximum_vertex_index, vertex_stride_bytes, 0, maximum_attribute_end,
              &required_vertex_bytes, error) ||
          required_vertex_bytes > kMaxLiveVertexBytes ||
          required_vertex_bytes > vertex_fetch.byte_length ||
          !ReadGuestMemory(this, vertex_fetch.guest_address, required_vertex_bytes,
                           &guest_bytes, &guest_byte_length) ||
          guest_byte_length < required_vertex_bytes ||
          !shift::xbox::normalize_captured_buffer_bytes(
              vertex_fetch.endian_mode, guest_bytes, required_vertex_bytes,
              &prepared.vertices, error)) {
        return false;
      }
    }
    prepared.vertex_stride_bytes = vertex_stride_bytes;
    R8ScratchPayloadReleaseGuard scratch_payload_guard(
        r8_upload_scratch_, draw_slot, prepared.textures);
    if (DebugFragmentColorEnabled()) {
      static std::atomic<uint32_t> vertex_sample_index{0};
      const uint32_t sample =
          vertex_sample_index.fetch_add(1, std::memory_order_relaxed);
      if (prepared.vertices.size() >= 12) {
        const auto vertex_component = [&prepared](size_t component) {
          const size_t offset = component * sizeof(uint32_t);
          const uint32_t bits = static_cast<uint32_t>(prepared.vertices[offset]) |
                                (static_cast<uint32_t>(prepared.vertices[offset + 1]) << 8) |
                                (static_cast<uint32_t>(prepared.vertices[offset + 2]) << 16) |
                                (static_cast<uint32_t>(prepared.vertices[offset + 3]) << 24);
          return std::bit_cast<float>(bits);
        };
        REXLOG_DEBUG(
            "shift-native: diagnostic vertex sample #{}: autoindex={}, topology={}, "
            "vs-bytes={}, has-fetch-constant={}, fetch-constant={}, attributes={}, "
            "guest={:08X}, endian={}, stride={}, bytes={}, position=({:.6g}, {:.6g}, {:.6g})",
            sample, draw.auto_index, static_cast<uint32_t>(draw.topology),
            vertex_program.size(), vertex_translation.has_vertex_fetch_constant,
            vertex_translation.vertex_fetch_constant_index,
            vertex_translation.vertex_input_attributes.size(),
            vertex_fetch.guest_address, vertex_fetch.endian_mode,
            vertex_stride_bytes, prepared.vertices.size(), vertex_component(0),
            vertex_component(1), vertex_component(2));
      } else {
        REXLOG_DEBUG(
            "shift-native: diagnostic vertex sample #{} has no position bytes: "
            "autoindex={}, topology={}, vs-bytes={}, has-fetch-constant={}, "
            "fetch-constant={}, attributes={}, stride={}, bytes={}",
            sample, draw.auto_index, static_cast<uint32_t>(draw.topology),
            vertex_program.size(), vertex_translation.has_vertex_fetch_constant,
            vertex_translation.vertex_fetch_constant_index,
            vertex_translation.vertex_input_attributes.size(),
            vertex_stride_bytes, prepared.vertices.size());
      }
    }
    if (pixel_translation.uses_texture) {
      size_t total_texture_bytes = 0;
      prepared.textures.reserve(resolved_textures.size());
      for (size_t i = 0; i < resolved_textures.size(); ++i) {
        const ResolvedTexture& resolved = resolved_textures[i];
        const auto& fetch = resolved.fetch;
        if (fetch.byte_length > kMaxLiveTextureBytes - total_texture_bytes) {
          if (error) *error = "captured pixel textures exceed the live read limit";
          return false;
        }
        if (!ReadGuestMemory(this, fetch.guest_address, fetch.byte_length,
                             &guest_bytes, &guest_byte_length) ||
            guest_byte_length < fetch.byte_length) {
          if (error) *error = "captured texture guest memory is unavailable";
          return false;
        }
        const char* texture_source_dump_prefix =
            std::getenv("SHIFT_NATIVE_VULKAN_DUMP_TEXTURE_SOURCE_PREFIX");
        if (texture_source_dump_prefix && *texture_source_dump_prefix) {
          const auto dump_texture_source = [&](const std::string& path) {
            std::ofstream source_file(path,
                                      std::ios::binary | std::ios::trunc);
            source_file.write(reinterpret_cast<const char*>(guest_bytes),
                              static_cast<std::streamsize>(fetch.byte_length));
            if (source_file) {
              REXLOG_INFO(
                  "shift-native: dumped guest texture source frame={} slot={} "
                  "texture={} address={:08X} format={} bytes={} fnv1a=0x{:016X} "
                  "path={}",
                  diagnostic_submitted_frame, draw_slot, i,
                  fetch.guest_address, fetch.format, fetch.byte_length,
                  Fnv1a64(guest_bytes, fetch.byte_length), path);
            } else {
              REXLOG_WARN("shift-native: could not write guest texture source {}",
                          path);
            }
          };
          if (diagnostic_submitted_frame != 0) {
            std::ostringstream source_path;
            source_path << texture_source_dump_prefix << ".frame"
                        << diagnostic_submitted_frame << ".slot" << draw_slot
                        << ".texture" << i << ".source.bin";
            dump_texture_source(source_path.str());
          }
          static const uint32_t selected_guest_address = [] {
            const char* text = std::getenv(
                "SHIFT_NATIVE_VULKAN_DUMP_TEXTURE_SOURCE_GUEST_ADDRESS");
            if (!text || !*text) return uint32_t{0};
            int base = 10;
            if (text[0] == '0' &&
                (text[1] == 'x' || text[1] == 'X')) {
              text += 2;
              base = 16;
            }
            const char* end = text + std::strlen(text);
            uint32_t address = 0;
            const auto parsed = std::from_chars(text, end, address, base);
            return parsed.ec == std::errc{} && parsed.ptr == end ? address
                                                                  : uint32_t{0};
          }();
          static std::atomic<bool> selected_guest_address_dumped{false};
          if (selected_guest_address != 0 &&
              fetch.guest_address == selected_guest_address &&
              !selected_guest_address_dumped.exchange(
                  true, std::memory_order_relaxed)) {
            std::ostringstream source_path;
            source_path << texture_source_dump_prefix << ".guest" << std::hex
                        << fetch.guest_address << ".first.source.bin";
            dump_texture_source(source_path.str());
          }
        }
        shift::xbox::CapturedVulkanTexture texture{};
        texture.fetch_constant_index =
            pixel_translation.texture_fetch_constant_indices[i];
        texture.sampling = resolved.sampling;
        texture.width = fetch.width;
        texture.height = fetch.height;
        const std::array<shift::xbox::TextureComponent, 4> r8_plane_swizzle = {
            shift::xbox::TextureComponent::X,
            shift::xbox::TextureComponent::X,
            shift::xbox::TextureComponent::X,
            shift::xbox::TextureComponent::One,
        };
        const bool use_native_r8 = fetch.format == 2 && fetch.endian_mode == 0 &&
                                   resolved.sampling.swizzle == r8_plane_swizzle;
        const shift::xbox::plugin::R8UploadScratchKey scratch_key{
            draw_slot, texture.fetch_constant_index, fetch.width, fetch.height};
        const bool scratch_acquired = use_native_r8 &&
            r8_upload_scratch_.acquire(scratch_key, &texture.pixels);
        const bool texture_ready = use_native_r8
            ? shift::xbox::copy_captured_r8_texture_2d(
                  fetch, guest_bytes, fetch.byte_length, &texture.pixels, error)
            : shift::xbox::untile_captured_texture_2d(
                  fetch, guest_bytes, fetch.byte_length, &texture.pixels, error);
        if (!texture_ready) {
          if (scratch_acquired) {
            r8_upload_scratch_.release(scratch_key, &texture.pixels);
          }
          return false;
        }
        texture.format = use_native_r8
            ? shift::xbox::CapturedVulkanTexture::Format::R8
            : shift::xbox::CapturedVulkanTexture::Format::Rgba8;
        total_texture_bytes += fetch.byte_length;
        prepared.textures.push_back(std::move(texture));
      }
      if (!prepared.textures.empty()) {
        prepared.texture_sampling = prepared.textures.front().sampling;
        prepared.texture_width = prepared.textures.front().width;
        prepared.texture_height = prepared.textures.front().height;
      }
    } else {
      prepared.texture_rgba8 = {255, 255, 255, 255};
    }
    if (CapturedDrawDumpEnabled()) {
      static std::atomic<uint32_t> dumped_draw_count{0};
      const uint32_t dump_index =
          dumped_draw_count.fetch_add(1, std::memory_order_relaxed);
      static const auto diagnostic_start = std::chrono::steady_clock::now();
      static std::atomic<uint32_t> late_dump_count{0};
      const bool initial_sample = dump_index < 8;
      const auto elapsed = std::chrono::steady_clock::now() - diagnostic_start;
      const bool late_sample_window =
          !initial_sample && elapsed >= std::chrono::seconds(30);
      const uint32_t late_dump_index =
          late_sample_window
              ? late_dump_count.fetch_add(1, std::memory_order_relaxed)
              : 0;
      if (initial_sample || (late_sample_window && late_dump_index < 8) ||
          diagnostic_submitted_frame != 0) {
        std::ostringstream dump;
        dump << "shift-native: resolved captured retail draw #" << dump_index;
        if (initial_sample) {
          dump << " (startup sample)";
        } else {
          dump << " (late sample #" << late_dump_index << ')';
        }
        if (diagnostic_submitted_frame != 0) {
          dump << " (Vulkan readback target frame "
               << diagnostic_submitted_frame << ')';
        }
        dump << " elapsed_ms="
             << std::chrono::duration_cast<std::chrono::milliseconds>(elapsed)
                    .count()
             << '\n'
             << "  topology=" << static_cast<uint32_t>(draw.topology)
             << " autoindex=" << draw.auto_index
             << " index_count=" << draw.index_count << " index_guest=0x"
             << std::hex << draw.index_guest_address << std::dec
             << " index_type=" << draw.index_type_bits
             << " index_endian=" << draw.index_endian_mode
             << " raster=" << raster_state.width << 'x' << raster_state.height
             << " pitch=" << raster_state.surface_pitch
             << " samples=" << raster_state.sample_count
             << " color_base_tiles=" << raster_state.color_base_tiles
             << " depth_base_tiles=" << raster_state.depth_base_tiles
             << " color_format="
             << static_cast<uint32_t>(raster_state.color_format) << " scissor=["
             << raster_state.scissor_x0 << ',' << raster_state.scissor_y0 << ','
             << raster_state.scissor_x1 << ',' << raster_state.scissor_y1
             << "] depth={test:" << raster_state.depth_test_enabled
             << ",write:" << raster_state.depth_write_enabled
             << ",stencil:" << raster_state.stencil_test_enabled
             << "} color_mask=0x" << std::hex
             << raster_state.color_write_mask << " blend=0x"
             << raster_state.blend_control_0 << " setup=0x"
             << raster_state.setup_mode_control << std::dec
             << " cull=" << static_cast<uint32_t>(raster_state.cull_mode)
             << " front_ccw=" << raster_state.front_face_ccw
             << " clip={valid:" << raster_state.clip_control_valid
             << ",disabled:" << raster_state.clip_disabled
             << ",vte_valid:" << raster_state.viewport_transform_control_valid
             << ",vte:0x" << std::hex
             << raster_state.viewport_transform_control << std::dec
             << ",window_xy:" << raster_state.clip_disabled_window_coordinates
             << "}\n"
             << "  shaders: VS=" << vertex_program.size() << " bytes FNV-1a=0x"
             << std::hex
             << Fnv1a64(vertex_program.data(), vertex_program.size())
             << " PS=" << std::dec << pixel_program.size() << " bytes FNV-1a=0x"
             << std::hex << Fnv1a64(pixel_program.data(), pixel_program.size())
             << std::dec << "\n  vertex fetch: guest=0x" << std::hex
             << vertex_fetch.guest_address << " descriptor={0x"
             << vertex_descriptor[0] << ",0x" << vertex_descriptor[1] << '}'
             << std::dec << " endian=" << vertex_fetch.endian_mode
             << " stride=" << vertex_stride_bytes
             << " payload_bytes=" << prepared.vertices.size() << " attributes="
             << vertex_translation.vertex_input_attributes.size() << "\n";
        const size_t vertex_count = std::min<size_t>(draw.index_count, 4u);
        for (size_t vertex = 0; vertex < vertex_count; ++vertex) {
          uint32_t vertex_index = static_cast<uint32_t>(vertex);
          if (!draw.auto_index) {
            const size_t index_offset = vertex * sizeof(uint16_t);
            if (draw.index_type_bits != 16 ||
                index_offset + sizeof(uint16_t) > prepared.indices.size()) {
              dump << "  vertex[" << vertex << "]: index unavailable\n";
              continue;
            }
            vertex_index =
                static_cast<uint32_t>(prepared.indices[index_offset]) |
                (static_cast<uint32_t>(prepared.indices[index_offset + 1])
                 << 8);
          }
          for (const auto &attribute :
               vertex_translation.vertex_input_attributes) {
            const size_t byte_offset =
                static_cast<size_t>(vertex_index) * vertex_stride_bytes +
                static_cast<size_t>(attribute.offset_dwords) * sizeof(uint32_t);
            const size_t component_count = attribute.vertex_format == 6  ? 0u
                                           : attribute.vertex_format == 37 ? 2u
                                           : attribute.vertex_format == 57 ? 3u
                                           : attribute.vertex_format == 38 ? 4u
                                                                           : 0u;
            dump << "  vertex[" << vertex << "] index=" << vertex_index
                 << " location=" << attribute.location << " destination=r"
                 << attribute.destination_register
                 << " format=" << attribute.vertex_format
                 << " offset=" << (attribute.offset_dwords * 4) << " values={";
            if (attribute.vertex_format == 6) {
              dump << "rgba8={";
              for (size_t component = 0; component < 4; ++component) {
                if (byte_offset + component >= prepared.vertices.size()) {
                  dump << (component ? ", " : "") << "out-of-range";
                  break;
                }
                dump << (component ? ", " : "")
                     << static_cast<uint32_t>(prepared.vertices[byte_offset + component]);
              }
              dump << "}";
            } else {
              for (size_t component = 0; component < component_count;
                   ++component) {
                const size_t offset = byte_offset + component * sizeof(uint32_t);
                if (offset + sizeof(uint32_t) > prepared.vertices.size()) {
                  dump << (component ? ", " : "") << "out-of-range";
                  break;
                }
                const uint32_t bits =
                    static_cast<uint32_t>(prepared.vertices[offset]) |
                    (static_cast<uint32_t>(prepared.vertices[offset + 1]) << 8) |
                    (static_cast<uint32_t>(prepared.vertices[offset + 2]) << 16) |
                    (static_cast<uint32_t>(prepared.vertices[offset + 3]) << 24);
                dump << (component ? ", " : "") << std::hex << bits << std::dec
                     << '(' << std::bit_cast<float>(bits) << ')';
              }
            }
            if (attribute.vertex_format == 37)
              dump << ", 0(0), 1(1)";
            else if (attribute.vertex_format == 57)
              dump << ", 1(1)";
            dump << "}\n";
          }
        }
        dump << "  normalized_vertex_payload_fnv1a=0x" << std::hex
             << Fnv1a64(prepared.vertices.data(), prepared.vertices.size())
             << std::dec << "\n";
        const char* geometry_dump_prefix =
            std::getenv("SHIFT_NATIVE_VULKAN_DUMP_GEOMETRY_PREFIX");
        if (diagnostic_submitted_frame != 0 && geometry_dump_prefix &&
            *geometry_dump_prefix) {
          const auto dump_geometry = [&](const char* kind,
                                         const std::vector<uint8_t>& bytes) {
            std::ostringstream path;
            path << geometry_dump_prefix << ".frame"
                 << diagnostic_submitted_frame << ".draw" << dump_index << '.'
                 << kind << ".bin";
            std::ofstream file(path.str(), std::ios::binary | std::ios::trunc);
            if (!bytes.empty()) {
              file.write(reinterpret_cast<const char*>(bytes.data()),
                         static_cast<std::streamsize>(bytes.size()));
            }
            if (file) {
              dump << "  raw_" << kind << "_dump=" << path.str()
                   << " bytes=" << bytes.size() << " fnv1a=0x" << std::hex
                   << Fnv1a64(bytes.data(), bytes.size()) << std::dec << "\n";
            } else {
              dump << "  raw_" << kind << "_dump_failed=" << path.str()
                   << " bytes=" << bytes.size() << "\n";
            }
          };
          dump_geometry("vertices", prepared.vertices);
          dump_geometry("indices", prepared.indices);
        }
        if (pixel_translation.uses_texture) {
          for (size_t texture_index = 0; texture_index < resolved_textures.size();
               ++texture_index) {
            const auto& resolved = resolved_textures[texture_index];
            const auto& texture = prepared.textures[texture_index];
            dump << "  texture fetch="
                 << texture.fetch_constant_index << " guest=0x"
                 << std::hex << resolved.fetch.guest_address << " descriptor={";
            for (size_t i = 0; i < resolved.descriptor.size(); ++i) {
              dump << (i ? "," : "") << "0x" << resolved.descriptor[i];
            }
            dump << "} extent=" << std::dec << resolved.fetch.width << 'x'
                 << resolved.fetch.height << " format=" << resolved.fetch.format
                 << " byte_length=" << resolved.fetch.byte_length
                 << " sampler={clamp:";
            for (size_t axis = 0; axis < resolved.sampling.clamps.size(); ++axis) {
              dump << (axis ? "," : "")
                   << static_cast<uint32_t>(resolved.sampling.clamps[axis]);
            }
            dump << ",filter:"
                 << static_cast<uint32_t>(resolved.sampling.mag_filter) << '/'
                 << static_cast<uint32_t>(resolved.sampling.min_filter) << '/'
                 << static_cast<uint32_t>(resolved.sampling.mip_filter)
                 << ",aniso:" << static_cast<uint32_t>(resolved.sampling.anisotropy)
                 << ",border:" << static_cast<uint32_t>(resolved.sampling.border_color)
                 << ",border_alpha_known:" << resolved.sampling.border_alpha_known
                 << "}"
                 << " texel_format="
                 << (texture.format == shift::xbox::CapturedVulkanTexture::Format::R8
                         ? "R8_UNORM"
                         : "RGBA8_UNORM")
                 << " texel_bytes=" << texture.pixels.size()
                 << " texel_fnv1a=0x" << std::hex
                 << Fnv1a64(texture.pixels.data(), texture.pixels.size())
                 << std::dec << "\n";
            const char* texture_dump_prefix =
                std::getenv("SHIFT_NATIVE_VULKAN_DUMP_TEXTURES_PREFIX");
            if (diagnostic_submitted_frame != 0 && texture_dump_prefix &&
                *texture_dump_prefix) {
              std::ostringstream texture_path;
              texture_path << texture_dump_prefix << ".frame"
                           << diagnostic_submitted_frame << ".draw"
                           << dump_index << ".texture" << texture_index
                           << (texture.format ==
                                       shift::xbox::CapturedVulkanTexture::Format::R8
                                   ? ".r8"
                                   : ".rgba8");
              std::ofstream texture_file(texture_path.str(),
                                        std::ios::binary | std::ios::trunc);
              texture_file.write(
                  reinterpret_cast<const char*>(texture.pixels.data()),
                  static_cast<std::streamsize>(texture.pixels.size()));
              if (texture_file) {
                dump << "    raw_texture_dump=" << texture_path.str() << "\n";
              } else {
                dump << "    raw_texture_dump_failed=" << texture_path.str()
                     << "\n";
              }
            }
          }
        } else {
          dump << "  texture: unused\n";
        }
        AppendShaderConstantDump(&dump, constants,
                                 vertex_translation.float_constant_registers,
                                 true);
        AppendShaderConstantDump(&dump, constants,
                                 pixel_translation.float_constant_registers,
                                 false);
        dump << "  pixel boolean constants valid="
             << constants.pixel_boolean_constants_valid
             << " b128=" << constants.pixel_b128
             << " b129=" << constants.pixel_b129
             << "\n  translated vertex GLSL:\n"
             << vertex_translation.glsl << "  translated pixel GLSL:\n"
             << pixel_translation.glsl;
        REXLOG_INFO("{}", dump.str());
      }
    }
    *prepared_draw = std::move(prepared);
    scratch_payload_guard.dismiss();
    return true;
  }

  uint32_t ReadRegister(uint32_t address) {
    const uint32_t index = (address & 0xFFFFu) / sizeof(uint32_t);
    if (index == kVblankStatusRegister) return 1u;
    if (index == kVgtEventInitiatorRegister) {
      return event_initiator_.load(std::memory_order_acquire);
    }
    if (index == kCoherSizeHostRegister ||
        index == kCoherBaseHostRegister ||
        index == kCoherStatusHostRegister) {
      std::lock_guard<std::mutex> lock(guest_coherency_mutex_);
      if (index == kCoherSizeHostRegister) return coher_size_host_;
      if (index == kCoherBaseHostRegister) return coher_base_host_;
      return coher_status_host_;
    }
    std::lock_guard<std::mutex> lock(ring_mutex_);
    if (index == kRingReadPointerRegister) return ring_read_pointer_;
    if (index == kRingWritePointerRegister) return ring_write_pointer_;
    return 0;
  }

  bool DispatchGuestInterrupt(uint32_t source, uint32_t cpu,
                              rex::system::XHostThread* expected_thread) {
    uint32_t callback = 0;
    uint32_t callback_data = 0;
    {
      std::lock_guard<std::mutex> lock(interrupt_mutex_);
      callback = interrupt_callback_;
      callback_data = interrupt_callback_data_;
    }
    if (!callback) return false;
    if (!function_dispatcher_ || !expected_thread) {
      REXLOG_WARN("shift-native: cannot dispatch guest GPU interrupt without "
                  "the ReXGlue host-thread context");
      return false;
    }
    auto* thread = rex::system::XThread::GetCurrentThread();
    if (thread != expected_thread) {
      REXLOG_ERROR("shift-native: GPU interrupt left its ReXGlue host thread");
      return false;
    }
    thread->SetActiveCpu(static_cast<uint8_t>(cpu));
    uint64_t args[] = {source, callback_data};
    function_dispatcher_->ExecuteInterrupt(thread->thread_state(), callback, args, 2);
    return true;
  }

  void VblankWorkerLoop() {
    rex::system::X_VIDEO_MODE video_mode{};
    rex::kernel::xboxkrnl::VdQueryVideoMode(&video_mode);
    const double refresh_rate_hz =
        std::max(1.0, double(float(video_mode.refresh_rate)));
    const uint64_t guest_tick_frequency =
        rex::chrono::Clock::guest_tick_frequency();
    const uint64_t vblank_interval_ticks = std::max(
        uint64_t{1}, uint64_t(double(guest_tick_frequency) / refresh_rate_hz));
    uint64_t last_vblank_tick = rex::chrono::Clock::QueryGuestTickCount();
    uint32_t dispatched_vblanks = 0;
    while (vblank_worker_running_.load(std::memory_order_acquire)) {
      const uint64_t current_tick = rex::chrono::Clock::QueryGuestTickCount();
      while (vblank_worker_running_.load(std::memory_order_acquire) &&
             current_tick - last_vblank_tick >= vblank_interval_ticks) {
        last_vblank_tick += vblank_interval_ticks;
        if (DispatchGuestInterrupt(0u, 2u, vblank_host_worker_.get()) &&
            dispatched_vblanks < 3u) {
          ++dispatched_vblanks;
          REXLOG_INFO("shift-native: dispatched guest vblank callback {} "
                      "at {:.3f} Hz",
                      dispatched_vblanks, refresh_rate_hz);
        }
      }
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
  }

  void ApplyCoherencyRegisterWrite(uint32_t index, uint32_t value) {
    if (index != kCoherSizeHostRegister &&
        index != kCoherBaseHostRegister &&
        index != kCoherStatusHostRegister) {
      return;
    }
    std::lock_guard<std::mutex> lock(guest_coherency_mutex_);
    if (index == kCoherSizeHostRegister) {
      coher_size_host_ = value;
    } else if (index == kCoherBaseHostRegister) {
      coher_base_host_ = value;
    } else {
      // Xenos marks host data dirty on every COHER_STATUS_HOST write. The
      // captured register wait clears it only after prior renderer work drains.
      coher_status_host_ = value | kCoherStatusHostDirty;
    }
    ++coherency_generation_;
  }

  void ApplyScratchRegisterWrite(uint32_t index, uint32_t value) {
    if (index == rex::graphics::XE_GPU_REG_SCRATCH_ADDR) {
      scratch_address_.store(value, std::memory_order_release);
      return;
    }
    if (index == rex::graphics::XE_GPU_REG_SCRATCH_UMSK) {
      scratch_umsk_.store(value, std::memory_order_release);
      return;
    }
    if (index < rex::graphics::XE_GPU_REG_SCRATCH_REG0 ||
        index > rex::graphics::XE_GPU_REG_SCRATCH_REG7) {
      return;
    }

    const uint32_t scratch_index =
        index - rex::graphics::XE_GPU_REG_SCRATCH_REG0;
    const uint32_t umsk = scratch_umsk_.load(std::memory_order_acquire);
    if ((umsk & (uint32_t{1} << scratch_index)) == 0u) return;

    const uint64_t guest_address =
        static_cast<uint64_t>(scratch_address_.load(std::memory_order_acquire)) +
        static_cast<uint64_t>(scratch_index) * sizeof(uint32_t);
    if (guest_address > kPhysicalAddressMask ||
        !physical_span_valid(static_cast<uint32_t>(guest_address),
                             sizeof(uint32_t))) {
      REXLOG_WARN(
          "shift-native: ignored scratch register {} writeback to invalid guest "
          "address {:08X}",
          scratch_index, static_cast<uint32_t>(guest_address));
      return;
    }
    auto* destination = memory_->TranslatePhysical<uint32_t*>(
        static_cast<uint32_t>(guest_address));
    if (!destination) {
      REXLOG_WARN(
          "shift-native: could not translate scratch register {} writeback "
          "address {:08X}",
          scratch_index, static_cast<uint32_t>(guest_address));
      return;
    }

    constexpr auto kScratchEndian = rex::graphics::xenos::Endian::k8in32;
    const uint32_t previous_value = rex::graphics::xenos::GpuSwap(
        __atomic_load_n(destination, __ATOMIC_ACQUIRE), kScratchEndian);
    __atomic_store_n(destination,
                     rex::graphics::xenos::GpuSwap(value, kScratchEndian),
                     __ATOMIC_RELEASE);
    static std::atomic<uint32_t> scratch_write_log_count{0};
    const uint32_t log_index =
        scratch_write_log_count.fetch_add(1, std::memory_order_relaxed);
    if (log_index < 16u) {
      REXLOG_INFO(
          "shift-native: SCRATCH_REG{} writeback guest={:08X} umsk={:08X} "
          "guest_value={:08X}->{:08X}",
          scratch_index, static_cast<uint32_t>(guest_address), umsk,
          previous_value, value);
    }
  }

  bool WaitForGuestMemoryCoherency(std::string* error) {
    bool completed = false;
    const auto drain = [this, &completed, error] {
      completed = texture_cache_.wait_for_guest_memory_coherency(error);
    };
    if (app_context_) {
      app_context_->CallInUIThreadSynchronous(drain);
    } else {
      drain();
    }
    return completed;
  }

  void NotifyWriteRegister(uint32_t address, uint32_t value) {
    const uint32_t index = (address & 0xFFFFu) / sizeof(uint32_t);
    ApplyScratchRegisterWrite(index, value);
    ApplyCoherencyRegisterWrite(index, value);
    if (index != kRingWritePointerRegister) return;

    uint32_t previous_write_pointer = 0;
    uint32_t read_pointer = 0;
    uint32_t ring_dwords = 0;
    uint64_t ring_generation = 0;
    {
      std::lock_guard<std::mutex> lock(ring_mutex_);
      if (!ring_initialized_ || !memory_) return;
      ring_dwords = static_cast<uint32_t>(ring_byte_length_ / sizeof(uint32_t));
      if (value >= ring_dwords) {
        REXLOG_WARN("shift-native: ignored out-of-range CP_RB_WPTR {:08X}", value);
        return;
      }
      previous_write_pointer = ring_write_pointer_;
      read_pointer = ring_read_pointer_;
      ring_generation = ring_generation_;
      ring_write_pointer_ = value;
    }
    if (GuestRingTraceEnabled()) {
      const uint32_t trace_record = NextGuestRingTraceRecord();
      if (trace_record < kMaxGuestRingTraceRecords) {
        const uint32_t distance = value >= read_pointer
            ? value - read_pointer
            : ring_dwords - read_pointer + value;
        REXLOG_INFO("shift-native: ring trace wptr #{} mmio={:08X} "
                    "previous={} new={} rptr={} modular-distance={} "
                    "ring-dwords={} generation={}",
                    trace_record, address, previous_write_pointer, value,
                    read_pointer, distance, ring_dwords, ring_generation);
      }
    }
    ring_changed_.notify_one();
  }

  void RingWorkerLoop() {
    shift::xbox::GuestRasterRegisterState raster_register_state;
    shift::xbox::CapturedXboxShaderRegisterState shader_register_state;
    std::vector<uint8_t> vertex_shader_program;
    std::vector<uint8_t> pixel_shader_program;
    std::vector<shift::xbox::CapturedVulkanDraw> frame_draws;
    std::vector<uint32_t> frame_draw_packet_indices;
    const auto recycle_frame_draws = [this, &frame_draws,
                                      &frame_draw_packet_indices] {
      for (size_t draw_slot = 0; draw_slot < frame_draws.size(); ++draw_slot) {
        for (auto& texture : frame_draws[draw_slot].textures) {
          if (texture.format != shift::xbox::CapturedVulkanTexture::Format::R8) {
            continue;
          }
          r8_upload_scratch_.release(
              {draw_slot, texture.fetch_constant_index,
               texture.width, texture.height},
              &texture.pixels);
        }
      }
      frame_draws.clear();
      frame_draw_packet_indices.clear();
    };
    shift::xbox::CapturedVulkanCopy frame_copy{};
    bool frame_copy_ready = false;
    uint64_t observed_ring_generation = 0;
    uint32_t guest_swap_counter = 0;
    uint32_t last_guest_swap_width = 0;
    uint32_t last_guest_swap_height = 0;
    uint32_t readback_frame_counter = 0;
    std::vector<std::string> logged_unresolved_draw_reasons;
    std::vector<std::string> logged_draw_decode_reasons;
#if defined(__ANDROID__) && !defined(NDEBUG)
    constexpr uint32_t kAndroidDebugReadbackFrame =
        SHIFT_NATIVE_VULKAN_DEBUG_READBACK_FRAME;
#else
    constexpr uint32_t kAndroidDebugReadbackFrame = 0u;
#endif
    uint32_t selected_draw_dump_frame = 0;
    if (const char* frame_text =
            std::getenv("SHIFT_NATIVE_VULKAN_DUMP_DRAW_FRAME");
        frame_text && *frame_text &&
        !parse_positive_environment_frame(frame_text,
                                          &selected_draw_dump_frame)) {
      REXLOG_WARN("shift-native: ignoring invalid "
                  "SHIFT_NATIVE_VULKAN_DUMP_DRAW_FRAME value '{}'",
                  frame_text);
    }
    std::map<uint32_t, size_t> traced_indirect_buffers;
    const auto trace_indirect_buffers = [this, &traced_indirect_buffers](
        const shift::xbox::ExpandedGuestCommandStream& stream) {
      constexpr size_t kMaxBuffers = 8;
      constexpr size_t kMaxBytesPerBuffer = 4096;
      constexpr size_t kDwordsPerLogLine = 16;
      for (const auto& resolved : stream.packets) {
        if (resolved.nesting_depth == 0 ||
            resolved.source_guest_buffer_byte_length == 0 ||
            traced_indirect_buffers.find(resolved.source_guest_address) !=
                traced_indirect_buffers.end()) {
          continue;
        }
        if (traced_indirect_buffers.size() >= kMaxBuffers) break;
        const size_t source_bytes = resolved.source_guest_buffer_byte_length;
        traced_indirect_buffers.emplace(resolved.source_guest_address,
                                        source_bytes);
        const size_t dump_bytes = std::min(source_bytes, kMaxBytesPerBuffer);
        const uint8_t* bytes = nullptr;
        size_t available_bytes = 0;
        if (!ReadGuestMemory(this, resolved.source_guest_address, dump_bytes,
                             &bytes, &available_bytes) ||
            available_bytes < dump_bytes) {
          REXLOG_WARN("shift-native: ring trace IB dump failed source={:08X} "
                      "source-bytes={} requested-bytes={} available-bytes={}",
                      resolved.source_guest_address, source_bytes, dump_bytes,
                      available_bytes);
          continue;
        }
        REXLOG_INFO("shift-native: ring trace IB dump #{} source={:08X} "
                    "depth={} source-bytes={} dumped-bytes={} truncated={}",
                    traced_indirect_buffers.size() - 1,
                    resolved.source_guest_address, resolved.nesting_depth,
                    source_bytes, dump_bytes, dump_bytes < source_bytes);
        for (size_t byte_offset = 0; byte_offset < dump_bytes;
             byte_offset += kDwordsPerLogLine * sizeof(uint32_t)) {
          std::ostringstream raw_dwords;
          const size_t dwords = std::min(
              kDwordsPerLogLine,
              (dump_bytes - byte_offset) / sizeof(uint32_t));
          for (size_t dword = 0; dword < dwords; ++dword) {
            raw_dwords << (dword == 0 ? "" : ",") << std::hex
                       << ReadGuestDword(bytes + byte_offset +
                                         dword * sizeof(uint32_t));
          }
          REXLOG_INFO("shift-native: ring trace IB data source={:08X} "
                      "byte-offset={} raw-dwords={}",
                      resolved.source_guest_address, byte_offset,
                      raw_dwords.str());
        }
      }
    };
    for (;;) {
      uint32_t read_pointer = 0;
      uint32_t write_pointer = 0;
      uint32_t ring_guest_address = 0;
      size_t ring_byte_length = 0;
      uint64_t ring_generation = 0;
      {
        std::unique_lock<std::mutex> lock(ring_mutex_);
        ring_changed_.wait(lock, [this] {
          return ring_worker_shutdown_ ||
                 (ring_initialized_ && ring_read_pointer_ != ring_write_pointer_);
        });
        if (ring_worker_shutdown_) return;
        read_pointer = ring_read_pointer_;
        write_pointer = ring_write_pointer_;
        ring_guest_address = ring_guest_address_;
        ring_byte_length = ring_byte_length_;
        ring_generation = ring_generation_;
      }
      if (GuestRingTraceEnabled()) {
        const uint32_t trace_record = NextGuestRingTraceRecord();
        if (trace_record < kMaxGuestRingTraceRecords) {
          const uint32_t ring_dwords =
              static_cast<uint32_t>(ring_byte_length / sizeof(uint32_t));
          const uint32_t distance = write_pointer >= read_pointer
              ? write_pointer - read_pointer
              : ring_dwords - read_pointer + write_pointer;
          REXLOG_INFO("shift-native: ring trace wake #{} rptr={} wptr={} "
                      "modular-distance={} ring-dwords={} generation={}",
                      trace_record, read_pointer, write_pointer, distance,
                      ring_dwords, ring_generation);
        }
      }
      if (ring_generation != observed_ring_generation) {
        raster_register_state.reset();
        shader_register_state.reset();
        vertex_shader_program.clear();
        pixel_shader_program.clear();
        recycle_frame_draws();
        frame_copy = {};
        frame_copy_ready = false;
        last_guest_swap_width = 0;
        last_guest_swap_height = 0;
        observed_ring_generation = ring_generation;
      }

      uint32_t interrupt_packets = 0;
      uint32_t dispatched_interrupt_callbacks = 0;
      ReadPointerWriteback read_pointer_writeback{};
      try {
        std::atomic_thread_fence(std::memory_order_acquire);
        const uint8_t* ring_bytes =
            memory_->TranslatePhysical<const uint8_t*>(ring_guest_address);
        shift::xbox::GuestRingBatch batch{};
        std::string error;
        const bool snapshotted = shift::xbox::snapshot_guest_ring_batch(
            ring_bytes, ring_byte_length, read_pointer, write_pointer, &batch, &error);
        if (snapshotted) {
          // The root ring bytes are now owned by `batch`; release those slots
          // before parsing nested work, which may stop at a guest memory wait.
          read_pointer_writeback = PublishReadPointer(
              ring_generation, read_pointer, batch.next_read_pointer_dwords,
              "snapshot");
        }
        shift::xbox::ExpandedGuestCommandStream expanded{};
        const bool expanded_ok = snapshotted && shift::xbox::expand_guest_indirect_buffers(
            batch, ReadGuestMemory, this, &expanded, &error);
        if (GuestRingTraceEnabled()) {
          const uint32_t trace_record = NextGuestRingTraceRecord();
          if (trace_record < kMaxGuestRingTraceRecords) {
            REXLOG_INFO("shift-native: ring trace snapshot #{} rptr={} wptr={} "
                        "ring-bytes={} snapshot-ok={} batch-bytes={} "
                        "expand-ok={} packets={} error={}",
                        trace_record, read_pointer, write_pointer,
                        ring_byte_length, snapshotted, batch.bytes.size(),
                        expanded_ok, expanded.packets.size(),
                        error.empty() ? "none" : error);
          }
          if (expanded_ok) trace_indirect_buffers(expanded);
        }

        uint32_t decoded_draws = 0;
        uint32_t draws_with_raster_state = 0;
        uint32_t draws_elided_as_noops = 0;
        uint32_t draws_with_both_shader_programs = 0;
        uint32_t draws_with_captured_shader_inputs = 0;
        uint32_t draws_with_project_shader_translation = 0;
        uint32_t draws_with_resolved_resource_payloads = 0;
        uint32_t draws_with_unresolved_resource_payloads = 0;
        uint32_t recognized_intermediate_copies = 0;
        uint32_t loaded_shader_programs = 0;
        uint32_t unresolved_shader_programs = 0;
        uint32_t loaded_immediate_shader_programs = 0;
        uint32_t unresolved_immediate_shader_programs = 0;
        uint32_t loaded_constant_spans = 0;
        uint32_t unresolved_constant_spans = 0;
        uint32_t unsupported_draws = 0;
        uint32_t decoded_swaps = 0;
        uint32_t submitted_frames = 0;
        uint32_t raw_register_writes = 0;
        std::array<uint32_t, 256> type3_opcode_counts{};
        std::array<uint32_t, 256> draw_source_primitive_counts{};
        std::map<uint32_t, uint32_t> draw_index_count_counts;
        std::array<bool, 2> type3_packet_sample_logged{};
        bool logged_autoindex_state = false;
        uint32_t rectangle_raster_diagnostics = 0;
        if (expanded_ok) {
          for (const shift::xbox::ResolvedGuestPacket& resolved : expanded.packets) {
            const shift::xbox::PacketSpan& packet = resolved.packet;
            if (packet.type == shift::xbox::PacketType::Type3) {
              ++type3_opcode_counts[packet.opcode & 0xFFu];
            }
            const uint8_t* packet_bytes = nullptr;
            if (resolved.nesting_depth == 0) {
              packet_bytes = batch.bytes.data() + packet.byte_offset;
            } else {
              const uint8_t* source_bytes = nullptr;
              size_t source_available = 0;
              if (!ReadGuestMemory(this, resolved.source_guest_address,
                                   resolved.source_guest_buffer_byte_length,
                                   &source_bytes, &source_available) ||
                  source_available < resolved.source_guest_buffer_byte_length) {
                ++unsupported_draws;
                continue;
              }
              packet_bytes = source_bytes + packet.byte_offset;
            }

            if (GuestRingTraceEnabled() &&
                packet.type == shift::xbox::PacketType::Type3 &&
                IsGuestMemoryWriteCandidateOpcode(packet.opcode)) {
              static std::array<std::atomic<uint32_t>, 256> candidate_log_counts{};
              const uint32_t log_index = candidate_log_counts[packet.opcode].fetch_add(
                  1, std::memory_order_relaxed);
              if (log_index < 16u) {
                std::ostringstream raw_dwords;
                const size_t dword_count = packet.byte_length / sizeof(uint32_t);
                for (size_t dword = 0;
                     dword < std::min(dword_count, size_t{16}); ++dword) {
                  raw_dwords << (dword == 0 ? "" : ",") << std::hex
                             << ReadGuestDword(packet_bytes +
                                               dword * sizeof(uint32_t));
                }
                REXLOG_INFO(
                    "shift-native: memory-write candidate opcode={:02X} #{} "
                    "source={:08X} depth={} byte-offset={} bytes={} "
                    "raw-dwords={}",
                    packet.opcode, log_index, resolved.source_guest_address,
                    resolved.nesting_depth, packet.byte_offset,
                    packet.byte_length, raw_dwords.str());
              }
            }

            if (packet.type == shift::xbox::PacketType::Type3 &&
                packet.opcode == 0x46u) {
              static std::atomic<uint32_t> event_write_log_count{0};
              const uint32_t event_write_log_index =
                  event_write_log_count.fetch_add(1, std::memory_order_relaxed);
              if (event_write_log_index < 16u) {
                std::ostringstream raw_dwords;
                const size_t dword_count = packet.byte_length / sizeof(uint32_t);
                for (size_t dword = 0;
                     dword < std::min(dword_count, size_t{8}); ++dword) {
                  raw_dwords << (dword == 0 ? "" : ",") << std::hex
                             << ReadGuestDword(packet_bytes +
                                               dword * sizeof(uint32_t));
                }
                REXLOG_INFO(
                    "shift-native: observed PM4_EVENT_WRITE #{} source={:08X} "
                    "depth={} byte-offset={} bytes={} raw-dwords={}",
                    event_write_log_index, resolved.source_guest_address,
                    resolved.nesting_depth, packet.byte_offset,
                    packet.byte_length, raw_dwords.str());
              }
            }

            if (packet.type == shift::xbox::PacketType::Type3 &&
                (packet.opcode == 0x2Bu || packet.opcode == 0x36u)) {
              if (packet.opcode == 0x36u && packet.byte_length >= 8u) {
                const uint32_t initiator = ReadGuestDword(packet_bytes + 4u);
                const uint32_t primitive_type = initiator & 0x3Fu;
                const uint32_t source_select = (initiator >> 6) & 0x3u;
                const uint32_t index_count = initiator >> 16;
                ++draw_source_primitive_counts[source_select * 64u +
                                               primitive_type];
                ++draw_index_count_counts[index_count];
                if (source_select == 2u && !logged_autoindex_state) {
                  logged_autoindex_state = true;
                  shift::xbox::CapturedShaderConstants constants{};
                  std::array<uint32_t, 2> vertex_descriptor{};
                  std::array<uint32_t, 6> texture_descriptor{};
                  shift::xbox::CapturedVertexFetch vertex_fetch{};
                  shift::xbox::CapturedTextureFetch texture_fetch{};
                  shift::xbox::CapturedTextureSampling texture_sampling{};
                  shift::xbox::CapturedRasterRegisters raster_registers{};
                  shift::xbox::CapturedRasterState raster_state{};
                  std::string state_error;
                  std::string vertex_error;
                  std::string texture_error;
                  std::string sampling_error;
                  std::string raster_error;
                  const bool shader_state_ready =
                      shader_register_state.snapshot(
                          &constants, &vertex_descriptor, &texture_descriptor,
                          &state_error);
                  const bool vertex_fetch_ready =
                      shader_state_ready &&
                      shift::xbox::decode_captured_vertex_fetch(
                          vertex_descriptor.data(), &vertex_fetch,
                          &vertex_error);
                  const bool texture_fetch_ready =
                      shader_state_ready &&
                      shift::xbox::decode_captured_texture_fetch(
                          texture_descriptor.data(), &texture_fetch,
                          &texture_error);
                  const bool texture_sampling_ready =
                      texture_fetch_ready &&
                      shift::xbox::decode_captured_texture_sampling(
                          texture_fetch, &texture_sampling, &sampling_error);
                  const bool raster_state_ready =
                      raster_register_state.snapshot(&raster_registers,
                                                     &raster_error) &&
                      shift::xbox::decode_captured_raster_state(
                          raster_registers, &raster_state, &raster_error,
                          last_guest_swap_width, last_guest_swap_height);
                  std::vector<shift::xbox::CapturedShaderControlFlow>
                      pixel_control_flow;
                  std::string pixel_control_flow_error;
                  const bool pixel_control_flow_ready =
                      !pixel_shader_program.empty() &&
                      shift::xbox::decode_captured_shader_control_flow(
                          pixel_shader_program.data(),
                          pixel_shader_program.size(), &pixel_control_flow,
                          &pixel_control_flow_error);
                  const auto uses_pixel_bool = [&pixel_control_flow](
                                                   uint32_t index) {
                    return std::any_of(
                        pixel_control_flow.begin(), pixel_control_flow.end(),
                        [index](const auto &entry) {
                          return entry.opcode ==
                                     shift::xbox::ShaderControlFlowOpcode::
                                         ConditionalJump &&
                                 entry.bool_constant == index;
                        });
                  };
                  std::vector<shift::xbox::CapturedShaderControlFlow>
                      vertex_control_flow;
                  std::vector<shift::xbox::CapturedShaderInstructionSchedule>
                      vertex_schedule;
                  std::string vertex_schedule_error;
                  const bool vertex_schedule_ready =
                      !vertex_shader_program.empty() &&
                      shift::xbox::decode_captured_shader_control_flow(
                          vertex_shader_program.data(),
                          vertex_shader_program.size(), &vertex_control_flow,
                          &vertex_schedule_error) &&
                      shift::xbox::schedule_captured_shader_instructions(
                          vertex_control_flow, vertex_shader_program.size(),
                          &vertex_schedule, &vertex_schedule_error);
                  std::ostringstream vertex_fetch_summary;
                  bool first_vertex_fetch = true;
                  if (vertex_schedule_ready) {
                    for (const auto &scheduled : vertex_schedule) {
                      if (scheduled.kind !=
                          shift::xbox::ShaderScheduledInstructionKind::Fetch) {
                        continue;
                      }
                      const size_t offset =
                          static_cast<size_t>(scheduled.address) * 12u;
                      shift::xbox::CapturedShaderFetchInstruction fetch{};
                      if (offset + 12u > vertex_shader_program.size() ||
                          !shift::xbox::
                              decode_captured_shader_fetch_instruction(
                                  vertex_shader_program.data() + offset, 12u,
                                  &fetch, &vertex_schedule_error)) {
                        vertex_fetch_summary << "invalid-fetch";
                        break;
                      }
                      if (fetch.kind !=
                              shift::xbox::CapturedShaderFetchKind::VertexFull &&
                          fetch.kind !=
                              shift::xbox::CapturedShaderFetchKind::VertexMini) {
                        continue;
                      }
                      if (!first_vertex_fetch)
                        vertex_fetch_summary << ',';
                      vertex_fetch_summary << (fetch.kind ==
                                                       shift::xbox::CapturedShaderFetchKind::VertexMini
                                                   ? "mini"
                                                   : "full")
                                            << "(constant=" << fetch.fetch_constant_index
                                            << "/format=" << fetch.vertex_format
                                            << "/stride=" << fetch.vertex_stride
                                            << "/offset=" << fetch.vertex_offset
                                            << "/src=" << fetch.source_register
                                            << "/dst=" << fetch.destination_register
                                            << "/swiz=" << fetch.destination_swizzle
                                            << ')';
                      first_vertex_fetch = false;
                    }
                  }
                  const char *first_error =
                      !shader_state_ready       ? state_error.c_str()
                      : !vertex_fetch_ready     ? vertex_error.c_str()
                      : !texture_fetch_ready    ? texture_error.c_str()
                      : !texture_sampling_ready ? sampling_error.c_str()
                      : !raster_state_ready     ? raster_error.c_str()
                                                : "none";
                  REXLOG_DEBUG("shift-native: AutoIndex state snapshot: "
                               "shader-registers={}, "
                               "vertex-fetch={} ({} bytes), texture-fetch={} "
                               "({}x{}, {} bytes), "
                               "texture-sampling={}, raster-state={} ({}x{}), "
                               "vertex-shader-bytes={}, pixel-shader-bytes={}, "
                               "first-error={}",
                               shader_state_ready, vertex_fetch_ready,
                               vertex_fetch.byte_length, texture_fetch_ready,
                               texture_fetch.width, texture_fetch.height,
                               texture_fetch.byte_length,
                               texture_sampling_ready, raster_state_ready,
                               raster_state.width, raster_state.height,
                               vertex_shader_program.size(),
                               pixel_shader_program.size(), first_error);
                  if (raster_register_state.snapshot(&raster_registers,
                                                     &raster_error)) {
                    REXLOG_DEBUG(
                        "shift-native: captured raster registers: "
                        "surface={:08x}, color={:08x}, depth={:08x}, mode={:08x}, "
                        "setup={:08x}, "
                        "mask={:08x}, viewport=[{:08x},{:08x},{:08x},{:08x}], "
                        "screen-scissor=[{:08x},{:08x}], "
                        "window-scissor=[{:08x},{:08x}], window-offset={:08x}, "
                        "blend={:08x}, depth-control={:08x}",
                        raster_registers.surface_info,
                        raster_registers.color_info, raster_registers.depth_info,
                        raster_registers.mode_control,
                        raster_registers.setup_mode_control,
                        raster_registers.color_mask,
                        raster_registers.viewport_x_scale,
                        raster_registers.viewport_x_offset,
                        raster_registers.viewport_y_scale,
                        raster_registers.viewport_y_offset,
                        raster_registers.screen_scissor_tl,
                        raster_registers.screen_scissor_br,
                        raster_registers.window_scissor_tl,
                        raster_registers.window_scissor_br,
                        raster_registers.window_offset,
                        raster_registers.blend_control_0,
                        raster_registers.depth_control);
                  }
                  REXLOG_DEBUG(
                      "shift-native: AutoIndex pixel control flow: decoded={}, "
                      "uses-b128={}, uses-b129={}, error={}",
                      pixel_control_flow_ready, uses_pixel_bool(128u),
                      uses_pixel_bool(129u),
                      pixel_control_flow_error.empty()
                          ? "none"
                          : pixel_control_flow_error);
                  REXLOG_DEBUG(
                      "shift-native: AutoIndex vertex fetch contracts: "
                      "scheduled={}, "
                      "fetches=[{}], error={}",
                      vertex_schedule_ready, vertex_fetch_summary.str(),
                      vertex_schedule_error.empty() ? "none"
                                                    : vertex_schedule_error);
                }
              }
              const size_t sample_index = packet.opcode == 0x2Bu ? 0u : 1u;
              if (!type3_packet_sample_logged[sample_index]) {
                type3_packet_sample_logged[sample_index] = true;
                std::ostringstream sample;
                sample << std::hex << packet.opcode << std::dec << '/'
                       << packet.byte_length << ':';
                const size_t word_count = std::min(packet.byte_length / 4u, size_t{12});
                for (size_t word = 0; word < word_count; ++word) {
                  sample << (word ? "," : "") << std::hex
                         << ReadGuestDword(packet_bytes + word * 4u) << std::dec;
                }
                REXLOG_DEBUG("shift-native: raw type3 packet sample {}",
                             sample.str());
              }
            }

            if (packet.type == shift::xbox::PacketType::Type3 &&
                packet.opcode == 0x58u) {
              shift::xbox::DecodedEventWriteShd event{};
              if (!shift::xbox::decode_guest_event_write_shd(
                      packet_bytes, packet.byte_length, &event, &error) ||
                  !physical_span_valid(event.guest_address,
                                       sizeof(uint32_t))) {
                ++unsupported_draws;
                REXLOG_WARN("shift-native: rejected EVENT_WRITE_SHD packet: {}",
                            error.empty() ? "guest address is outside physical memory"
                                          : error);
                continue;
              }
              auto* destination =
                  memory_->TranslatePhysical<uint32_t*>(event.guest_address);
              if (!destination) {
                ++unsupported_draws;
                REXLOG_WARN("shift-native: could not translate EVENT_WRITE_SHD guest "
                            "address {:08X}",
                            event.guest_address);
                continue;
              }
              const uint32_t data_value = shift::xbox::event_write_shd_value(
                  event, guest_swap_counter);
              const uint32_t stored_value = rex::graphics::xenos::GpuSwap(
                  data_value,
                  static_cast<rex::graphics::xenos::Endian>(event.endian_mode));
              const uint32_t previous_guest_value =
                  rex::memory::load_and_swap<uint32_t>(destination);
              rex::memory::store(destination, stored_value);
              const uint32_t stored_guest_value =
                  rex::memory::load_and_swap<uint32_t>(destination);
              event_initiator_.store(event.initiator & 0x3Fu,
                                     std::memory_order_release);
              static std::atomic<uint32_t> event_write_log_count{0};
              const uint32_t event_log_index = event_write_log_count.fetch_add(
                  1, std::memory_order_relaxed);
              if (event_log_index < 16u) {
                REXLOG_INFO(
                    "shift-native: EVENT_WRITE_SHD #{} initiator={:08X} "
                    "guest={:08X} endian={} packet_value={:08X} "
                    "swap_counter={} guest_value={:08X}->{:08X} "
                    "source={:08X} depth={} byte-offset={}",
                    event_log_index, event.initiator, event.guest_address,
                    event.endian_mode, event.value, guest_swap_counter,
                    previous_guest_value, stored_guest_value,
                    resolved.source_guest_address, resolved.nesting_depth,
                    packet.byte_offset);
              }
            } else if (packet.type == shift::xbox::PacketType::Type3 &&
                       packet.opcode == 0x3Cu) {
              shift::xbox::DecodedWaitRegMem wait{};
              if (!shift::xbox::decode_captured_wait_reg_mem(
                      packet_bytes, packet.byte_length, &wait, &error)) {
                ++unsupported_draws;
                REXLOG_WARN("shift-native: rejected WAIT_REG_MEM packet: {}",
                            error);
                continue;
              }
              const bool coherency_register_wait =
                  !wait.memory && wait.control == 0x03u &&
                  wait.poll_address == kCoherStatusHostRegister &&
                  wait.compare == shift::xbox::GuestWaitCompare::Equal &&
                  wait.reference == 0u &&
                  wait.mask == kCoherStatusHostDirty &&
                  wait.poll_interval == 8u;
              const bool captured_memory_wait =
                  wait.memory &&
                  wait.compare == shift::xbox::GuestWaitCompare::Equal &&
                  wait.mask == UINT32_MAX && wait.endian_mode == 2u &&
                  wait.poll_interval == 0x100u;
              if (!coherency_register_wait && !captured_memory_wait) {
                ++unsupported_draws;
                REXLOG_WARN(
                    "shift-native: unsupported WAIT_REG_MEM form control={:08X} "
                    "poll-address={:08X} reference={:08X} mask={:08X} "
                    "memory={} compare={} endian={} interval={:08X} "
                    "source={:08X} depth={} byte-offset={}",
                    wait.control, wait.poll_address, wait.reference, wait.mask,
                    wait.memory,
                    static_cast<uint32_t>(wait.compare), wait.endian_mode,
                    wait.poll_interval, resolved.source_guest_address,
                    resolved.nesting_depth, packet.byte_offset);
                continue;
              }
              uint32_t* poll_word = nullptr;
              if (wait.memory) {
                if (!physical_span_valid(wait.guest_address, sizeof(uint32_t))) {
                  ++unsupported_draws;
                  REXLOG_WARN(
                      "shift-native: WAIT_REG_MEM address {:08X} is outside "
                      "physical memory",
                      wait.guest_address);
                  continue;
                }
                poll_word = memory_->TranslatePhysical<uint32_t*>(
                    wait.guest_address);
                if (!poll_word) {
                  ++unsupported_draws;
                  REXLOG_WARN(
                      "shift-native: could not translate WAIT_REG_MEM address {:08X}",
                      wait.guest_address);
                  continue;
                }
              }
              const auto wait_started = std::chrono::steady_clock::now();
              static std::atomic<uint32_t> wait_log_count{0};
              const uint32_t wait_log_index =
                  wait_log_count.fetch_add(1, std::memory_order_relaxed);
              if (wait_log_index < 16u) {
                if (wait.memory) {
                  REXLOG_INFO(
                      "shift-native: entering captured WAIT_REG_MEM guest={:08X} "
                      "reference={:08X} mask={:08X} endian={} compare={} "
                      "source={:08X} depth={} byte-offset={}",
                      wait.guest_address, wait.reference, wait.mask,
                      wait.endian_mode, static_cast<uint32_t>(wait.compare),
                      resolved.source_guest_address, resolved.nesting_depth,
                      packet.byte_offset);
                } else {
                  REXLOG_INFO(
                      "shift-native: entering captured COHER_STATUS_HOST wait "
                      "source={:08X} depth={} byte-offset={}",
                      resolved.source_guest_address, resolved.nesting_depth,
                      packet.byte_offset);
                }
              }
              uint32_t poll_count = 0;
              uint32_t wait_value_samples = 0;
              uint32_t previous_wait_value = 0;
              bool have_previous_wait_value = false;
              for (;;) {
                uint32_t observed_value = 0;
                uint32_t coher_base = 0;
                uint32_t coher_size = 0;
                uint32_t raw_value = 0;
                if (wait.memory) {
                  raw_value = __atomic_load_n(poll_word, __ATOMIC_ACQUIRE);
                  observed_value = rex::graphics::xenos::GpuSwap(
                      raw_value,
                      static_cast<rex::graphics::xenos::Endian>(wait.endian_mode));
                } else {
                  uint64_t generation = 0;
                  {
                    std::lock_guard<std::mutex> lock(guest_coherency_mutex_);
                    observed_value = coher_status_host_;
                    coher_base = coher_base_host_;
                    coher_size = coher_size_host_;
                    generation = coherency_generation_;
                  }
                  if ((observed_value & kCoherStatusHostDirty) != 0u) {
                    std::string coherency_error;
                    if (!WaitForGuestMemoryCoherency(&coherency_error)) {
                      REXLOG_ERROR(
                          "shift-native: failed to drain Vulkan work for "
                          "COHER_STATUS_HOST base={:08X} size={:08X}: {}",
                          coher_base, coher_size, coherency_error);
                      return;
                    }
                    {
                      std::lock_guard<std::mutex> lock(guest_coherency_mutex_);
                      if (generation != coherency_generation_) continue;
                      coher_status_host_ = 0;
                      ++coherency_generation_;
                      observed_value = coher_status_host_;
                    }
                    REXLOG_INFO(
                        "shift-native: completed captured COHER_STATUS_HOST wait "
                        "base={:08X} size={:08X} status=00000000",
                        coher_base, coher_size);
                  }
                }
                const bool wait_condition_met =
                    shift::xbox::captured_wait_reg_mem_condition_met(
                        wait, observed_value);
                const bool wait_value_changed =
                    !have_previous_wait_value ||
                    observed_value != previous_wait_value;
                const bool periodic_wait_sample =
                    poll_count != 0u && (poll_count % 1000u) == 0u;
                if (GuestRingTraceEnabled() && wait.memory &&
                    wait_value_samples < 8u &&
                    (wait_value_changed || periodic_wait_sample)) {
                  const auto elapsed =
                      std::chrono::duration_cast<std::chrono::milliseconds>(
                          std::chrono::steady_clock::now() - wait_started);
                  REXLOG_INFO(
                      "shift-native: ring trace WAIT_REG_MEM sample "
                      "guest={:08X} poll-address={:08X} reference={:08X} "
                      "mask={:08X} endian={} compare={} poll={} raw={:08X} "
                      "observed={:08X} condition={} elapsed_ms={} "
                      "source={:08X} byte-offset={}",
                      wait.guest_address, wait.poll_address, wait.reference,
                      wait.mask, wait.endian_mode,
                      static_cast<uint32_t>(wait.compare), poll_count,
                      raw_value, observed_value, wait_condition_met,
                      elapsed.count(), resolved.source_guest_address,
                      packet.byte_offset);
                  ++wait_value_samples;
                }
                previous_wait_value = observed_value;
                have_previous_wait_value = true;
                if (wait_condition_met) {
                  break;
                }
                {
                  std::lock_guard<std::mutex> lock(ring_mutex_);
                  if (ring_worker_shutdown_) return;
                }
                ++poll_count;
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
              }
              if (wait.memory && wait_log_index < 16u) {
                const auto elapsed = std::chrono::duration_cast<
                    std::chrono::milliseconds>(
                    std::chrono::steady_clock::now() - wait_started);
                REXLOG_INFO(
                    "shift-native: completed captured WAIT_REG_MEM guest={:08X} "
                    "reference={:08X} polls={} elapsed_ms={}",
                    wait.guest_address, wait.reference, poll_count,
                    elapsed.count());
              }
            } else if (packet.type == shift::xbox::PacketType::Type0 ||
                packet.type == shift::xbox::PacketType::Type1) {
              std::vector<shift::xbox::GuestRegisterWrite> writes;
              if (shift::xbox::decode_guest_register_writes(
                      packet_bytes, packet.byte_length, &writes, &error)) {
                raw_register_writes += static_cast<uint32_t>(writes.size());
                for (const shift::xbox::GuestRegisterWrite& write : writes) {
                  ApplyScratchRegisterWrite(write.register_index, write.value);
                  ApplyCoherencyRegisterWrite(write.register_index, write.value);
                  raster_register_state.apply(write);
                  shader_register_state.apply(write);
                }
              }
            } else if (packet.type == shift::xbox::PacketType::Type3 &&
                       packet.opcode == 0x2Fu) {
              shift::xbox::CapturedConstantLoad load{};
              const uint8_t* source_bytes = nullptr;
              size_t source_byte_length = 0;
              std::vector<shift::xbox::GuestRegisterWrite> writes;
              if (shift::xbox::decode_captured_constant_load(
                      packet_bytes, packet.byte_length, &load, &error) &&
                  ReadGuestMemory(this, load.guest_address, load.byte_length,
                                  &source_bytes, &source_byte_length) &&
                  source_byte_length >= load.byte_length &&
                  shift::xbox::decode_captured_constant_load_data(
                      load, source_bytes, load.byte_length, &writes, &error)) {
                for (const shift::xbox::GuestRegisterWrite& write : writes) {
                  ApplyScratchRegisterWrite(write.register_index, write.value);
                  ApplyCoherencyRegisterWrite(write.register_index, write.value);
                  raster_register_state.apply(write);
                  shader_register_state.apply(write);
                }
                ++loaded_constant_spans;
              } else {
                ++unresolved_constant_spans;
              }
            } else if (packet.type == shift::xbox::PacketType::Type3 &&
                       packet.opcode == 0x2Bu) {
              shift::xbox::CapturedImmediateShaderProgramLoad shader_load{};
              if (shift::xbox::decode_captured_immediate_shader_program_load(
                      packet_bytes, packet.byte_length, &shader_load, &error) &&
                  shader_load.code_offset <= packet.byte_length &&
                  shader_load.byte_length <= packet.byte_length - shader_load.code_offset) {
                std::vector<uint8_t>& active_program =
                    shader_load.stage == shift::xbox::GuestShaderStage::Vertex
                        ? vertex_shader_program
                        : pixel_shader_program;
                active_program.assign(packet_bytes + shader_load.code_offset,
                                      packet_bytes + shader_load.code_offset +
                                          shader_load.byte_length);
                ++loaded_immediate_shader_programs;
              } else {
                ++unresolved_immediate_shader_programs;
              }
            } else if (packet.type == shift::xbox::PacketType::Type3 &&
                       packet.opcode == 0x27u) {
              shift::xbox::CapturedShaderProgramLoad shader_load{};
              const uint8_t* shader_bytes = nullptr;
              size_t shader_byte_length = 0;
              if (shift::xbox::decode_captured_shader_program_load(
                      packet_bytes, packet.byte_length, &shader_load, &error) &&
                  ReadGuestMemory(this, shader_load.guest_address,
                                  shader_load.byte_length, &shader_bytes,
                                  &shader_byte_length) &&
                  shader_byte_length >= shader_load.byte_length) {
                std::vector<uint8_t>& active_program =
                    shader_load.stage == shift::xbox::GuestShaderStage::Vertex
                        ? vertex_shader_program
                        : pixel_shader_program;
                active_program.assign(shader_bytes,
                                      shader_bytes + shader_load.byte_length);
                ++loaded_shader_programs;
              } else {
                ++unresolved_shader_programs;
              }
            } else if (packet.type == shift::xbox::PacketType::Type3 &&
                       (packet.opcode == 0x22u || packet.opcode == 0x36u)) {
              shift::xbox::DecodedIndexedDraw draw{};
              if (shift::xbox::decode_captured_draw_indx(
                      packet_bytes, packet.byte_length, &draw, &error)) {
                ++decoded_draws;
                shift::xbox::CapturedRasterRegisters raster_registers{};
                shift::xbox::CapturedRasterState raster_state{};
                const bool raster_registers_ready =
                    raster_register_state.snapshot(&raster_registers, &error);
                uint32_t captured_target_width = last_guest_swap_width;
                uint32_t captured_target_height = last_guest_swap_height;
                if (raster_registers_ready && last_guest_swap_width != 0 &&
                    last_guest_swap_height != 0) {
                  const uint32_t surface_pitch =
                      raster_registers.surface_info & 0x3FFFu;
                  const uint32_t msaa_mode =
                      (raster_registers.surface_info >> 16) & 0x3u;
                  const uint64_t target_width =
                      static_cast<uint64_t>(surface_pitch) *
                      (msaa_mode == 2u ? 2u : 1u);
                  if (target_width != 0 &&
                      target_width <= std::numeric_limits<uint32_t>::max()) {
                    const uint64_t target_height =
                        (static_cast<uint64_t>(last_guest_swap_height) *
                             target_width +
                         last_guest_swap_width / 2u) /
                        last_guest_swap_width;
                    if (target_height != 0 &&
                        target_height <= std::numeric_limits<uint32_t>::max()) {
                      captured_target_width =
                          static_cast<uint32_t>(target_width);
                      captured_target_height =
                          static_cast<uint32_t>(target_height);
                    }
                  }
                }
                if (!raster_registers_ready &&
                    error == "incomplete captured raster register state") {
                  std::ostringstream detail;
                  detail << error << " valid_mask=0x" << std::hex
                         << raster_register_state.observed_register_mask();
                  error = detail.str();
                }
                const bool raster_state_ready = raster_registers_ready &&
                    shift::xbox::decode_captured_raster_state(
                        raster_registers, &raster_state, &error,
                        captured_target_width, captured_target_height);
                if (!raster_state_ready && raster_registers_ready &&
                    error == "unsupported captured target or raster state") {
                  std::ostringstream detail;
                  detail << error << " surface=0x" << std::hex
                         << raster_registers.surface_info << " color=0x"
                         << raster_registers.color_info << " depth=0x"
                         << raster_registers.depth_info << " mode=0x"
                         << raster_registers.mode_control << " depth_control=0x"
                         << raster_registers.depth_control << " color_mask=0x"
                         << raster_registers.color_mask << " blend=0x"
                         << raster_registers.blend_control_0 << " stencil=0x"
                         << raster_registers.stencil_refmask << " setup=0x"
                         << raster_registers.setup_mode_control << " viewport=[0x"
                         << raster_registers.viewport_x_scale << ",0x"
                         << raster_registers.viewport_x_offset << ",0x"
                         << raster_registers.viewport_y_scale << ",0x"
                         << raster_registers.viewport_y_offset << "] screen_scissor=[0x"
                         << raster_registers.screen_scissor_tl << ",0x"
                         << raster_registers.screen_scissor_br << "] window_offset=0x"
                         << raster_registers.window_offset << " window_scissor=[0x"
                         << raster_registers.window_scissor_tl << ",0x"
                         << raster_registers.window_scissor_br << ']';
                  error = detail.str();
                }
                if (!raster_state_ready && raster_registers_ready &&
                    error == "unsupported captured viewport or surface pitch") {
                  std::ostringstream detail;
                  detail << error << " surface_info=0x" << std::hex
                         << raster_registers.surface_info << " viewport=[0x"
                         << raster_registers.viewport_x_scale << ",0x"
                         << raster_registers.viewport_x_offset << ",0x"
                         << raster_registers.viewport_y_scale << ",0x"
                         << raster_registers.viewport_y_offset << "] screen_scissor=[0x"
                         << raster_registers.screen_scissor_tl << ",0x"
                         << raster_registers.screen_scissor_br << "] window_offset=0x"
                         << raster_registers.window_offset << " window_scissor=[0x"
                         << raster_registers.window_scissor_tl << ",0x"
                         << raster_registers.window_scissor_br << ']';
                  error = detail.str();
                }
                const std::string raster_state_error = error;
                if (raster_state_ready) {
                  ++draws_with_raster_state;
                  if (shift::xbox::captured_draw_has_no_framebuffer_effects(
                          raster_state)) {
                    ++draws_elided_as_noops;
                    continue;
                  }
                }
                if (!raster_state_ready && raster_registers_ready &&
                    draw.topology == shift::xbox::PrimitiveTopology::RectangleList) {
                  shift::xbox::CapturedCopyState copy_state{};
                  if (shift::xbox::decode_captured_copy_state(
                          raster_registers, &copy_state, &error)) {
                    if (copy_state.destination_format != 6u ||
                        copy_state.destination_number_format != 0u ||
                        copy_state.destination_endian != 0u ||
                        copy_state.destination_exp_bias != 0 ||
                        copy_state.sample_select != 0u ||
                        copy_state.color_clear_enable ||
                        copy_state.depth_clear_enable ||
                        !copy_state.destination_swap_red_blue) {
                      ++recognized_intermediate_copies;
                      continue;
                    }
                    shift::xbox::CapturedVulkanCopy prepared_copy{};
                    prepared_copy.state = copy_state;
                    prepared_copy.source_width = captured_target_width;
                    prepared_copy.source_height = captured_target_height;
                    prepared_copy.source_gamma = copy_state.source_gamma;
                    if (CompileCapturedCopyResolveShaders(&prepared_copy, &error)) {
                        frame_copy = std::move(prepared_copy);
                        frame_copy_ready = true;
                      REXLOG_INFO(
                          "shift-native: accepted captured source-0/sample-0 "
                          "Copy/Convert destination {:08X} {}x{} format {} R/B swap {}",
                          copy_state.destination_base, copy_state.destination_pitch,
                          copy_state.destination_height, copy_state.destination_format,
                          copy_state.destination_swap_red_blue);
                    } else {
                      frame_copy_ready = false;
                      REXLOG_WARN("shift-native: could not compile captured Copy/Convert "
                                  "resolve shaders: {}", error);
                    }
                    continue;
                  } else if (error ==
                             "unsupported captured Xenos color Copy/Convert state") {
                    std::ostringstream detail;
                    detail << raster_state_error << "; copy check: " << error
                           << " registers=[0x" << std::hex
                           << raster_registers.copy_control << ",0x"
                           << raster_registers.copy_dest_base << ",0x"
                           << raster_registers.copy_dest_pitch << ",0x"
                           << raster_registers.copy_dest_info << "] valid=0x"
                           << raster_registers.copy_valid_mask;
                    error = detail.str();
                  } else {
                    error = raster_state_error + "; copy check: " + error;
                  }
                }
                if (!vertex_shader_program.empty() && !pixel_shader_program.empty()) {
                  ++draws_with_both_shader_programs;
                }
                bool shader_inputs_ready = false;
                bool shaders_translated = false;
                shift::xbox::CapturedVulkanDraw prepared_draw{};
                const uint32_t upcoming_submitted_frame = readback_frame_counter + 1u;
                const uint32_t diagnostic_submitted_frame =
                    (kAndroidDebugReadbackFrame != 0u &&
                     upcoming_submitted_frame == kAndroidDebugReadbackFrame) ||
                            (selected_draw_dump_frame != 0u &&
                             upcoming_submitted_frame == selected_draw_dump_frame)
                        ? upcoming_submitted_frame
                        : 0u;
                const bool resources_resolved =
                    raster_state_ready && raster_state.scissor_has_area &&
                    PrepareCapturedDrawResources(draw, frame_draws.size(),
                                                 raster_state, shader_register_state,
                                                 vertex_shader_program, pixel_shader_program,
                                                 diagnostic_submitted_frame,
                                                 &prepared_draw, &shader_inputs_ready,
                                                 &shaders_translated, &error);
                if (shader_inputs_ready) {
                  ++draws_with_captured_shader_inputs;
                }
                if (shaders_translated) {
                  ++draws_with_project_shader_translation;
                  if (resources_resolved) {
                    ++draws_with_resolved_resource_payloads;
                    frame_draws.push_back(std::move(prepared_draw));
                    frame_draw_packet_indices.push_back(decoded_draws - 1u);
                  } else {
                    ++draws_with_unresolved_resource_payloads;
                  }
                }
                if (!resources_resolved) {
                  const std::string reason =
                      error.empty() ? "unsupported shader or resource form" : error;
                  if (logged_unresolved_draw_reasons.size() < 16u &&
                      std::find(logged_unresolved_draw_reasons.begin(),
                                logged_unresolved_draw_reasons.end(), reason) ==
                          logged_unresolved_draw_reasons.end()) {
                    logged_unresolved_draw_reasons.push_back(reason);
                    REXLOG_INFO(
                        "shift-native: unresolved captured draw #{} topology={} "
                        "autoindex={} count={} raster={} inputs={} translated={}: {}",
                        decoded_draws - 1u,
                        static_cast<uint32_t>(draw.topology), draw.auto_index,
                        draw.index_count, raster_state_ready, shader_inputs_ready,
                        shaders_translated, reason);
                  }
                  if (draw.topology == shift::xbox::PrimitiveTopology::RectangleList &&
                      rectangle_raster_diagnostics < 8) {
                    ++rectangle_raster_diagnostics;
                    REXLOG_DEBUG(
                        "shift-native: rejected rectangle raster snapshot={} "
                        "decoded={} error={} surface={:08x} color={:08x} "
                        "depth={:08x} mode={:08x} mask={:08x} screen=[{:08x},{:08x}] "
                        "window=[{:08x},{:08x}] blend={:08x} copy=[{:08x},{:08x},"
                        "{:08x},{:08x}] valid={:x}",
                        raster_registers_ready, raster_state_ready, error,
                        raster_registers.surface_info, raster_registers.color_info,
                        raster_registers.depth_info, raster_registers.mode_control,
                        raster_registers.color_mask, raster_registers.screen_scissor_tl,
                        raster_registers.screen_scissor_br,
                        raster_registers.window_scissor_tl,
                        raster_registers.window_scissor_br,
                        raster_registers.blend_control_0,
                        raster_registers.copy_control,
                        raster_registers.copy_dest_base,
                        raster_registers.copy_dest_pitch,
                        raster_registers.copy_dest_info,
                        raster_registers.copy_valid_mask);
                  }
                }
              } else {
                ++unsupported_draws;
                const std::string reason =
                    error.empty() ? "unsupported draw packet form" : error;
                if (logged_draw_decode_reasons.size() < 16u &&
                    std::find(logged_draw_decode_reasons.begin(),
                              logged_draw_decode_reasons.end(), reason) ==
                        logged_draw_decode_reasons.end()) {
                  logged_draw_decode_reasons.push_back(reason);
                  REXLOG_INFO("shift-native: rejected captured PM4 draw opcode {} "
                              "({} bytes): {}",
                              packet.opcode, packet.byte_length, reason);
                }
              }
            } else if (packet.type == shift::xbox::PacketType::Type3 &&
                       packet.opcode == 0x64u) {
              shift::xbox::DecodedGuestSwap swap{};
              if (!shift::xbox::decode_guest_swap(
                      packet_bytes, packet.byte_length, &swap, &error)) {
                ++unsupported_draws;
                recycle_frame_draws();
                frame_copy = {};
                frame_copy_ready = false;
                continue;
              }
              ++decoded_swaps;
              last_guest_swap_width = swap.width;
              last_guest_swap_height = swap.height;
              const bool copy_matches_swap = frame_copy_ready &&
                  frame_copy.state.destination_base == swap.frontbuffer_guest_address &&
                  frame_copy.state.destination_pitch == swap.width &&
                  frame_copy.state.destination_height == swap.height;
              const shift::xbox::CapturedVulkanCopy* copy_for_swap =
                  copy_matches_swap ? &frame_copy : nullptr;
              if (frame_copy_ready && !copy_matches_swap) {
                REXLOG_WARN("shift-native: ignored captured Copy/Convert destination "
                            "{:08X} {}x{} for guest swap {:08X} {}x{}",
                            frame_copy.state.destination_base,
                            frame_copy.state.destination_pitch,
                            frame_copy.state.destination_height,
                            swap.frontbuffer_guest_address, swap.width, swap.height);
              }
              if (!frame_draws.empty() && presenter_ && provider_ &&
                  provider_->vulkan_device()) {
                const uint32_t draw_count = static_cast<uint32_t>(frame_draws.size());
                const uint32_t upcoming_submitted_frame = readback_frame_counter + 1u;
                const bool capture_draw_visibility =
                    selected_draw_dump_frame != 0u &&
                    upcoming_submitted_frame == selected_draw_dump_frame;
                const char* readback_path = std::getenv("SHIFT_NATIVE_VULKAN_READBACK_PATH");
                const bool explicit_readback_path = readback_path && *readback_path;
                const char* source_readback_path =
                    std::getenv("SHIFT_NATIVE_VULKAN_SOURCE_READBACK_PATH");
                const bool explicit_source_readback_path =
                    source_readback_path && *source_readback_path;
#if defined(__ANDROID__) && !defined(NDEBUG)
                constexpr bool kAndroidDebugReadback = true;
                constexpr const char* kAndroidDebugReadbackPath =
                    SHIFT_NATIVE_VULKAN_DEBUG_READBACK_PATH;
#else
                constexpr bool kAndroidDebugReadback = false;
                constexpr const char* kAndroidDebugReadbackPath = "";
#endif
                if ((!readback_path || !*readback_path) &&
                    kAndroidDebugReadbackPath[0] != '\0') {
                  readback_path = kAndroidDebugReadbackPath;
                }
                uint32_t selected_readback_frame = 0;
                bool readback_frame_selection_valid = true;
                if (const char* frame_text =
                        std::getenv("SHIFT_NATIVE_VULKAN_READBACK_FRAME");
                    frame_text && *frame_text) {
                  readback_frame_selection_valid =
                      parse_positive_environment_frame(frame_text,
                                                       &selected_readback_frame);
                  if (!readback_frame_selection_valid &&
                      !readback_frame_warning_logged_) {
                    readback_frame_warning_logged_ = true;
                    REXLOG_WARN(
                        "shift-native: ignoring invalid "
                        "SHIFT_NATIVE_VULKAN_READBACK_FRAME value '{}'",
                        frame_text);
                  }
                } else if (explicit_readback_path || explicit_source_readback_path) {
                    selected_readback_frame = 1u;
                } else if (kAndroidDebugReadback) {
                  selected_readback_frame = kAndroidDebugReadbackFrame;
                }
                const bool capture_output = !readback_saved_ &&
                    readback_frame_selection_valid && selected_readback_frame != 0 &&
                    upcoming_submitted_frame == selected_readback_frame;
                const bool capture_source = capture_output &&
                                            explicit_source_readback_path;
                std::vector<uint32_t> output_readback;
                shift::xbox::CapturedVulkanSourceReadback source_readback;
                std::vector<shift::xbox::CapturedVulkanDrawVisibility>
                    draw_visibility;
                std::string render_error;
                bool refresh_callback_called = false;
                const bool refreshed = presenter_->RefreshGuestOutput(
                    swap.width, swap.height, swap.width, swap.height,
                    [this, &frame_draws, &render_error, &refresh_callback_called,
                      copy_for_swap, width = swap.width,
                      height = swap.height, capture_output, capture_source,
                     capture_draw_visibility, &output_readback, &source_readback,
                     &draw_visibility](
                        rex::ui::Presenter::GuestOutputRefreshContext& base) {
                      refresh_callback_called = true;
                      // This presenter was created by VulkanProvider below, so the refresh
                      // context is Vulkan-specific. static_cast keeps the SDK context usable
                      // across Android DSOs where hidden RTTI makes dynamic_cast fail.
                      auto* context = static_cast<
                          rex::ui::vulkan::VulkanPresenter::VulkanGuestOutputRefreshContext*>(
                          &base);
                      auto* device = provider_->vulkan_device();
                      if (!device) {
                        render_error = "Vulkan provider has no device during guest refresh";
                        return false;
                      }
                      if (!pipeline_cache_) {
                        const auto get_device_proc_addr =
                            device->vulkan_instance()->functions().vkGetDeviceProcAddr;
                        const auto create_pipeline_cache =
                            get_device_proc_addr
                                ? reinterpret_cast<PFN_vkCreatePipelineCache>(
                                      get_device_proc_addr(device->device(),
                                                           "vkCreatePipelineCache"))
                                : nullptr;
                        destroy_pipeline_cache_ =
                            get_device_proc_addr
                                ? reinterpret_cast<PFN_vkDestroyPipelineCache>(
                                      get_device_proc_addr(device->device(),
                                                           "vkDestroyPipelineCache"))
                                : nullptr;
                        if (!create_pipeline_cache || !destroy_pipeline_cache_) {
                          render_error = "Vulkan pipeline cache entry points are unavailable";
                          return false;
                        }
                        VkPipelineCacheCreateInfo cache_info{};
                        cache_info.sType = VK_STRUCTURE_TYPE_PIPELINE_CACHE_CREATE_INFO;
                        const VkResult cache_result = create_pipeline_cache(
                            device->device(), &cache_info, nullptr, &pipeline_cache_);
                        if (cache_result != VK_SUCCESS) {
                          render_error = "vkCreatePipelineCache failed with VkResult " +
                                         std::to_string(cache_result);
                          destroy_pipeline_cache_ = nullptr;
                          return false;
                        }
                      }
                      const uint32_t family = device->queue_family_graphics_compute();
                      const auto queue = device->AcquireQueue(family, 0);
                  // Older ReXGlue SDKs do not expose the optional resolve
                  // capability.
#if defined(SHIFT_REXGLUE_OPTIONAL_DEPTH_STENCIL_RESOLVE_PROVIDER)
                      const bool depth_stencil_resolve_enabled =
                          device->properties().depthStencilResolveSampleZero;
#else
                      constexpr bool depth_stencil_resolve_enabled = false;
#endif
                      return shift::xbox::submit_captured_vulkan_frame(
                          device->physical_device(), device->device(), queue.queue(), family,
                          context->image(), context->image_view(),
                          context->image_ever_written_previously(),
                          width, height, frame_draws, &render_error,
                          capture_output ? &output_readback : nullptr,
                          device->properties().geometryShader, copy_for_swap,
                          depth_stencil_resolve_enabled,
                          {device->properties().samplerAnisotropy,
                           device->properties().maxSamplerAnisotropy},
                          pipeline_cache_, &texture_cache_,
                          capture_source ? &source_readback : nullptr,
                          capture_draw_visibility ? &draw_visibility : nullptr);
                    });
                if (refreshed) {
                  ++submitted_frames;
                  ++readback_frame_counter;
                  REXLOG_INFO("shift-native: submitted {} captured indexed draw packets to "
                              "the Vulkan presenter at {}x{} (frontbuffer {:08X})",
                              draw_count, swap.width, swap.height,
                              swap.frontbuffer_guest_address);
                  if (capture_draw_visibility) {
                    for (size_t draw = 0; draw < draw_visibility.size(); ++draw) {
                      const auto& visibility = draw_visibility[draw];
                      REXLOG_INFO(
                          "shift-native: Vulkan occlusion draw packet #{} "
                          "(submitted draw {}) any samples passed: {}{}",
                          draw < frame_draw_packet_indices.size()
                              ? frame_draw_packet_indices[draw] : UINT32_MAX,
                          draw, visibility.available
                              ? (visibility.any_samples_passed ? "yes" : "no")
                              : "unavailable",
                          visibility.available
                              ? " (non-precise query; does not prove color writes)"
                              : "");
                    }
                  }
                  if (capture_output) {
                    const size_t expected_pixels =
                        static_cast<size_t>(swap.width) * swap.height;
                    bool output_written = output_readback.size() == expected_pixels;
                    if (output_written && readback_path && *readback_path) {
                      std::ofstream output_file;
                      output_file.open(readback_path,
                                       std::ios::binary | std::ios::trunc);
                      output_file.write(
                          reinterpret_cast<const char*>(output_readback.data()),
                          static_cast<std::streamsize>(output_readback.size() *
                                                       sizeof(uint32_t)));
                      output_file.close();
                      output_written = static_cast<bool>(output_file);
                    }
                    if (output_written) {
                      size_t non_black_pixels = 0;
                      uint64_t checksum = 14695981039346656037ull;
                      for (const uint32_t pixel : output_readback) {
                        if (pixel & 0x3FFFFFFFu) ++non_black_pixels;
                        for (unsigned byte = 0; byte < sizeof(pixel); ++byte) {
                          checksum ^= (pixel >> (byte * 8)) & 0xFFu;
                          checksum *= 1099511628211ull;
                        }
                      }
                      readback_saved_ = true;
                      REXLOG_INFO("shift-native: {} Vulkan guest output {}x{} as "
                                  "VK_FORMAT_A2B10G10R10_UNORM_PACK32{}{}; "
                                  "non-black pixels {}, FNV-1a64 {:016X} at submitted frame {}",
                                  readback_path && *readback_path ? "saved" : "read back",
                                  swap.width, swap.height,
                                  readback_path && *readback_path ? " to file " : " (no output file configured)",
                                  readback_path && *readback_path ? readback_path : "",
                                  non_black_pixels, checksum, readback_frame_counter);
                    } else {
                      REXLOG_WARN("shift-native: could not read/write Vulkan guest output{}{}",
                                  readback_path && *readback_path ? " at " : "",
                                  readback_path && *readback_path ? readback_path : "");
                    }
                  }
                  if (capture_source) {
                    if (source_readback.status ==
                        shift::xbox::CapturedVulkanSourceReadback::Status::Captured) {
                      bool source_written = true;
                      if (source_readback_path && *source_readback_path) {
                        std::ofstream source_file(source_readback_path,
                                                  std::ios::binary | std::ios::trunc);
                        source_file.write(
                            reinterpret_cast<const char*>(source_readback.bytes.data()),
                            static_cast<std::streamsize>(source_readback.bytes.size()));
                        source_file.close();
                        source_written = static_cast<bool>(source_file);
                      }
                      const uint32_t bytes_per_pixel =
                          (source_readback.format == VK_FORMAT_R16G16B16A16_SFLOAT ||
                           source_readback.format == VK_FORMAT_R16G16B16A16_UNORM)
                              ? 8u : 4u;
                      const size_t pixel_count =
                          static_cast<size_t>(source_readback.width) *
                          source_readback.height;
                      size_t non_black_pixels = 0;
                      uint64_t checksum = 14695981039346656037ull;
                      for (size_t byte_index = 0;
                           byte_index < source_readback.bytes.size(); ++byte_index) {
                        checksum ^= source_readback.bytes[byte_index];
                        checksum *= 1099511628211ull;
                      }
                      for (size_t pixel_index = 0; pixel_index < pixel_count;
                           ++pixel_index) {
                        const uint8_t* pixel = source_readback.bytes.data() +
                                               pixel_index * bytes_per_pixel;
                        bool has_color = false;
                        if (source_readback.format ==
                                VK_FORMAT_R16G16B16A16_SFLOAT ||
                            source_readback.format ==
                                VK_FORMAT_R16G16B16A16_UNORM) {
                          for (size_t channel = 0; channel < 3; ++channel) {
                            uint16_t value = 0;
                            std::memcpy(&value, pixel + channel * 2, sizeof(value));
                            has_color |= (value & 0x7FFFu) != 0;
                          }
                        } else if (source_readback.format ==
                                   VK_FORMAT_R16G16_SFLOAT) {
                          for (size_t channel = 0; channel < 2; ++channel) {
                            uint16_t value = 0;
                            std::memcpy(&value, pixel + channel * 2, sizeof(value));
                            has_color |= (value & 0x7FFFu) != 0;
                          }
                        } else if (source_readback.format ==
                                   VK_FORMAT_A2B10G10R10_UNORM_PACK32) {
                          uint32_t value = 0;
                          std::memcpy(&value, pixel, sizeof(value));
                          has_color = (value & 0x3FFFFFFFu) != 0;
                        } else {
                          has_color = pixel[0] || pixel[1] || pixel[2];
                        }
                        if (has_color) ++non_black_pixels;
                      }
                      const char* source_format_name =
                          source_readback.format == VK_FORMAT_R8G8B8A8_UNORM
                              ? "VK_FORMAT_R8G8B8A8_UNORM"
                          : source_readback.format ==
                                    VK_FORMAT_A2B10G10R10_UNORM_PACK32
                              ? "VK_FORMAT_A2B10G10R10_UNORM_PACK32"
                          : source_readback.format == VK_FORMAT_R16G16B16A16_SFLOAT
                              ? "VK_FORMAT_R16G16B16A16_SFLOAT"
                          : source_readback.format == VK_FORMAT_R16G16B16A16_UNORM
                              ? "VK_FORMAT_R16G16B16A16_UNORM"
                          : source_readback.format == VK_FORMAT_R16G16_SFLOAT
                              ? "VK_FORMAT_R16G16_SFLOAT" : "unknown";
                      if (!source_written) {
                        REXLOG_WARN("shift-native: could not write Vulkan pre-Copy source at {}",
                                    source_readback_path);
                      }
                      readback_saved_ = true;
                      REXLOG_INFO(
                          "shift-native: {} Vulkan pre-Copy source {}x{} {} "
                          "samples {}, average-resolve {}; non-black pixels {}, "
                          "FNV-1a64 {:016X}, {} bytes at submitted frame {}",
                          source_written && source_readback_path && *source_readback_path
                              ? "saved" : "read back",
                          source_readback.width, source_readback.height,
                          source_format_name, source_readback.sample_count,
                          source_readback.multisample_average_resolve,
                          non_black_pixels, checksum, source_readback.bytes.size(),
                          readback_frame_counter);
                    } else {
                      REXLOG_WARN("shift-native: Vulkan pre-Copy source readback unsupported: {}",
                                  source_readback.reason);
                    }
                  }
                } else {
                  if (render_error.empty()) {
                    render_error = refresh_callback_called
                        ? "refresh callback failed without a Vulkan diagnostic"
                        : "presenter did not invoke refresh callback; guest output image unavailable";
                  }
                  static std::atomic<uint32_t> refresh_failure_count{0};
                  const uint32_t failure_index = refresh_failure_count.fetch_add(
                      1, std::memory_order_relaxed);
                  if (failure_index < 8u || (failure_index & 0x3FFu) == 0u) {
                    REXLOG_WARN("shift-native: Vulkan frame refresh failed for {}x{} "
                                "with {} captured draws (failure {}): {}",
                                swap.width, swap.height, draw_count, failure_index + 1u,
                                render_error);
                  }
                }
              }
              recycle_frame_draws();
              frame_copy = {};
              frame_copy_ready = false;
              ++guest_swap_counter;
            } else if (packet.type == shift::xbox::PacketType::Type3 &&
                       packet.opcode == 0x54u) {
              uint32_t cpu_mask = 0;
              if (!shift::xbox::decode_captured_gpu_interrupt(
                      packet_bytes, packet.byte_length, &cpu_mask, &error)) {
                ++unsupported_draws;
                REXLOG_WARN("shift-native: rejected PM4_INTERRUPT packet: {}", error);
                continue;
              }
              ++interrupt_packets;
              try {
                for (uint32_t cpu = 0; cpu < 6u; ++cpu) {
                  if ((cpu_mask & (1u << cpu)) != 0 &&
                      DispatchGuestInterrupt(1u, cpu,
                                             ring_host_worker_.get())) {
                    ++dispatched_interrupt_callbacks;
                  }
                }
              } catch (const std::exception& e) {
                REXLOG_ERROR("shift-native: guest GPU interrupt callback failed: {}",
                             e.what());
              } catch (...) {
                REXLOG_ERROR("shift-native: guest GPU interrupt callback failed");
              }
            }
          }
          std::ostringstream type3_opcode_summary;
          bool first_type3_opcode = true;
          for (size_t opcode = 0; opcode < type3_opcode_counts.size(); ++opcode) {
            if (!type3_opcode_counts[opcode]) continue;
            if (!first_type3_opcode) type3_opcode_summary << ',';
            type3_opcode_summary << std::hex << opcode << std::dec << ':'
                                 << type3_opcode_counts[opcode];
            first_type3_opcode = false;
          }
          type3_opcode_summary << "; DRAW_INDX_2 source/primitive [";
          bool first_draw_form = true;
          for (uint32_t source = 0; source < 4u; ++source) {
            for (uint32_t primitive = 0; primitive < 64u; ++primitive) {
              const uint32_t count =
                  draw_source_primitive_counts[source * 64u + primitive];
              if (!count)
                continue;
              if (!first_draw_form)
                type3_opcode_summary << ',';
              type3_opcode_summary << "source=" << source
                                   << "/primitive=" << primitive << ':'
                                   << count;
              first_draw_form = false;
            }
          }
          type3_opcode_summary << ']';
          type3_opcode_summary << "; DRAW_INDX_2 index-count [";
          bool first_draw_count = true;
          for (const auto &[index_count, count] : draw_index_count_counts) {
            if (!first_draw_count)
              type3_opcode_summary << ',';
            type3_opcode_summary << index_count << ':' << count;
            first_draw_count = false;
          }
          type3_opcode_summary << ']';
          const auto shader_cache_stats = shader_translation_cache_.stats();
          const auto r8_scratch_stats = r8_upload_scratch_.stats();
          REXLOG_DEBUG("shift-native: framed {} PM4 packets, {} raw register writes, "
                       "{} constant spans loaded ({} unresolved), "
                       "{} pointer-loaded shader programs ({} unresolved), "
                       "{} inline shader programs ({} unresolved), "
                       "{} captured indexed draw packets ({} with supported raster state, "
                       "{} elided as framebuffer no-ops, {} with both shader programs, "
                       "{} with complete captured shader inputs, "
                       "{} translated to project GLSL, shader cache {}/{} hits/misses "
                       "({} entries, {} payload bytes), {} with resolved resource bytes "
                       "({} unresolved)), "
                       "R8 upload scratch {}/{} hits/misses ({} slots, {} bytes), "
                       "{} intermediate Copy/Convert states decoded, "
                       "{} guest swaps, {} Vulkan frames submitted, "
                       "{} unsupported packet/draw forms, type3 opcodes [{}]",
                       expanded.packets.size(), raw_register_writes,
                       loaded_constant_spans, unresolved_constant_spans,
                       loaded_shader_programs, unresolved_shader_programs,
                       loaded_immediate_shader_programs, unresolved_immediate_shader_programs,
                       decoded_draws, draws_with_raster_state, draws_elided_as_noops,
                       draws_with_both_shader_programs,
                       draws_with_captured_shader_inputs, draws_with_project_shader_translation,
                       shader_cache_stats.hits, shader_cache_stats.misses,
                       shader_cache_stats.entries,
                       shader_cache_stats.retained_payload_bytes,
                       draws_with_resolved_resource_payloads,
                       draws_with_unresolved_resource_payloads,
                       r8_scratch_stats.hits, r8_scratch_stats.misses,
                       r8_scratch_stats.entries, r8_scratch_stats.reserved_bytes,
                       recognized_intermediate_copies, decoded_swaps, submitted_frames,
                       unsupported_draws, type3_opcode_summary.str());
        } else {
          REXLOG_WARN("shift-native: dropped malformed PM4 batch at WPTR {:08X}: {}",
                      write_pointer, error);
        }
      } catch (const std::exception& e) {
        REXLOG_ERROR("shift-native: failed to process guest PM4 batch: {}", e.what());
      } catch (...) {
        REXLOG_ERROR("shift-native: failed to process guest PM4 batch");
      }

      uint32_t current_read_pointer = 0;
      uint32_t current_write_pointer = 0;
      uint64_t current_ring_generation = 0;
      if (!read_pointer_writeback.published) {
        // Keep malformed/unsupported batches consumable as before, but do not
        // overwrite a newer ring generation or read pointer.
        read_pointer_writeback = PublishReadPointer(
            ring_generation, read_pointer, write_pointer, "completion");
      }
      {
        std::lock_guard<std::mutex> lock(ring_mutex_);
        current_read_pointer = ring_read_pointer_;
        current_write_pointer = ring_write_pointer_;
        current_ring_generation = ring_generation_;
      }
      if (GuestRingTraceEnabled()) {
        const uint32_t trace_record = NextGuestRingTraceRecord();
        if (trace_record < kMaxGuestRingTraceRecords) {
          REXLOG_INFO("shift-native: ring trace complete #{} consumed=[{},{}), "
                      "current-rptr={} current-wptr={} generation={} "
                      "writeback-guest={:08X} value={:08X}->{:08X}",
                      trace_record, read_pointer, write_pointer,
                      current_read_pointer, current_write_pointer,
                      current_ring_generation,
                      read_pointer_writeback.guest_address,
                      read_pointer_writeback.previous_value,
                      read_pointer_writeback.stored_value);
        }
      }
      if (interrupt_packets) {
        REXLOG_DEBUG("shift-native: consumed {} PM4_INTERRUPT packets and dispatched "
                     "{} guest callbacks",
                     interrupt_packets, dispatched_interrupt_callbacks);
      }
    }
  }

  std::unique_ptr<rex::ui::vulkan::VulkanProvider> provider_;
  std::unique_ptr<rex::ui::Presenter> presenter_;
  VkPipelineCache pipeline_cache_ = VK_NULL_HANDLE;
  shift::xbox::CapturedVulkanTextureCache texture_cache_;
  shift::xbox::plugin::R8UploadScratchCache r8_upload_scratch_;
  shift::xbox::CapturedShaderTranslationCache shader_translation_cache_;
  PFN_vkDestroyPipelineCache destroy_pipeline_cache_ = nullptr;
  rex::ui::WindowedAppContext* app_context_ = nullptr;
  rex::memory::Memory* memory_ = nullptr;
  rex::runtime::FunctionDispatcher* function_dispatcher_ = nullptr;
  rex::system::KernelState* kernel_state_ = nullptr;
  std::mutex ring_mutex_;
  std::condition_variable ring_changed_;
  std::thread ring_worker_;
  rex::system::object_ref<rex::system::XHostThread> ring_host_worker_;
  std::atomic<bool> vblank_worker_running_{false};
  std::atomic<uint32_t> event_initiator_{0};
  rex::system::object_ref<rex::system::XHostThread> vblank_host_worker_;
  std::mutex interrupt_mutex_;
  std::mutex guest_coherency_mutex_;
  uint32_t interrupt_callback_ = 0;
  uint32_t interrupt_callback_data_ = 0;
  uint32_t coher_size_host_ = 0;
  uint32_t coher_base_host_ = 0;
  uint32_t coher_status_host_ = 0;
  uint64_t coherency_generation_ = 0;
  std::atomic<uint32_t> scratch_address_{0};
  std::atomic<uint32_t> scratch_umsk_{0};
  uint32_t ring_guest_address_ = 0;
  size_t ring_byte_length_ = 0;
  uint32_t ring_read_pointer_ = 0;
  uint32_t ring_write_pointer_ = 0;
  uint32_t read_pointer_writeback_address_ = 0;
  uint64_t ring_generation_ = 0;
  bool ring_initialized_ = false;
  bool ring_worker_shutdown_ = false;
  bool readback_saved_ = false;
  bool readback_frame_warning_logged_ = false;
};

}  // namespace

extern "C" REX_GPU_PLUGIN_EXPORT uint32_t rex_gpu_abi_version() {
  return rex::system::kGpuPluginAbiVersion;
}

extern "C" REX_GPU_PLUGIN_EXPORT rex::system::IGraphicsSystem* rex_gpu_create(
    uint32_t abi_version, const rex::system::GpuCreateInfo* info) {
  if (abi_version != rex::system::kGpuPluginAbiVersion ||
      (info && info->struct_size < sizeof(rex::system::GpuCreateInfo))) {
    return nullptr;
  }
  if (info && info->backend && std::string(info->backend) != "any" &&
      std::string(info->backend) != "vulkan") {
    return nullptr;
  }
  return new ShiftNativeGraphicsSystem();
}
