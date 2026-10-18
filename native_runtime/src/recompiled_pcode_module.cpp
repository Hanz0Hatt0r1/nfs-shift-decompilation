#include "shift_recompiled_pcode_module.hpp"
#include "shift_recompiled_pcode_abi.h"

#include <dlfcn.h>
#include <cerrno>
#include <fcntl.h>
#include <filesystem>
#include <sys/stat.h>
#include <sys/mman.h>
#include <sys/sysinfo.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <ucontext.h>

#if defined(__i386__) || defined(__x86_64__)
#include <cpuid.h>
#endif

#include <algorithm>
#include <array>
#include <chrono>
#include <cfloat>
#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <deque>
#include <thread>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace shift::runtime {
namespace {

constexpr uint64_t kGuestRamSize = UINT64_C(1) << 32;
constexpr size_t kRegisterBankSize = 0x2000;
constexpr size_t kMaximumPcodeValueSize = 16;
constexpr uint32_t kMaximumCallDepth = 256;
constexpr uint16_t kPeI386 = 0x014c;
constexpr uint16_t kPe32Magic = 0x010b;
constexpr uint16_t kMaximumPeSectionCount = 96;
constexpr size_t kPeSectionHeaderSize = 40;
constexpr size_t kPeImportDescriptorSize = 20;
constexpr size_t kCopyChunkSize = 64 * 1024;
constexpr uint32_t kImportStubPreferredBase = 0xf0000000;
constexpr uint32_t kImportStubStride = 0x10;
constexpr uint32_t kGuestProcessHeapHandle = 0x00010000;
constexpr uint32_t kGuestCurrentProcessPseudoHandle = UINT32_MAX;
constexpr uint32_t kGuestCurrentThreadPseudoHandle = UINT32_MAX - 1;
constexpr uint32_t kGuestFileHandleBase = 0x00050000;
constexpr uint32_t kGuestEventHandleBase = 0x00060000;
constexpr uint32_t kGuestTimerPeriodMs = 1;
constexpr uint32_t kGuestTimerNoError = 0;
constexpr uint32_t kGuestTimerErrNoCanDo = 97;
constexpr uint32_t kGuestAlreadyFiberError = 1280;
constexpr size_t kMaximumGuestFileReadBytes = 64 * 1024 * 1024;
constexpr uint64_t kMaximumGuestVirtualAllocationSize =
    UINT64_C(512) * 1024 * 1024;
constexpr uint32_t kGuestStdInputHandle = 0x00020000;
constexpr uint32_t kGuestStdOutputHandle = 0x00020004;
constexpr uint32_t kGuestStdErrorHandle = 0x00020008;
constexpr uint32_t kGuestCommandLineAddress = 0x00031000;
constexpr uint32_t kGuestEnvironmentAnsiAddress = 0x00031010;
constexpr uint32_t kGuestEnvironmentWideAddress = 0x00031020;
constexpr uint32_t kGuestHeapStartAddress = 0x10000000;
constexpr uint32_t kGuestModuleHandleBase = 0xe0000000;
constexpr uint32_t kGuestModuleHandleStride = 0x10;
constexpr uint32_t kGuestDynamicImportStubBase = 0xd0000000;
constexpr uint32_t kMaximumGuestTlsSlots = 1088;
constexpr size_t kMaximumWin32TextUnits = 1024 * 1024;
constexpr size_t kOsVersionInfoABytes = 148;
constexpr size_t kOsVersionInfoExABytes = 156;
constexpr uint64_t kWindowsFileTimeUnixEpoch = UINT64_C(116444736000000000);
constexpr uint64_t kWindowsFileTimeTicksPerSecond = UINT64_C(10000000);
constexpr uint64_t kWindowsPerformanceCounterFrequency = UINT64_C(1000000000);
constexpr uint32_t kWindowsAnsiCodePage = 1252;
constexpr uint64_t kX86EaxRegisterOffset = 0;
constexpr uint64_t kX86EspRegisterOffset = 0x10;
constexpr uint64_t kX86EbpRegisterOffset = 0x14;
constexpr uint64_t kX86FsBaseRegisterOffset = 0x110;
constexpr uint64_t kX86X87EnvironmentRegisterOffset = 0x10a0;
constexpr uint32_t kGuestInitialStackPointer = 0x7ffdf000;
constexpr uint32_t kGuestStackLimit = 0x7ff00000;
constexpr uint32_t kGuestTebAddress = 0x7ffde000;
constexpr size_t kGuestTebSize = 0x1000;
constexpr uint32_t kGuestFiberHandleBase = 0x00070000;
constexpr uint32_t kGuestFiberHandleStride = 0x10;
constexpr uint32_t kGuestThreadHandleBase = 0x00080000;
constexpr uint32_t kGuestThreadHandleStride = 0x10;
constexpr uint32_t kGuestDefaultThreadStackSize = 1024 * 1024;
constexpr uint32_t kGuestMaximumThreadStackSize = 64 * 1024 * 1024;
constexpr int kGuestThreadExitResult = 1;
constexpr uint32_t kGuestCpuidScratchAddress = 0xfffffff0;
constexpr size_t kMaximumImportDescriptors = 4096;
constexpr size_t kMaximumImportThunksPerModule = 65536;
constexpr size_t kMaximumImportFunctions = 65536;
constexpr size_t kMaximumImportNameSize = 512;
constexpr std::array<uint16_t, 32> kWindows1252HighCharacters = {
    0x20ac, 0x0081, 0x201a, 0x0192, 0x201e, 0x2026, 0x2020, 0x2021,
    0x02c6, 0x2030, 0x0160, 0x2039, 0x0152, 0x008d, 0x017d, 0x008f,
    0x0090, 0x2018, 0x2019, 0x201c, 0x201d, 0x2022, 0x2013, 0x2014,
    0x02dc, 0x2122, 0x0161, 0x203a, 0x0153, 0x009d, 0x017e, 0x0178};

using PcodeFunction = int (*)(RviPcodeContext*);
thread_local void* active_pcode_scheduler = nullptr;

struct PeSection {
    uint32_t virtual_address = 0;
    uint32_t virtual_size = 0;
    uint32_t raw_offset = 0;
    uint32_t raw_size = 0;

    uint64_t mapped_size() const {
        return std::max(virtual_size, raw_size);
    }
};

struct ImportedThunk {
    uint32_t iat_rva = 0;
    std::string name;
};

void require_pe(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error("invalid PE32 image: " +
                                 std::string(message));
    }
}

void require_file_range(uint64_t offset, uint64_t size, uint64_t file_size) {
    require_pe(offset <= file_size && size <= file_size - offset,
               "file range is out of bounds");
}

void read_file_range(std::ifstream& file, uint64_t file_size,
                     uint64_t offset, uint8_t* output, size_t size) {
    require_file_range(offset, size, file_size);
    require_pe(offset <= static_cast<uint64_t>(
                            std::numeric_limits<std::streamoff>::max()),
               "file offset cannot be represented by the host stream");
    file.clear();
    file.seekg(static_cast<std::streamoff>(offset), std::ios::beg);
    require_pe(static_cast<bool>(file), "cannot seek in image file");
    file.read(reinterpret_cast<char*>(output),
              static_cast<std::streamsize>(size));
    require_pe(file.gcount() == static_cast<std::streamsize>(size),
               "short read from image file");
}

uint16_t read_u16(std::ifstream& file, uint64_t file_size, uint64_t offset) {
    std::array<uint8_t, 2> bytes{};
    read_file_range(file, file_size, offset, bytes.data(), bytes.size());
    return static_cast<uint16_t>(bytes[0]) |
           static_cast<uint16_t>(static_cast<uint16_t>(bytes[1]) << 8);
}

uint32_t read_u32(std::ifstream& file, uint64_t file_size, uint64_t offset) {
    std::array<uint8_t, 4> bytes{};
    read_file_range(file, file_size, offset, bytes.data(), bytes.size());
    return static_cast<uint32_t>(bytes[0]) |
           (static_cast<uint32_t>(bytes[1]) << 8) |
           (static_cast<uint32_t>(bytes[2]) << 16) |
           (static_cast<uint32_t>(bytes[3]) << 24);
}

uint64_t file_offset_for_rva(uint32_t rva, size_t size,
                             uint32_t headers_size,
                             const std::vector<PeSection>& sections) {
    if (rva <= headers_size && size <= headers_size - rva) return rva;
    for (const auto& section : sections) {
        if (rva < section.virtual_address) continue;
        const uint64_t delta =
            static_cast<uint64_t>(rva) - section.virtual_address;
        if (delta <= section.raw_size && size <= section.raw_size - delta) {
            return static_cast<uint64_t>(section.raw_offset) + delta;
        }
    }
    throw std::runtime_error(
        "invalid PE32 image: import RVA has no raw file backing");
}

uint32_t read_rva_u32(std::ifstream& file, uint64_t file_size, uint32_t rva,
                      uint32_t headers_size,
                      const std::vector<PeSection>& sections) {
    return read_u32(file, file_size,
                    file_offset_for_rva(rva, sizeof(uint32_t), headers_size,
                                        sections));
}

std::string read_import_name(std::ifstream& file, uint64_t file_size,
                             uint32_t rva, uint32_t headers_size,
                             const std::vector<PeSection>& sections) {
    std::string name;
    name.reserve(32);
    for (size_t index = 0; index < kMaximumImportNameSize; ++index) {
        require_pe(static_cast<uint64_t>(rva) + index <=
                       std::numeric_limits<uint32_t>::max(),
                   "import name RVA overflows");
        const uint64_t offset = file_offset_for_rva(
            rva + static_cast<uint32_t>(index), 1, headers_size, sections);
        uint8_t byte = 0;
        read_file_range(file, file_size, offset, &byte, 1);
        if (byte == 0) {
            require_pe(!name.empty(), "import name is empty");
            return name;
        }
        require_pe(byte >= 0x20 && byte <= 0x7e,
                   "import name contains a non-ASCII byte");
        name.push_back(static_cast<char>(byte));
    }
    throw std::runtime_error(
        "invalid PE32 image: import name is not terminated");
}

std::string lowercase_ascii(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(),
                   [](unsigned char byte) {
                       return static_cast<char>(std::tolower(byte));
                   });
    return value;
}

uint16_t decode_windows_1252(uint8_t byte) {
    if (byte < 0x80 || byte >= 0xa0) return byte;
    return kWindows1252HighCharacters[byte - 0x80];
}

bool encode_windows_1252(uint16_t character, uint8_t& byte) {
    if (character < 0x80 || (character >= 0xa0 && character <= 0xff)) {
        byte = static_cast<uint8_t>(character);
        return true;
    }
    const auto found = std::find(kWindows1252HighCharacters.begin(),
                                 kWindows1252HighCharacters.end(), character);
    if (found == kWindows1252HighCharacters.end()) return false;
    byte = static_cast<uint8_t>(0x80 +
                                (found - kWindows1252HighCharacters.begin()));
    return true;
}

uint16_t classify_windows_ctype1(uint16_t character) {
    constexpr uint16_t upper = 0x0001;
    constexpr uint16_t lower = 0x0002;
    constexpr uint16_t digit = 0x0004;
    constexpr uint16_t space = 0x0008;
    constexpr uint16_t punctuation = 0x0010;
    constexpr uint16_t control = 0x0020;
    constexpr uint16_t blank = 0x0040;
    constexpr uint16_t hex_digit = 0x0080;
    constexpr uint16_t alpha = 0x0100;
    if (character < 0x20 || character == 0x7f) return control;
    if (character == 0x20 || character == 0xa0) return space | blank;
    if (character == '\t') return control | space | blank;
    if (character == '\n' || character == '\v' || character == '\f' ||
        character == '\r') {
        return control | space;
    }
    if (character >= '0' && character <= '9')
        return digit | hex_digit;
    if ((character >= 'A' && character <= 'Z') || character == 0x0160 ||
        character == 0x0152 || character == 0x017d || character == 0x0178 ||
        (character >= 0x00c0 && character <= 0x00d6) ||
        (character >= 0x00d8 && character <= 0x00de)) {
        return upper | alpha |
               ((character >= 'A' && character <= 'F') ? hex_digit : 0);
    }
    if ((character >= 'a' && character <= 'z') || character == 0x0192 ||
        character == 0x0161 || character == 0x0153 || character == 0x017e ||
        character == 0x00df || character == 0x00ff ||
        character == 0x00aa || character == 0x00ba ||
        (character >= 0x00e0 && character <= 0x00f6) ||
        (character >= 0x00f8 && character <= 0x00fe)) {
        return lower | alpha |
               ((character >= 'a' && character <= 'f') ? hex_digit : 0);
    }
    return punctuation;
}

uint16_t map_windows_1252_case(uint16_t character, bool to_lower) {
    if (to_lower) {
        if (character >= 'A' && character <= 'Z')
            return static_cast<uint16_t>(character + 0x20);
        if ((character >= 0x00c0 && character <= 0x00d6) ||
            (character >= 0x00d8 && character <= 0x00de)) {
            return static_cast<uint16_t>(character + 0x20);
        }
        if (character == 0x0160) return 0x0161;
        if (character == 0x0152) return 0x0153;
        if (character == 0x017d) return 0x017e;
        if (character == 0x0178) return 0x00ff;
        return character;
    }
    if (character >= 'a' && character <= 'z')
        return static_cast<uint16_t>(character - 0x20);
    if ((character >= 0x00e0 && character <= 0x00f6) ||
        (character >= 0x00f8 && character <= 0x00fe)) {
        return static_cast<uint16_t>(character - 0x20);
    }
    if (character == 0x0161) return 0x0160;
    if (character == 0x0153) return 0x0152;
    if (character == 0x017e) return 0x017d;
    if (character == 0x00ff) return 0x0178;
    return character;
}

uint32_t choose_import_stub_base(uint32_t image_base, uint32_t image_size,
                                 size_t unique_import_count) {
    if (unique_import_count == 0) return 0;
    const uint64_t span = static_cast<uint64_t>(unique_import_count) *
                          kImportStubStride;
    const uint64_t image_end =
        static_cast<uint64_t>(image_base) + image_size;
    uint64_t candidate = kImportStubPreferredBase;
    if (candidate + span > (UINT64_C(1) << 32) ||
        (candidate < image_end && image_base < candidate + span)) {
        require_pe(static_cast<uint64_t>(image_base) >= span + 0x10000,
                   "no guest address range is available for import traps");
        candidate = (static_cast<uint64_t>(image_base) - span) &
                    ~static_cast<uint64_t>(kImportStubStride - 1);
    }
    require_pe(candidate >= 0x10000 &&
                   candidate + span <= (UINT64_C(1) << 32) &&
                   !(candidate < image_end && image_base < candidate + span),
               "no guest address range is available for import traps");
    return static_cast<uint32_t>(candidate);
}

uint32_t choose_guest_module_handle_base(uint32_t image_base,
                                         uint32_t image_size,
                                         uint32_t import_stub_base,
                                         size_t import_count,
                                         size_t module_count) {
    if (module_count == 0) return 0;
    const uint64_t span = static_cast<uint64_t>(module_count) *
                          kGuestModuleHandleStride;
    const uint64_t image_end = static_cast<uint64_t>(image_base) + image_size;
    const uint64_t import_end = static_cast<uint64_t>(import_stub_base) +
                                import_count * kImportStubStride;
    for (uint64_t candidate = kGuestModuleHandleBase;
         candidate >= 0x20000000; candidate -= 0x10000000) {
        const uint64_t end = candidate + span;
        if (end > kGuestRamSize ||
            (candidate < image_end && image_base < end) ||
            (candidate < import_end && import_stub_base < end)) {
            continue;
        }
        return static_cast<uint32_t>(candidate);
    }
    throw std::runtime_error(
        "invalid PE32 image: no address range is available for module handles");
}

}  // namespace

struct RecompiledPcodeModule::Impl {
    struct GuestHeapBlock {
        uint32_t address = 0;
        size_t size = 0;
        uint32_t heap = 0;
        size_t requested_size = 0;
    };
    struct GuestCriticalSection {
        uint32_t recursion_count = 0;
        uint32_t spin_count = 0;
    };
    struct GuestMutex {
        uint32_t recursion_count = 0;
    };
    struct GuestFile {
        int descriptor = -1;
        uint64_t size = 0;
    };
    struct GuestEvent {
        bool manual_reset = false;
        bool signaled = false;
    };
    struct GuestFiber {
        uint32_t data = 0;
    };
    struct GuestExecutionState {
        std::array<uint8_t, kRegisterBankSize> registers{};
        std::unordered_map<uint32_t, uint32_t> tls_values;
        std::vector<uint32_t> active_functions;
        uint32_t last_error = 0;
        int32_t priority = 0;
        uint32_t ideal_processor = 0;
        uint32_t current_fiber = 0;
        uint32_t current_exit_code = 259;
        uint32_t call_depth = 0;
        uint32_t indirect_jump_depth = 0;
        bool exit_requested = false;
    };

    struct GuestThread : GuestExecutionState {
        uint32_t id = 0;
        uint32_t start_address = 0;
        uint32_t parameter = 0;
        uint32_t suspend_count = 0;
        uint32_t exit_code = 259;
        GuestHeapBlock stack;
        GuestHeapBlock teb;
        ucontext_t coroutine{};
        std::unique_ptr<uint8_t[]> coroutine_stack;
        size_t coroutine_stack_size = 0;
        uint32_t wait_handle = 0;
        uint32_t wait_result = 0x00000102;
        std::chrono::steady_clock::time_point wait_deadline{};
        bool started = false;
        bool completed = false;
        bool close_pending = false;
        bool coroutine_initialized = false;
        bool runnable = false;
        bool waiting = false;
    };

    explicit Impl(const std::string& path) {
        static_assert(sizeof(size_t) >= sizeof(uint64_t),
                      "the guest RAM reservation requires a 64-bit host");
        ram = mmap(nullptr, static_cast<size_t>(kGuestRamSize),
                   PROT_READ | PROT_WRITE,
                   MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0);
        if (ram == MAP_FAILED) {
            ram = nullptr;
            throw std::runtime_error("cannot reserve 4 GiB guest RAM");
        }

        module = dlopen(path.c_str(), RTLD_NOW | RTLD_LOCAL);
        if (!module) {
            const char* error = dlerror();
            munmap(ram, static_cast<size_t>(kGuestRamSize));
            ram = nullptr;
            throw std::runtime_error("cannot load P-code module: " +
                                     std::string(error ? error : "unknown dlopen error"));
        }
        context = {this, &read_callback, &write_callback,
                   &call_callback, &userop_callback};
    }

    ~Impl() {
        for (const auto& [handle, file] : guest_files) {
            (void)handle;
            if (file.descriptor >= 0) (void)::close(file.descriptor);
        }
        for (auto it = override_modules.rbegin(); it != override_modules.rend();
             ++it) {
            if (*it) dlclose(*it);
        }
        for (auto it = supplemental_modules.rbegin();
             it != supplemental_modules.rend(); ++it) {
            if (*it) dlclose(*it);
        }
        if (module) dlclose(module);
        if (ram) munmap(ram, static_cast<size_t>(kGuestRamSize));
    }

    static int read_callback(void* opaque, const char* space, uint64_t offset,
                             size_t size, uint8_t* output) {
        auto* self = static_cast<Impl*>(opaque);
        return self && self->read_guest(space, offset, size, output) ? 0 : -1;
    }

    static int write_callback(void* opaque, const char* space, uint64_t offset,
                              size_t size, const uint8_t* input) {
        auto* self = static_cast<Impl*>(opaque);
        return self && self->write_guest(space, offset, size, input) ? 0 : -1;
    }

    static int call_callback(void* opaque, uint64_t target) {
        auto* self = static_cast<Impl*>(opaque);
        return self ? self->dispatch(target) : -1;
    }

    static int userop_callback(void* opaque, uint32_t index,
                               const uint64_t* arguments,
                               const unsigned* argument_sizes,
                               size_t argument_count, uint64_t* output,
                               unsigned output_size) {
        auto* self = static_cast<Impl*>(opaque);
        if (!self) return -1;
        if (index == 17 || index == 18) {
            if (argument_count != 0 || output != nullptr || output_size != 0) {
                self->error = "invalid x86 LOCK/UNLOCK P-code userop signature";
                return -1;
            }
            return 0;
        }
        if (index == 72) {
            if (argument_count != 0 || !output || output_size != 8) {
                self->error = "invalid x86 RDTSC P-code userop signature";
                return -1;
            }
            *output = static_cast<uint64_t>(
                std::chrono::duration_cast<std::chrono::nanoseconds>(
                    std::chrono::steady_clock::now().time_since_epoch())
                    .count());
            return 0;
        }
        if (index == 100) {
            if (!arguments || !argument_sizes || argument_count != 1 ||
                argument_sizes[0] != 10 || !output || output_size != 10) {
                self->error = "invalid x86 FCOS P-code userop signature";
                return -1;
            }
#if (defined(__i386__) || defined(__x86_64__)) && \
    LDBL_MANT_DIG == 64 && LDBL_MAX_EXP == 16384 && \
    defined(__BYTE_ORDER__) && __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
            std::array<uint8_t, 10> input_bytes{};
            for (size_t index = 0; index < input_bytes.size(); ++index) {
                input_bytes[index] = static_cast<uint8_t>(
                    arguments[index / sizeof(uint64_t)] >>
                    ((index % sizeof(uint64_t)) * 8));
            }
            long double input = 0.0L;
            std::memcpy(&input, input_bytes.data(), input_bytes.size());
            const long double result = std::cos(input);
            std::array<uint8_t, 10> result_bytes{};
            std::memcpy(result_bytes.data(), &result, result_bytes.size());
            std::memcpy(output, result_bytes.data(), result_bytes.size());
            return 0;
#else
            self->error = "x86 FCOS P-code userop requires a binary80 Linux host";
            return -1;
#endif
        }
        if (index < 44 || index > 60) {
            self->error = "unhandled P-code userop index " +
                          std::to_string(index);
            if (!self->active_guest_functions.empty()) {
                char address[40]{};
                std::snprintf(address, sizeof(address),
                              " in guest function 0x%08x",
                              self->active_guest_functions.back());
                self->error += address;
            }
            return -1;
        }
        if (!arguments || !argument_sizes || argument_count != 1 ||
            argument_sizes[0] != 4 || !output || output_size != 4) {
            self->error = "invalid CPUID P-code userop signature";
            return -1;
        }
#if defined(__i386__) || defined(__x86_64__)
        unsigned int eax = static_cast<uint32_t>(arguments[0]);
        unsigned int ebx = 0;
        unsigned int ecx = 0;
        unsigned int edx = 0;
        (void)__get_cpuid_count(eax, 0, &eax, &ebx, &ecx, &edx);
        const std::array<uint32_t, 4> registers = {eax, ebx, edx, ecx};
        std::array<uint8_t, sizeof(registers)> bytes{};
        for (size_t register_index = 0; register_index < registers.size();
             ++register_index) {
            for (size_t byte_index = 0; byte_index < sizeof(uint32_t);
                 ++byte_index) {
                bytes[register_index * sizeof(uint32_t) + byte_index] =
                    static_cast<uint8_t>(registers[register_index] >>
                                         (byte_index * 8));
            }
        }
        if (!self->write_guest("ram", kGuestCpuidScratchAddress,
                               bytes.size(), bytes.data())) {
            self->error = "could not write CPUID P-code result";
            return -1;
        }
        *output = kGuestCpuidScratchAddress;
        return 0;
#else
        self->error = "CPUID P-code userops require an x86 host";
        return -1;
#endif
    }

    PcodeFunction resolve(uint32_t address) {
        const auto found = functions.find(address);
        if (found != functions.end()) return found->second;

        char symbol[16]{};
        std::snprintf(symbol, sizeof(symbol), "rvi_%08x", address);
        PcodeFunction function = nullptr;
        const auto lookup = [&](void* loaded_module, bool reject_duplicate) {
            dlerror();
            void* value = dlsym(loaded_module, symbol);
            if (dlerror() || !value) return true;
            if (function && reject_duplicate) {
                error = "duplicate P-code export " + std::string(symbol);
                return false;
            }
            function = reinterpret_cast<PcodeFunction>(value);
            return true;
        };
        for (void* override_module : override_modules) {
            if (!lookup(override_module, true)) return nullptr;
        }
        if (!function) {
            if (!lookup(module, true)) return nullptr;
            for (void* supplemental : supplemental_modules) {
                if (!lookup(supplemental, true)) return nullptr;
            }
        }
        if (!function) {
            error = "P-code module has no exported function " +
                    std::string(symbol);
            if (!active_guest_functions.empty()) {
                char caller[48]{};
                std::snprintf(caller, sizeof(caller),
                              " called from guest function 0x%08x",
                              active_guest_functions.back());
                error += caller;
            }
            return nullptr;
        }
        functions.emplace(address, function);
        return function;
    }

    bool load_supplemental_module(const std::string& path) {
        error.clear();
        if (execution_started || call_depth != 0) {
            error = "cannot load a supplemental P-code module after execution starts";
            return false;
        }
        void* supplemental = dlopen(path.c_str(), RTLD_NOW | RTLD_LOCAL);
        if (!supplemental) {
            const char* load_error = dlerror();
            error = "cannot load supplemental P-code module: " +
                    std::string(load_error ? load_error : "unknown dlopen error");
            return false;
        }
        supplemental_modules.push_back(supplemental);
        return true;
    }

    bool load_override_module(const std::string& path) {
        error.clear();
        if (execution_started || call_depth != 0) {
            error = "cannot load an override P-code module after execution starts";
            return false;
        }
        void* override_module = dlopen(path.c_str(), RTLD_NOW | RTLD_LOCAL);
        if (!override_module) {
            const char* load_error = dlerror();
            error = "cannot load override P-code module: " +
                    std::string(load_error ? load_error : "unknown dlopen error");
            return false;
        }
        override_modules.push_back(override_module);
        return true;
    }

    int dispatch(uint64_t target) {
        if (target > std::numeric_limits<uint32_t>::max()) {
            error = "P-code call target exceeds the x86-32 address space";
            return -1;
        }
        if (call_depth >= kMaximumCallDepth) {
            error = "P-code call depth limit exceeded";
            return -1;
        }
        const auto import_id =
            import_id_traps.find(static_cast<uint32_t>(target));
        if (import_id != import_id_traps.end()) target = import_id->second;
        const auto imported = import_traps.find(
            static_cast<uint32_t>(target));
        if (imported != import_traps.end()) {
            const auto& name = imported->second;
            if (name == "KERNEL32.dll!GetSystemTimeAsFileTime")
                return get_system_time_as_file_time();
            if (name == "KERNEL32.dll!GetCurrentProcessId")
                return get_current_process_id();
            if (name == "KERNEL32.dll!GetCurrentProcess")
                return get_current_process();
            if (name == "KERNEL32.dll!GetPriorityClass")
                return get_priority_class();
            if (name == "KERNEL32.dll!GetCurrentThread")
                return get_current_thread();
            if (name == "KERNEL32.dll!GetThreadPriority")
                return get_thread_priority();
            if (name == "KERNEL32.dll!SetPriorityClass")
                return set_priority_class();
            if (name == "KERNEL32.dll!SetThreadPriority")
                return set_thread_priority();
            if (name == "KERNEL32.dll!SetThreadIdealProcessor")
                return set_thread_ideal_processor();
            if (name == "KERNEL32.dll!SwitchToThread")
                return switch_to_thread();
            if (name == "KERNEL32.dll!CreateThread")
                return create_thread();
            if (name == "KERNEL32.dll!ResumeThread")
                return resume_thread();
            if (name == "KERNEL32.dll!SuspendThread")
                return suspend_thread();
            if (name == "KERNEL32.dll!GetExitCodeThread")
                return get_exit_code_thread();
            if (name == "KERNEL32.dll!ExitThread")
                return exit_thread();
            if (name == "KERNEL32.dll!GetCurrentThreadId")
                return get_current_thread_id();
            if (name == "KERNEL32.dll!GetTickCount")
                return get_tick_count();
            if (name == "KERNEL32.dll!GetLocalTime")
                return get_local_time();
            if (name == "KERNEL32.dll!ConvertThreadToFiber")
                return convert_thread_to_fiber();
            if (name == "KERNEL32.dll!IsThreadAFiber")
                return is_thread_a_fiber();
            if (name == "KERNEL32.dll!GlobalMemoryStatus")
                return global_memory_status();
            if (name == "WINMM.dll!timeBeginPeriod")
                return time_begin_period();
            if (name == "WINMM.dll!timeEndPeriod")
                return time_end_period();
            if (name == "WINMM.dll!timeGetTime")
                return time_get_time();
            if (name == "KERNEL32.dll!QueryPerformanceCounter")
                return query_performance_counter();
            if (name == "KERNEL32.dll!QueryPerformanceFrequency")
                return query_performance_frequency();
            if (name == "KERNEL32.dll!GetStartupInfoA")
                return get_startup_info_a();
            if (name == "KERNEL32.dll!GetProcessHeap")
                return get_process_heap();
            if (name == "KERNEL32.dll!CreateMutexA")
                return create_mutex_a();
            if (name == "KERNEL32.dll!WaitForSingleObject")
                return wait_for_single_object();
            if (name == "KERNEL32.dll!WaitForSingleObjectEx")
                return wait_for_single_object_ex();
            if (name == "KERNEL32.dll!CreateEventW")
                return create_event(true);
            if (name == "KERNEL32.dll!CreateEventA")
                return create_event(false);
            if (name == "KERNEL32.dll!SetEvent") return set_event(true);
            if (name == "KERNEL32.dll!ResetEvent") return set_event(false);
            if (name == "KERNEL32.dll!InterlockedCompareExchange")
                return interlocked_compare_exchange();
            if (name == "KERNEL32.dll!InterlockedExchange")
                return interlocked_exchange();
            if (name == "KERNEL32.dll!VirtualAlloc")
                return virtual_alloc();
            if (name == "KERNEL32.dll!VirtualFree")
                return virtual_free();
            if (name == "KERNEL32.dll!ReleaseMutex")
                return release_mutex();
            if (name == "KERNEL32.dll!CloseHandle")
                return close_handle();
            if (name == "KERNEL32.dll!CreateFileA")
                return create_file_a();
            if (name == "KERNEL32.dll!GetFileSize")
                return get_file_size();
            if (name == "KERNEL32.dll!ReadFile")
                return read_file();
            if (name == "KERNEL32.dll!HeapCreate")
                return heap_create();
            if (name == "KERNEL32.dll!HeapAlloc")
                return heap_alloc();
            if (name == "KERNEL32.dll!HeapReAlloc")
                return heap_realloc();
            if (name == "KERNEL32.dll!HeapSize")
                return heap_size();
            if (name == "KERNEL32.dll!HeapFree")
                return heap_free();
            if (name == "KERNEL32.dll!GetVersionExA")
                return get_version_ex_a();
            if (name == "KERNEL32.dll!SetUnhandledExceptionFilter")
                return set_unhandled_exception_filter();
            if (name == "KERNEL32.dll!GetModuleHandleA")
                return get_module_handle_a();
            if (name == "KERNEL32.dll!GetModuleFileNameA")
                return get_module_file_name_a();
            if (name == "KERNEL32.dll!GetProcAddress")
                return get_proc_address();
            if (name == "KERNEL32.dll!TlsAlloc") return tls_alloc();
            if (name == "KERNEL32.dll!TlsGetValue") return tls_get_value();
            if (name == "KERNEL32.dll!TlsSetValue") return tls_set_value();
            if (name == "KERNEL32.dll!TlsFree") return tls_free();
            if (name ==
                "KERNEL32.dll!InitializeCriticalSectionAndSpinCount") {
                return initialize_critical_section_and_spin_count();
            }
            if (name == "KERNEL32.dll!InterlockedIncrement")
                return interlocked_increment();
            if (name == "KERNEL32.dll!InterlockedDecrement")
                return interlocked_decrement();
            if (name == "KERNEL32.dll!EnterCriticalSection")
                return enter_critical_section(false);
            if (name == "KERNEL32.dll!TryEnterCriticalSection")
                return enter_critical_section(true);
            if (name == "KERNEL32.dll!LeaveCriticalSection")
                return leave_critical_section();
            if (name == "KERNEL32.dll!DeleteCriticalSection")
                return delete_critical_section();
            if (name == "KERNEL32.dll!InitializeCriticalSection")
                return initialize_critical_section();
            if (name == "KERNEL32.dll!SetCriticalSectionSpinCount")
                return set_critical_section_spin_count();
            if (name == "KERNEL32.dll!GetStdHandle")
                return get_std_handle();
            if (name == "KERNEL32.dll!GetFileType")
                return get_file_type();
            if (name == "KERNEL32.dll!SetHandleCount")
                return set_handle_count();
            if (name == "KERNEL32.dll!GetCommandLineA")
                return get_command_line_a();
            if (name == "KERNEL32.dll!GetEnvironmentStringsW")
                return get_environment_strings(true);
            if (name == "KERNEL32.dll!GetEnvironmentStringsA" ||
                name == "KERNEL32.dll!GetEnvironmentStrings")
                return get_environment_strings(false);
            if (name == "KERNEL32.dll!GetEnvironmentVariableA")
                return get_environment_variable_a();
            if (name == "KERNEL32.dll!SetEnvironmentVariableA")
                return set_environment_variable_a();
            if (name == "KERNEL32.dll!FreeEnvironmentStringsW")
                return free_environment_strings(true);
            if (name == "KERNEL32.dll!FreeEnvironmentStringsA" ||
                name == "KERNEL32.dll!FreeEnvironmentStrings")
                return free_environment_strings(false);
            if (name == "KERNEL32.dll!WideCharToMultiByte")
                return wide_char_to_multi_byte();
            if (name == "KERNEL32.dll!MultiByteToWideChar")
                return multi_byte_to_wide_char();
            if (name == "KERNEL32.dll!LCMapStringW")
                return locale_map_string_w();
            if (name == "KERNEL32.dll!GetLastError")
                return get_last_error();
            if (name == "KERNEL32.dll!SetLastError")
                return set_last_error();
            if (name == "KERNEL32.dll!RaiseException")
                return raise_exception();
            if (name == "KERNEL32.dll!GetACP")
                return get_ansi_code_page();
            if (name == "KERNEL32.dll!IsValidCodePage")
                return is_valid_code_page();
            if (name == "KERNEL32.dll!GetCPInfo")
                return get_code_page_info();
            if (name == "KERNEL32.dll!GetStringTypeW")
                return get_string_type_w();
            if (name == "imagehlp.dll!SymSetOptions")
                return sym_set_options();
            if (name == "imagehlp.dll!SymInitialize")
                return sym_initialize();
            if (name == "imagehlp.dll!SymCleanup")
                return sym_cleanup();
            if (name == "imagehlp.dll!SymFunctionTableAccess64")
                return sym_function_table_access64();
            if (name == "imagehlp.dll!SymGetModuleBase64")
                return sym_get_module_base64();
            if (name == "imagehlp.dll!SymFromAddr")
                return sym_from_addr();
            if (name == "imagehlp.dll!SymGetLineFromAddr64")
                return sym_get_line_from_addr64();
            error = "unimplemented PE import " + imported->second;
            if (!active_guest_functions.empty()) {
                char address[48]{};
                std::snprintf(address, sizeof(address),
                              " called from 0x%08x",
                              active_guest_functions.back());
                error += address;
            }
            uint32_t esp = 0;
            if (read_guest_u32("register", kX86EspRegisterOffset, esp)) {
                error += " args=[";
                for (uint32_t index = 0; index < 6; ++index) {
                    uint32_t argument = 0;
                    if (!read_guest_u32("ram",
                                        static_cast<uint64_t>(esp) + 4 +
                                            index * sizeof(uint32_t),
                                        argument)) {
                        break;
                    }
                    char value[16]{};
                    std::snprintf(value, sizeof(value), "%s0x%08x",
                                  index == 0 ? "" : ",", argument);
                    error += value;
                }
                error += "]";
            }
            return -1;
        }
        int indirect_jump_result = -1;
        if (dispatch_x86_absolute_indirect_jump(
                static_cast<uint32_t>(target), indirect_jump_result)) {
            return indirect_jump_result;
        }
        const auto function = resolve(static_cast<uint32_t>(target));
        if (!function) {
            const std::string unresolved_error = error;
            error.clear();
            int thunk_result = -1;
            if (dispatch_tls_alloc_wrapper(static_cast<uint32_t>(target),
                                           thunk_result)) {
                if (thunk_result == 0)
                    error.clear();
                else if (error.empty())
                    error = unresolved_error;
                return thunk_result;
            }
            error = unresolved_error;
            return -1;
        }

        ++call_depth;
        ++function_count;
        unique_function_addresses.insert(static_cast<uint32_t>(target));
        active_guest_functions.push_back(static_cast<uint32_t>(target));
        const int result = function(&context);
        active_guest_functions.pop_back();
        --call_depth;
        if (current_guest_thread_handle != 0 &&
            current_guest_thread_exit_requested) {
            return kGuestThreadExitResult;
        }
        if (result != 0 && error.empty()) {
            char message[96]{};
            std::snprintf(message, sizeof(message),
                          "P-code function 0x%08x returned %d",
                          static_cast<uint32_t>(target), result);
            error = message;
        }
        return result;
    }

    bool dispatch_x86_absolute_indirect_jump(uint32_t address, int& result) {
        if (pe_image_size == 0 || address < pe_image_base ||
            static_cast<uint64_t>(address) + 6 >
                static_cast<uint64_t>(pe_image_base) + pe_image_size) {
            return false;
        }
        std::array<uint8_t, 6> instruction{};
        if (!read_guest("ram", address, instruction.size(),
                        instruction.data()) ||
            instruction[0] != 0xff || instruction[1] != 0x25) {
            return false;
        }
        const uint32_t pointer_address =
            static_cast<uint32_t>(instruction[2]) |
            (static_cast<uint32_t>(instruction[3]) << 8) |
            (static_cast<uint32_t>(instruction[4]) << 16) |
            (static_cast<uint32_t>(instruction[5]) << 24);
        uint32_t target = 0;
        if (!valid_guest_pointer(pointer_address, sizeof(uint32_t)) ||
            !read_guest_u32("ram", pointer_address, target) || target == 0) {
            error = "x86 indirect jump thunk has an invalid target pointer";
            result = -1;
            return true;
        }
        if (indirect_jump_depth >= kMaximumCallDepth) {
            error = "x86 indirect jump thunk chain exceeded the call limit";
            result = -1;
            return true;
        }
        ++indirect_jump_depth;
        result = dispatch(target);
        --indirect_jump_depth;
        return true;
    }

    bool dispatch_tls_alloc_wrapper(uint32_t address, int& result) {
        if (pe_image_size == 0 || address < pe_image_base ||
            static_cast<uint64_t>(address) + 9 >
                static_cast<uint64_t>(pe_image_base) + pe_image_size) {
            return false;
        }
        std::array<uint8_t, 9> code{};
        if (!read_guest("ram", address, code.size(), code.data())) return false;
        if (code[0] != 0xff || code[1] != 0x15 || code[6] != 0xc2 ||
            code[7] != 0x04 || code[8] != 0x00) {
            return false;
        }
        const uint32_t iat_address =
            static_cast<uint32_t>(code[2]) |
            (static_cast<uint32_t>(code[3]) << 8) |
            (static_cast<uint32_t>(code[4]) << 16) |
            (static_cast<uint32_t>(code[5]) << 24);
        uint32_t import_stub = 0;
        if (!read_guest_u32("ram", iat_address, import_stub)) return false;
        const auto imported = import_traps.find(import_stub);
        if (imported == import_traps.end() ||
            imported->second != "KERNEL32.dll!TlsAlloc") {
            return false;
        }
        uint32_t original_esp = 0;
        if (!read_guest_u32("register", kX86EspRegisterOffset, original_esp)) {
            result = -1;
            return true;
        }
        if (original_esp < sizeof(uint32_t)) {
            error = "KERNEL32.dll!TlsAlloc wrapper has an invalid ESP";
            result = -1;
            return true;
        }
        const uint32_t nested_esp = original_esp - sizeof(uint32_t);
        if (!write_guest_u32("ram", nested_esp, address + 6) ||
            !write_guest_u32("register", kX86EspRegisterOffset,
                             nested_esp)) {
            result = -1;
            return true;
        }
        result = dispatch(import_stub);
        if (result == 0) {
            if (!write_guest_u32("register", kX86EspRegisterOffset,
                                 original_esp + 8)) {
                result = -1;
                return true;
            }
        } else {
            (void)write_guest_u32("register", kX86EspRegisterOffset,
                                  original_esp);
        }
        return true;
    }

    bool read_guest_u32(const char* space, uint64_t offset, uint32_t& value) {
        std::array<uint8_t, 4> bytes{};
        if (!read_guest(space, offset, bytes.size(), bytes.data())) return false;
        value = static_cast<uint32_t>(bytes[0]) |
                (static_cast<uint32_t>(bytes[1]) << 8) |
                (static_cast<uint32_t>(bytes[2]) << 16) |
                (static_cast<uint32_t>(bytes[3]) << 24);
        return true;
    }

    bool write_guest_u32(const char* space, uint64_t offset, uint32_t value) {
        const std::array<uint8_t, 4> bytes = {
            static_cast<uint8_t>(value), static_cast<uint8_t>(value >> 8),
            static_cast<uint8_t>(value >> 16),
            static_cast<uint8_t>(value >> 24)};
        return write_guest(space, offset, bytes.size(), bytes.data());
    }

    bool write_guest_u64(const char* space, uint64_t offset, uint64_t value) {
        std::array<uint8_t, 8> bytes{};
        for (size_t index = 0; index < bytes.size(); ++index)
            bytes[index] = static_cast<uint8_t>(value >> (index * 8));
        return write_guest(space, offset, bytes.size(), bytes.data());
    }

    bool read_stack_argument(uint32_t index, uint32_t& value,
                             const char* api) {
        uint32_t esp = 0;
        if (!read_guest_u32("register", kX86EspRegisterOffset, esp)) {
            error = std::string(api) + " cannot read ESP";
            return false;
        }
        if (!read_guest_u32("ram", static_cast<uint64_t>(esp) + 4 +
                                       static_cast<uint64_t>(index) * 4,
                            value)) {
            error = std::string(api) + " has an invalid stack argument";
            return false;
        }
        return true;
    }

    bool finish_stdcall(uint32_t argument_bytes, const char* api) {
        uint32_t esp = 0;
        if (!read_guest_u32("register", kX86EspRegisterOffset, esp)) {
            error = std::string(api) + " cannot read ESP";
            return false;
        }
        if (!write_guest_u32("register", kX86EspRegisterOffset,
                             esp + 4 + argument_bytes)) {
            error = std::string(api) + " cannot restore ESP";
            return false;
        }
        return true;
    }

    bool valid_guest_pointer(uint32_t address, size_t size) const {
        return address != 0 && static_cast<uint64_t>(address) + size <=
                                    kGuestRamSize;
    }

    bool read_guest_bytes(uint32_t address, uint8_t* output, size_t size,
                          const char* api) {
        if (!output || !valid_guest_pointer(address, size)) {
            error = std::string(api) + " has an invalid input pointer";
            return false;
        }
        for (size_t offset = 0; offset < size;
             offset += kMaximumPcodeValueSize) {
            const size_t chunk = std::min(kMaximumPcodeValueSize,
                                          size - offset);
            if (!read_guest("ram", static_cast<uint64_t>(address) + offset,
                            chunk, output + offset)) {
                error = std::string(api) + " cannot read its input";
                return false;
            }
        }
        return true;
    }

    bool write_guest_bytes(uint32_t address, const uint8_t* input,
                           size_t size, const char* api) {
        if (!input || !valid_guest_pointer(address, size)) {
            error = std::string(api) + " has an invalid output pointer";
            return false;
        }
        for (size_t offset = 0; offset < size;
             offset += kMaximumPcodeValueSize) {
            const size_t chunk = std::min(kMaximumPcodeValueSize,
                                          size - offset);
            if (!write_guest("ram", static_cast<uint64_t>(address) + offset,
                             chunk, input + offset)) {
                error = std::string(api) + " cannot write its output";
                return false;
            }
        }
        return true;
    }

    bool is_supported_kernel32_api(const std::string& name) const {
        static const std::unordered_set<std::string> supported = {
            "GetCurrentProcess", "GetPriorityClass", "GetCurrentProcessId",
            "GetCurrentThread", "GetThreadPriority", "SetPriorityClass",
            "SetThreadPriority", "SetThreadIdealProcessor",
            "SwitchToThread",
            "GetCurrentThreadId", "GetTickCount",
            "CreateThread", "ResumeThread", "SuspendThread",
            "GetExitCodeThread", "ExitThread",
            "GetLocalTime",
            "ConvertThreadToFiber", "IsThreadAFiber",
            "GlobalMemoryStatus",
            "GetSystemTimeAsFileTime", "QueryPerformanceCounter",
            "QueryPerformanceFrequency", "GetStartupInfoA", "GetProcessHeap",
            "CreateMutexA", "WaitForSingleObject", "ReleaseMutex",
            "WaitForSingleObjectEx", "CreateEventW", "CreateEventA",
            "SetEvent", "ResetEvent",
            "InterlockedCompareExchange",
            "InterlockedExchange",
            "VirtualAlloc", "VirtualFree",
            "CloseHandle",
            "CreateFileA", "GetFileSize", "ReadFile",
            "HeapCreate", "HeapAlloc", "HeapReAlloc", "HeapSize", "HeapFree", "GetVersionExA",
            "SetUnhandledExceptionFilter", "GetModuleHandleA",
            "GetModuleFileNameA", "GetProcAddress",
            "TlsAlloc", "TlsGetValue",
            "TlsSetValue", "TlsFree",
            "InitializeCriticalSectionAndSpinCount", "InterlockedIncrement",
            "InterlockedDecrement",
            "EnterCriticalSection", "TryEnterCriticalSection",
            "LeaveCriticalSection", "DeleteCriticalSection",
            "InitializeCriticalSection", "SetCriticalSectionSpinCount",
            "GetStdHandle", "GetFileType", "SetHandleCount",
            "GetCommandLineA", "GetEnvironmentStrings",
            "GetEnvironmentStringsA", "GetEnvironmentStringsW",
            "GetEnvironmentVariableA", "SetEnvironmentVariableA",
            "FreeEnvironmentStrings", "FreeEnvironmentStringsA",
            "FreeEnvironmentStringsW", "WideCharToMultiByte", "GetLastError",
            "SetLastError", "RaiseException", "GetACP", "IsValidCodePage", "GetCPInfo",
            "GetStringTypeW", "MultiByteToWideChar", "LCMapStringW"};
        return supported.find(name) != supported.end();
    }

    bool allocate_dynamic_import_stub(const std::string& name,
                                      uint32_t& address) {
        uint64_t candidate = next_dynamic_import_stub_address;
        while (candidate >= 0x10000 &&
               candidate + kImportStubStride <= kGuestRamSize) {
            bool available = true;
            if (pe_image_size != 0) {
                const uint64_t image_end =
                    static_cast<uint64_t>(pe_image_base) + pe_image_size;
                if (candidate < image_end && pe_image_base <
                                                 candidate + kImportStubStride)
                    available = false;
            }
            if (available) {
                for (const auto& trap : import_traps) {
                    const uint64_t trap_begin = trap.first;
                    const uint64_t trap_end = trap_begin + kImportStubStride;
                    if (candidate < trap_end && trap_begin <
                                                   candidate + kImportStubStride) {
                        available = false;
                        break;
                    }
                }
            }
            if (available) {
                for (const auto& module : guest_module_handles) {
                    if (candidate <= module.second &&
                        module.second < candidate + kImportStubStride) {
                        available = false;
                        break;
                    }
                }
            }
            if (available) {
                address = static_cast<uint32_t>(candidate);
                next_dynamic_import_stub_address = candidate -
                                                   kImportStubStride;
                import_traps.emplace(address, name);
                return true;
            }
            candidate -= kImportStubStride;
        }
        return false;
    }

    bool read_guest_ascii(uint32_t address, std::string& value,
                          const char* api) {
        value.clear();
        for (size_t index = 0; index < kMaximumImportNameSize; ++index) {
            uint8_t byte = 0;
            if (!read_guest("ram", static_cast<uint64_t>(address) + index,
                            sizeof(byte), &byte)) {
                error = std::string(api) + " received an invalid string pointer";
                return false;
            }
            if (byte == 0) return true;
            if (byte < 0x20 || byte > 0x7e) {
                error = std::string(api) + " received a non-ASCII string";
                return false;
            }
            value.push_back(static_cast<char>(byte));
        }
        error = std::string(api) + " received an unterminated string";
        return false;
    }

    int return_kernel32_dword(uint32_t value, const char* api,
                              uint32_t argument_bytes = 0) {
        if (!write_guest_u32("register", kX86EaxRegisterOffset, value)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(argument_bytes, api) ? 0 : -1;
    }

    int get_local_time() {
        constexpr const char* api = "KERNEL32.dll!GetLocalTime";
        uint32_t output_address = 0;
        if (!read_stack_argument(0, output_address, api)) return -1;
        if (!valid_guest_pointer(output_address, 16)) {
            error = std::string(api) + " has an invalid output pointer";
            return -1;
        }

        const auto now = std::chrono::system_clock::now();
        const std::time_t seconds = std::chrono::system_clock::to_time_t(now);
        std::tm local{};
        if (!localtime_r(&seconds, &local)) {
            error = std::string(api) + " cannot convert the host local time";
            return -1;
        }
        auto milliseconds =
            std::chrono::duration_cast<std::chrono::milliseconds>(
                now.time_since_epoch())
                .count() % 1000;
        if (milliseconds < 0) milliseconds += 1000;

        std::array<uint8_t, 16> system_time{};
        const auto store_word = [&system_time](size_t offset, uint16_t value) {
            system_time[offset] = static_cast<uint8_t>(value);
            system_time[offset + 1] = static_cast<uint8_t>(value >> 8);
        };
        store_word(0, static_cast<uint16_t>(local.tm_year + 1900));
        store_word(2, static_cast<uint16_t>(local.tm_mon + 1));
        store_word(4, static_cast<uint16_t>(local.tm_wday));
        store_word(6, static_cast<uint16_t>(local.tm_mday));
        store_word(8, static_cast<uint16_t>(local.tm_hour));
        store_word(10, static_cast<uint16_t>(local.tm_min));
        store_word(12, static_cast<uint16_t>(local.tm_sec));
        store_word(14, static_cast<uint16_t>(milliseconds));
        if (!write_guest_bytes(output_address, system_time.data(),
                               system_time.size(), api)) {
            return -1;
        }
        return finish_stdcall(sizeof(uint32_t), api) ? 0 : -1;
    }

    int convert_thread_to_fiber() {
        constexpr const char* api = "KERNEL32.dll!ConvertThreadToFiber";
        uint32_t fiber_data = 0;
        if (!read_stack_argument(0, fiber_data, api)) return -1;
        if (current_guest_fiber != 0) {
            guest_last_error = kGuestAlreadyFiberError;
            return return_kernel32_dword(0, api, sizeof(uint32_t));
        }

        uint32_t teb_address = 0;
        uint32_t teb_self = 0;
        if (!read_guest_u32("register", kX86FsBaseRegisterOffset,
                            teb_address) ||
            !valid_guest_pointer(teb_address, 0x1c) ||
            !read_guest_u32("ram", teb_address + 0x18, teb_self) ||
            teb_self != teb_address) {
            error = std::string(api) + " requires an initialized guest TEB";
            return -1;
        }

        uint32_t handle = next_guest_fiber_handle;
        const uint64_t image_begin = pe_image_base;
        const uint64_t image_end = image_begin + pe_image_size;
        bool found_fiber_address = false;
        while (valid_guest_pointer(handle, sizeof(uint32_t))) {
            const bool overlaps_image =
                pe_image_size != 0 && handle < image_end &&
                image_begin < static_cast<uint64_t>(handle) +
                                  sizeof(uint32_t);
            if (!overlaps_image && guest_fibers.find(handle) ==
                                       guest_fibers.end()) {
                found_fiber_address = true;
                break;
            }
            if (handle > UINT32_MAX - kGuestFiberHandleStride) break;
            handle += kGuestFiberHandleStride;
        }
        if (!found_fiber_address) {
            guest_last_error = 8;
            return return_kernel32_dword(0, api, sizeof(uint32_t));
        }

        if (!write_guest_u32("ram", handle, fiber_data) ||
            !write_guest_u32("ram", teb_address + 0x10, handle)) {
            error = std::string(api) + " cannot initialize guest fiber data";
            return -1;
        }
        guest_fibers.emplace(handle, GuestFiber{fiber_data});
        current_guest_fiber = handle;
        next_guest_fiber_handle = handle + kGuestFiberHandleStride;
        return return_kernel32_dword(handle, api, sizeof(uint32_t));
    }

    int is_thread_a_fiber() {
        return return_kernel32_dword(current_guest_fiber != 0 ? 1 : 0,
                                     "KERNEL32.dll!IsThreadAFiber");
    }

    int global_memory_status() {
        constexpr const char* api = "KERNEL32.dll!GlobalMemoryStatus";
        constexpr uint64_t guest_virtual_limit = UINT64_C(1) << 31;
        uint32_t output_address = 0;
        if (!read_stack_argument(0, output_address, api)) return -1;
        if (!valid_guest_pointer(output_address, 8 * sizeof(uint32_t))) {
            error = std::string(api) + " has an invalid output pointer";
            return -1;
        }

        struct sysinfo host_memory {};
        if (sysinfo(&host_memory) != 0) {
            error = std::string(api) + " cannot query host memory status";
            return -1;
        }
        const uint64_t unit = host_memory.mem_unit == 0
                                  ? 1
                                  : host_memory.mem_unit;
        const auto to_bytes = [unit](uint64_t value) {
            return value > UINT64_MAX / unit ? UINT64_MAX : value * unit;
        };
        const auto saturating_add = [](uint64_t left, uint64_t right) {
            return right > UINT64_MAX - left ? UINT64_MAX : left + right;
        };
        const auto guest_size = [](uint64_t value) {
            return static_cast<uint32_t>(std::min<uint64_t>(
                value, std::numeric_limits<uint32_t>::max()));
        };
        const uint64_t total_physical = to_bytes(host_memory.totalram);
        const uint64_t available_physical = std::min(
            total_physical,
            to_bytes(saturating_add(host_memory.freeram,
                                    host_memory.bufferram)));
        const uint64_t total_page_file = to_bytes(saturating_add(
            host_memory.totalram, host_memory.totalswap));
        const uint64_t available_page_file = std::min(
            total_page_file,
            to_bytes(saturating_add(
                saturating_add(host_memory.freeram, host_memory.bufferram),
                host_memory.freeswap)));
        const uint32_t memory_load = total_physical == 0
                                         ? 0
                                         : static_cast<uint32_t>(std::clamp(
                                               (static_cast<long double>(
                                                    total_physical -
                                                    available_physical) *
                                                100.0L) /
                                                   total_physical,
                                               0.0L, 100.0L));

        uint64_t used_guest_virtual = pe_image_size;
        for (const auto& allocation : guest_virtual_allocations) {
            if (allocation.second > UINT64_MAX - used_guest_virtual) {
                used_guest_virtual = guest_virtual_limit;
                break;
            }
            used_guest_virtual += allocation.second;
        }
        used_guest_virtual = std::min(used_guest_virtual,
                                      guest_virtual_limit);
        const std::array<uint32_t, 8> fields = {
            8 * sizeof(uint32_t),
            memory_load,
            guest_size(total_physical),
            guest_size(available_physical),
            guest_size(total_page_file),
            guest_size(available_page_file),
            static_cast<uint32_t>(guest_virtual_limit),
            static_cast<uint32_t>(guest_virtual_limit -
                                  used_guest_virtual)};
        std::array<uint8_t, sizeof(fields)> status{};
        for (size_t index = 0; index < fields.size(); ++index) {
            for (size_t byte = 0; byte < sizeof(uint32_t); ++byte) {
                status[index * sizeof(uint32_t) + byte] =
                    static_cast<uint8_t>(fields[index] >> (byte * 8));
            }
        }
        if (!write_guest_bytes(output_address, status.data(), status.size(),
                               api)) {
            return -1;
        }
        return finish_stdcall(sizeof(uint32_t), api) ? 0 : -1;
    }

    int time_begin_period() {
        constexpr const char* api = "WINMM.dll!timeBeginPeriod";
        uint32_t period = 0;
        if (!read_stack_argument(0, period, api)) return -1;
        uint32_t result = kGuestTimerErrNoCanDo;
        if (period == kGuestTimerPeriodMs) {
            auto& requests = guest_timer_period_requests[period];
            if (requests != UINT32_MAX) {
                ++requests;
                result = kGuestTimerNoError;
            }
        }
        return return_kernel32_dword(result, api, sizeof(uint32_t));
    }

    int time_end_period() {
        constexpr const char* api = "WINMM.dll!timeEndPeriod";
        uint32_t period = 0;
        if (!read_stack_argument(0, period, api)) return -1;
        uint32_t result = kGuestTimerErrNoCanDo;
        const auto request = guest_timer_period_requests.find(period);
        if (request != guest_timer_period_requests.end()) {
            result = kGuestTimerNoError;
            if (--request->second == 0)
                guest_timer_period_requests.erase(request);
        }
        return return_kernel32_dword(result, api, sizeof(uint32_t));
    }

    int time_get_time() {
        return return_kernel32_dword(
            monotonic_tick_milliseconds(), "WINMM.dll!timeGetTime");
    }

    int get_current_process_id() {
        return return_kernel32_dword(static_cast<uint32_t>(getpid()),
                                     "KERNEL32.dll!GetCurrentProcessId");
    }

    int get_current_process() {
        return return_kernel32_dword(kGuestCurrentProcessPseudoHandle,
                                     "KERNEL32.dll!GetCurrentProcess");
    }

    int get_priority_class() {
        constexpr const char* api = "KERNEL32.dll!GetPriorityClass";
        uint32_t process_handle = 0;
        if (!read_stack_argument(0, process_handle, api)) return -1;
        if (process_handle != kGuestCurrentProcessPseudoHandle) {
            guest_last_error = 6;
            return return_kernel32_dword(0, api, sizeof(uint32_t));
        }
        return return_kernel32_dword(guest_process_priority_class, api,
                                     sizeof(uint32_t));
    }

    int get_current_thread() {
        return return_kernel32_dword(kGuestCurrentThreadPseudoHandle,
                                     "KERNEL32.dll!GetCurrentThread");
    }

    int sym_set_options() {
        constexpr const char* api = "imagehlp.dll!SymSetOptions";
        if (!read_stack_argument(0, guest_symbol_options, api)) return -1;
        return return_kernel32_dword(guest_symbol_options, api, 4);
    }

    int sym_initialize() {
        constexpr const char* api = "imagehlp.dll!SymInitialize";
        uint32_t process_handle = 0;
        uint32_t search_path = 0;
        uint32_t invade_process = 0;
        if (!read_stack_argument(0, process_handle, api) ||
            !read_stack_argument(1, search_path, api) ||
            !read_stack_argument(2, invade_process, api)) {
            return -1;
        }
        (void)search_path;
        (void)invade_process;
        if (process_handle == 0 || guest_symbol_handler_initialized) {
            guest_last_error = 87;
            return return_kernel32_dword(0, api, 12);
        }
        guest_symbol_process_handle = process_handle;
        guest_symbol_handler_initialized = true;
        return return_kernel32_dword(1, api, 12);
    }

    int sym_cleanup() {
        constexpr const char* api = "imagehlp.dll!SymCleanup";
        uint32_t process_handle = 0;
        if (!read_stack_argument(0, process_handle, api)) return -1;
        if (!guest_symbol_handler_initialized ||
            process_handle != guest_symbol_process_handle) {
            guest_last_error = 6;
            return return_kernel32_dword(0, api, 4);
        }
        guest_symbol_handler_initialized = false;
        guest_symbol_process_handle = 0;
        return return_kernel32_dword(1, api, 4);
    }

    int sym_function_table_access64() {
        constexpr const char* api = "imagehlp.dll!SymFunctionTableAccess64";
        uint32_t process_handle = 0;
        uint32_t address_low = 0;
        uint32_t address_high = 0;
        if (!read_stack_argument(0, process_handle, api) ||
            !read_stack_argument(1, address_low, api) ||
            !read_stack_argument(2, address_high, api)) {
            return -1;
        }
        (void)address_low;
        (void)address_high;
        if (!guest_symbol_handler_initialized ||
            process_handle != guest_symbol_process_handle) {
            guest_last_error = 6;
        }
        return return_kernel32_dword(0, api, 12);
    }

    int sym_get_module_base64() {
        constexpr const char* api = "imagehlp.dll!SymGetModuleBase64";
        uint32_t process_handle = 0;
        uint32_t address_low = 0;
        uint32_t address_high = 0;
        if (!read_stack_argument(0, process_handle, api) ||
            !read_stack_argument(1, address_low, api) ||
            !read_stack_argument(2, address_high, api)) {
            return -1;
        }
        if (!guest_symbol_handler_initialized ||
            process_handle != guest_symbol_process_handle) {
            guest_last_error = 6;
            return return_kernel32_dword(0, api, 12);
        }
        const uint64_t address = (static_cast<uint64_t>(address_high) << 32) |
                                 address_low;
        const uint64_t image_begin = pe_image_base;
        const uint64_t image_end = image_begin + pe_image_size;
        const uint32_t module_base =
            address >= image_begin && address < image_end ? pe_image_base : 0;
        return return_kernel32_dword(module_base, api, 12);
    }

    int sym_from_addr() {
        constexpr const char* api = "imagehlp.dll!SymFromAddr";
        uint32_t process_handle = 0;
        uint32_t address_low = 0;
        uint32_t address_high = 0;
        uint32_t displacement = 0;
        uint32_t symbol_info = 0;
        if (!read_stack_argument(0, process_handle, api) ||
            !read_stack_argument(1, address_low, api) ||
            !read_stack_argument(2, address_high, api) ||
            !read_stack_argument(3, displacement, api) ||
            !read_stack_argument(4, symbol_info, api)) {
            return -1;
        }
        (void)address_low;
        (void)address_high;
        (void)displacement;
        (void)symbol_info;
        guest_last_error = process_handle == guest_symbol_process_handle
                               ? 126
                               : 6;
        return return_kernel32_dword(0, api, 20);
    }

    int sym_get_line_from_addr64() {
        constexpr const char* api = "imagehlp.dll!SymGetLineFromAddr64";
        uint32_t process_handle = 0;
        uint32_t address_low = 0;
        uint32_t address_high = 0;
        uint32_t displacement = 0;
        uint32_t line_info = 0;
        if (!read_stack_argument(0, process_handle, api) ||
            !read_stack_argument(1, address_low, api) ||
            !read_stack_argument(2, address_high, api) ||
            !read_stack_argument(3, displacement, api) ||
            !read_stack_argument(4, line_info, api)) {
            return -1;
        }
        (void)address_low;
        (void)address_high;
        (void)displacement;
        (void)line_info;
        guest_last_error = process_handle == guest_symbol_process_handle
                               ? 126
                               : 6;
        return return_kernel32_dword(0, api, 20);
    }

    int get_thread_priority() {
        constexpr const char* api = "KERNEL32.dll!GetThreadPriority";
        uint32_t thread_handle = 0;
        if (!read_stack_argument(0, thread_handle, api)) return -1;
        if (thread_handle == kGuestCurrentThreadPseudoHandle)
            return return_kernel32_dword(
                static_cast<uint32_t>(guest_thread_priority), api,
                sizeof(uint32_t));
        const auto thread = guest_threads.find(thread_handle);
        if (thread == guest_threads.end()) {
            guest_last_error = 6;
            return return_kernel32_dword(0x7fffffffu, api, sizeof(uint32_t));
        }
        return return_kernel32_dword(
            static_cast<uint32_t>(thread->second.priority), api,
            sizeof(uint32_t));
    }

    int set_priority_class() {
        constexpr const char* api = "KERNEL32.dll!SetPriorityClass";
        uint32_t process_handle = 0;
        uint32_t priority_class = 0;
        if (!read_stack_argument(0, process_handle, api) ||
            !read_stack_argument(1, priority_class, api)) {
            return -1;
        }
        if (process_handle != kGuestCurrentProcessPseudoHandle) {
            guest_last_error = 6;
            return return_kernel32_dword(0, api, 2 * sizeof(uint32_t));
        }
        constexpr std::array<uint32_t, 6> valid_classes = {
            0x00000020, 0x00000040, 0x00000080,
            0x00000100, 0x00000400, 0x00000800};
        if (std::find(valid_classes.begin(), valid_classes.end(),
                      priority_class) == valid_classes.end()) {
            guest_last_error = 87;
            return return_kernel32_dword(0, api, 2 * sizeof(uint32_t));
        }
        guest_process_priority_class = priority_class;
        return return_kernel32_dword(1, api, 2 * sizeof(uint32_t));
    }

    int set_thread_priority() {
        constexpr const char* api = "KERNEL32.dll!SetThreadPriority";
        uint32_t thread_handle = 0;
        uint32_t priority_word = 0;
        if (!read_stack_argument(0, thread_handle, api) ||
            !read_stack_argument(1, priority_word, api)) {
            return -1;
        }
        const int32_t priority = static_cast<int32_t>(priority_word);
        constexpr std::array<int32_t, 7> valid_priorities = {
            -15, -2, -1, 0, 1, 2, 15};
        if (std::find(valid_priorities.begin(), valid_priorities.end(),
                      priority) == valid_priorities.end()) {
            guest_last_error = 87;
            return return_kernel32_dword(0, api, 2 * sizeof(uint32_t));
        }
        if (thread_handle == kGuestCurrentThreadPseudoHandle) {
            guest_thread_priority = priority;
        } else {
            const auto thread = guest_threads.find(thread_handle);
            if (thread == guest_threads.end()) {
                guest_last_error = 6;
                return return_kernel32_dword(0, api, 2 * sizeof(uint32_t));
            }
            thread->second.priority = priority;
        }
        return return_kernel32_dword(1, api, 2 * sizeof(uint32_t));
    }

    int set_thread_ideal_processor() {
        constexpr const char* api =
            "KERNEL32.dll!SetThreadIdealProcessor";
        constexpr uint32_t kMaximumProcessors = 32;
        uint32_t thread_handle = 0;
        uint32_t requested_processor = 0;
        if (!read_stack_argument(0, thread_handle, api) ||
            !read_stack_argument(1, requested_processor, api)) {
            return -1;
        }

        uint32_t* ideal_processor = nullptr;
        if (thread_handle == kGuestCurrentThreadPseudoHandle) {
            ideal_processor = &guest_thread_ideal_processor;
        } else {
            const auto thread = guest_threads.find(thread_handle);
            if (thread == guest_threads.end()) {
                guest_last_error = 6;
                return return_kernel32_dword(UINT32_MAX, api,
                                             2 * sizeof(uint32_t));
            }
            ideal_processor = &thread->second.ideal_processor;
        }

        const uint32_t previous_processor = *ideal_processor;
        if (requested_processor != kMaximumProcessors) {
            if (requested_processor >= kMaximumProcessors) {
                guest_last_error = 87;
                return return_kernel32_dword(UINT32_MAX, api,
                                             2 * sizeof(uint32_t));
            }
            *ideal_processor = requested_processor;
        }
        return return_kernel32_dword(previous_processor, api,
                                     2 * sizeof(uint32_t));
    }

    int switch_to_thread() {
        constexpr const char* api = "KERNEL32.dll!SwitchToThread";
        if (!scheduler_context_active || !guest_coroutine_active) {
            std::this_thread::yield();
            return return_kernel32_dword(0, api, 0);
        }

        const bool another_guest_thread_ready = !ready_guest_threads.empty();
        enqueue_guest_thread(current_guest_thread_handle);
        pause_scheduler_after_yield = !another_guest_thread_ready;
        if (!yield_current_guest_thread(false)) return -1;
        return return_kernel32_dword(another_guest_thread_ready ? 1 : 0,
                                     api, 0);
    }

    void release_guest_thread_blocks(const GuestThread& thread) {
        for (const auto& block : {thread.stack, thread.teb}) {
            const auto allocation = heap_allocations.find(block.address);
            if (allocation == heap_allocations.end()) continue;
            free_heap_blocks.push_back(allocation->second);
            heap_allocations.erase(allocation);
        }
    }

    bool initialize_guest_thread_teb(const GuestThread& thread) {
        std::memset(static_cast<uint8_t*>(ram) + thread.teb.address, 0,
                    kGuestTebSize);
        const uint32_t stack_top = thread.stack.address +
                                   static_cast<uint32_t>(thread.stack.size);
        return write_guest_u32("ram", thread.teb.address, UINT32_MAX) &&
               write_guest_u32("ram", thread.teb.address + 4, stack_top) &&
               write_guest_u32("ram", thread.teb.address + 8,
                               thread.stack.address) &&
               write_guest_u32("ram", thread.teb.address + 0x18,
                               thread.teb.address) &&
               write_guest_u32("ram", thread.teb.address + 0x20,
                               static_cast<uint32_t>(getpid())) &&
               write_guest_u32("ram", thread.teb.address + 0x24,
                               thread.id);
    }

    GuestThread* guest_execution_state(uint32_t handle) {
        if (handle == 0) return &main_guest_thread;
        const auto found = guest_threads.find(handle);
        return found == guest_threads.end() ? nullptr : &found->second;
    }

    void save_execution_state(GuestExecutionState& state) {
        state.registers = registers;
        state.tls_values = tls_values;
        state.active_functions = active_guest_functions;
        state.last_error = guest_last_error;
        state.priority = guest_thread_priority;
        state.ideal_processor = guest_thread_ideal_processor;
        state.current_fiber = current_guest_fiber;
        state.current_exit_code = current_guest_thread_exit_code;
        state.exit_requested = current_guest_thread_exit_requested;
        state.call_depth = call_depth;
        state.indirect_jump_depth = indirect_jump_depth;
    }

    void load_execution_state(const GuestExecutionState& state,
                              uint32_t handle) {
        registers = state.registers;
        tls_values = state.tls_values;
        active_guest_functions = state.active_functions;
        guest_last_error = state.last_error;
        guest_thread_priority = state.priority;
        guest_thread_ideal_processor = state.ideal_processor;
        current_guest_fiber = state.current_fiber;
        current_guest_thread_exit_code = state.current_exit_code;
        current_guest_thread_exit_requested = state.exit_requested;
        call_depth = state.call_depth;
        indirect_jump_depth = state.indirect_jump_depth;
        current_guest_thread_handle = handle;
        const auto* thread = guest_execution_state(handle);
        current_guest_thread_id = thread ? thread->id : 0;
    }

    bool initialize_guest_coroutine(uint32_t handle) {
        GuestThread* thread = guest_execution_state(handle);
        if (!thread) return false;
        if (thread->coroutine_initialized) return true;

        thread->coroutine_stack_size = handle == 0
            ? 8 * 1024 * 1024
            : std::clamp<size_t>(thread->stack.size, 256 * 1024,
                                 8 * 1024 * 1024);
        thread->coroutine_stack =
            std::make_unique<uint8_t[]>(thread->coroutine_stack_size);
        if (getcontext(&thread->coroutine) != 0) {
            error = "cannot initialize guest thread coroutine context";
            return false;
        }
        thread->coroutine.uc_stack.ss_sp = thread->coroutine_stack.get();
        thread->coroutine.uc_stack.ss_size = thread->coroutine_stack_size;
        thread->coroutine.uc_stack.ss_flags = 0;
        thread->coroutine.uc_link = &scheduler_context;
        makecontext(&thread->coroutine, &Impl::guest_coroutine_entry, 0);
        thread->coroutine_initialized = true;
        return true;
    }

    static void guest_coroutine_entry() {
        auto* self = static_cast<Impl*>(active_pcode_scheduler);
        if (self) self->run_current_guest_coroutine();
    }

    void enqueue_guest_thread(uint32_t handle) {
        GuestThread* thread = guest_execution_state(handle);
        if (!thread || thread->completed || thread->waiting ||
            thread->suspend_count != 0 ||
            thread->runnable) {
            return;
        }
        thread->runnable = true;
        ready_guest_threads.push_back(handle);
    }

    bool yield_current_guest_thread(bool requeue) {
        if (!scheduler_context_active || !guest_coroutine_active) {
            error = "guest thread yielded outside the cooperative scheduler";
            return false;
        }
        const uint32_t handle = current_guest_thread_handle;
        GuestThread* thread = guest_execution_state(handle);
        if (!thread) {
            error = "active guest thread context disappeared";
            return false;
        }
        if (requeue) enqueue_guest_thread(handle);
        save_execution_state(*thread);
        guest_coroutine_active = false;
        if (swapcontext(&thread->coroutine, &scheduler_context) != 0) {
            error = "cannot switch from a guest thread to the scheduler";
            return false;
        }
        guest_coroutine_active = true;
        return true;
    }

    void complete_current_guest_thread() {
        const uint32_t handle = current_guest_thread_handle;
        GuestThread* thread = guest_execution_state(handle);
        if (!thread) {
            error = "completed guest thread context disappeared";
            return;
        }
        thread->exit_code = current_guest_thread_exit_code;
        if (handle == 0) {
            pe32_entry_point_complete = true;
        }
        thread->completed = true;
        thread->suspend_count = 0;
        thread->runnable = false;
        thread->waiting = false;
        save_execution_state(*thread);
        wake_guest_waiters(handle);
        guest_coroutine_active = false;
        if (swapcontext(&thread->coroutine, &scheduler_context) != 0) {
            error = "cannot return a completed guest thread to the scheduler";
        }
        std::abort();
    }

    void run_current_guest_coroutine() {
        const uint32_t handle = current_guest_thread_handle;
        GuestThread* thread = guest_execution_state(handle);
        if (!thread) {
            error = "guest coroutine has no thread record";
            std::abort();
        }
        guest_coroutine_active = true;
        thread->started = true;
        int result = -1;
        if (handle == 0) {
            result = dispatch(pe_image_entry_point);
        } else {
            result = dispatch(thread->start_address);
        }

        uint32_t returned_code = 0;
        if (result == 0 && !current_guest_thread_exit_requested &&
            !read_guest_u32("register", kX86EaxRegisterOffset,
                            returned_code)) {
            result = -1;
        }
        const bool exited = handle != 0 &&
                            current_guest_thread_exit_requested;
        if (result != 0 && !exited && error.empty()) {
            error = "guest thread routine failed";
        }
        if (result == 0 && !exited)
            current_guest_thread_exit_code = returned_code;
        thread->completed = true;
        complete_current_guest_thread();
    }

    void wake_guest_waiters(uint32_t handle) {
        auto wake = [&](uint32_t candidate, GuestThread& thread) {
            if (!thread.waiting || thread.wait_handle != handle) return;
            thread.waiting = false;
            thread.wait_result = 0;
            enqueue_guest_thread(candidate);
        };
        wake(0, main_guest_thread);
        for (auto& [candidate, thread] : guest_threads)
            wake(candidate, thread);
    }

    void wake_expired_guest_waiters() {
        const auto now = std::chrono::steady_clock::now();
        auto wake = [&](uint32_t handle, GuestThread& thread) {
            if (!thread.waiting ||
                thread.wait_deadline ==
                    std::chrono::steady_clock::time_point::max() ||
                now < thread.wait_deadline) {
                return;
            }
            thread.waiting = false;
            thread.wait_result = 0x00000102;
            enqueue_guest_thread(handle);
        };
        wake(0, main_guest_thread);
        for (auto& [handle, thread] : guest_threads) wake(handle, thread);
    }

    bool run_guest_scheduler(size_t max_slices, bool stop_when_entrypoint_done) {
        if (scheduler_context_active) {
            error = "guest scheduler cannot be entered recursively";
            return false;
        }
        GuestExecutionState host_state{};
        save_execution_state(host_state);
        const uint32_t host_handle = current_guest_thread_handle;
        const uint32_t host_thread_id = current_guest_thread_id;
        const std::string host_error = error;
        void* previous_scheduler = active_pcode_scheduler;
        active_pcode_scheduler = this;
        scheduler_context_active = true;
        pause_scheduler_after_yield = false;

        size_t slices = 0;
        while (slices < max_slices) {
            wake_expired_guest_waiters();
            if (stop_when_entrypoint_done && pe32_entry_point_complete) break;
            if (ready_guest_threads.empty()) break;

            const uint32_t handle = ready_guest_threads.front();
            ready_guest_threads.pop_front();
            GuestThread* thread = guest_execution_state(handle);
            if (!thread || thread->completed || thread->waiting) continue;
            if (thread->suspend_count != 0) {
                thread->runnable = false;
                continue;
            }
            thread->runnable = false;
            if (!initialize_guest_coroutine(handle)) break;
            load_execution_state(*thread, handle);
            guest_coroutine_active = true;
            if (swapcontext(&scheduler_context, &thread->coroutine) != 0) {
                error = "cannot schedule a guest thread coroutine";
                guest_coroutine_active = false;
                break;
            }
            guest_coroutine_active = false;
            ++slices;
            if (thread->close_pending && thread->completed && handle != 0) {
                release_guest_thread_blocks(*thread);
                guest_threads.erase(handle);
            }
            if (!error.empty() && error != host_error) break;
            if (pause_scheduler_after_yield) {
                pause_scheduler_after_yield = false;
                break;
            }
        }

        scheduler_context_active = false;
        active_pcode_scheduler = previous_scheduler;
        load_execution_state(host_state, host_handle);
        current_guest_thread_id = host_thread_id;
        guest_coroutine_active = false;
        return error.empty() || error == host_error;
    }

    bool prepare_guest_thread_context(uint32_t handle) {
        GuestThread* thread = guest_execution_state(handle);
        if (!thread) return false;
        if (thread->coroutine_initialized) return true;

        GuestExecutionState saved_state{};
        save_execution_state(saved_state);
        const uint32_t saved_handle = current_guest_thread_handle;
        const uint32_t saved_id = current_guest_thread_id;

        registers.fill(0);
        tls_values.clear();
        active_guest_functions.clear();
        call_depth = 0;
        indirect_jump_depth = 0;
        current_guest_thread_id = thread->id;
        current_guest_thread_handle = handle;
        current_guest_fiber = 0;
        current_guest_thread_exit_code = 259;
        current_guest_thread_exit_requested = false;
        guest_last_error = 0;

        const uint32_t stack_top = thread->stack.address +
                                   static_cast<uint32_t>(thread->stack.size);
        bool initialized = initialize_guest_thread_teb(*thread) &&
            write_guest_u32("register", kX86FsBaseRegisterOffset,
                            thread->teb.address) &&
            write_guest_u32("register", kX86EspRegisterOffset,
                            stack_top - 8) &&
            write_guest_u32("register", kX86EbpRegisterOffset, 0) &&
            write_guest_u32("ram", stack_top - 8, 0) &&
            write_guest_u32("ram", stack_top - 4, thread->parameter);
        constexpr std::array<uint8_t, 6> x87_environment = {
            0x7f, 0x03, 0x00, 0x00, 0xff, 0xff};
        initialized = initialized && write_guest(
            "register", kX86X87EnvironmentRegisterOffset,
            x87_environment.size(), x87_environment.data());
        if (initialized) save_execution_state(*thread);

        load_execution_state(saved_state, saved_handle);
        current_guest_thread_id = saved_id;
        if (!initialized || !initialize_guest_coroutine(handle)) return false;
        return true;
    }

    bool run_guest_thread_synchronously(uint32_t handle) {
        const auto found = guest_threads.find(handle);
        if (found == guest_threads.end()) return false;
        GuestThread& thread = found->second;
        if (thread.started || thread.completed) return true;
        thread.started = true;

        const auto saved_registers = registers;
        const uint32_t saved_thread_id = current_guest_thread_id;
        const uint32_t saved_thread_handle = current_guest_thread_handle;
        const uint32_t saved_fiber = current_guest_fiber;
        const uint32_t saved_exit_code = current_guest_thread_exit_code;
        const bool saved_exit_requested = current_guest_thread_exit_requested;
        const uint32_t saved_last_error = guest_last_error;
        const int32_t saved_priority = guest_thread_priority;
        const uint32_t saved_ideal_processor = guest_thread_ideal_processor;

        registers.fill(0);
        current_guest_thread_id = thread.id;
        current_guest_thread_handle = handle;
        current_guest_fiber = 0;
        current_guest_thread_exit_code = 259;
        current_guest_thread_exit_requested = false;
        guest_last_error = thread.last_error;
        guest_thread_priority = thread.priority;
        guest_thread_ideal_processor = thread.ideal_processor;

        const uint32_t stack_top = thread.stack.address +
                                   static_cast<uint32_t>(thread.stack.size);
        bool initialized = initialize_guest_thread_teb(thread) &&
            write_guest_u32("register", kX86FsBaseRegisterOffset,
                            thread.teb.address) &&
            write_guest_u32("register", kX86EspRegisterOffset,
                            stack_top - 8) &&
            write_guest_u32("register", kX86EbpRegisterOffset, 0) &&
            write_guest_u32("ram", stack_top - 8, 0) &&
            write_guest_u32("ram", stack_top - 4, thread.parameter);
        constexpr std::array<uint8_t, 6> x87_environment = {
            0x7f, 0x03, 0x00, 0x00, 0xff, 0xff};
        initialized = initialized && write_guest(
            "register", kX86X87EnvironmentRegisterOffset,
            x87_environment.size(), x87_environment.data());
        int result = -1;
        if (initialized) {
            result = dispatch(thread.start_address);
        } else if (error.empty()) {
            error = "cannot initialize guest thread context";
        }

        uint32_t returned_code = 0;
        const bool exited = current_guest_thread_exit_requested;
        if (result == 0 && !exited &&
            !read_guest_u32("register", kX86EaxRegisterOffset,
                            returned_code)) {
            result = -1;
        }
        thread.exit_code = exited
                               ? current_guest_thread_exit_code
                               : returned_code;
        thread.last_error = guest_last_error;
        thread.ideal_processor = guest_thread_ideal_processor;
        thread.completed = true;
        thread.suspend_count = 0;
        const bool close_pending = thread.close_pending;

        registers = saved_registers;
        current_guest_thread_id = saved_thread_id;
        current_guest_thread_handle = saved_thread_handle;
        current_guest_fiber = saved_fiber;
        current_guest_thread_exit_code = saved_exit_code;
        current_guest_thread_exit_requested = saved_exit_requested;
        guest_last_error = saved_last_error;
        guest_thread_priority = saved_priority;
        guest_thread_ideal_processor = saved_ideal_processor;
        if (close_pending) {
            release_guest_thread_blocks(thread);
            guest_threads.erase(handle);
        }
        return result == 0 ||
               (exited && result == kGuestThreadExitResult);
    }

    bool run_guest_thread(uint32_t handle) {
        if (!guest_coroutine_active) return run_guest_thread_synchronously(handle);
        GuestThread* thread = guest_execution_state(handle);
        if (!thread || thread->started || thread->completed) return thread != nullptr;
        if (!prepare_guest_thread_context(handle)) return false;
        enqueue_guest_thread(handle);
        return true;
    }

    int create_thread() {
        constexpr const char* api = "KERNEL32.dll!CreateThread";
        uint32_t security_attributes = 0;
        uint32_t stack_size = 0;
        uint32_t start_address = 0;
        uint32_t parameter = 0;
        uint32_t flags = 0;
        uint32_t thread_id_address = 0;
        if (!read_stack_argument(0, security_attributes, api) ||
            !read_stack_argument(1, stack_size, api) ||
            !read_stack_argument(2, start_address, api) ||
            !read_stack_argument(3, parameter, api) ||
            !read_stack_argument(4, flags, api) ||
            !read_stack_argument(5, thread_id_address, api)) {
            return -1;
        }
        (void)security_attributes;
        if (start_address == 0 || (flags & ~UINT32_C(0x00010004)) != 0 ||
            (thread_id_address != 0 &&
             !valid_guest_pointer(thread_id_address, sizeof(uint32_t)))) {
            guest_last_error = 87;
            return return_kernel32_dword(0, api, 24);
        }
        if (stack_size > kGuestMaximumThreadStackSize) {
            guest_last_error = 8;
            return return_kernel32_dword(0, api, 24);
        }
        if (next_guest_thread_handle >
                UINT32_MAX - kGuestThreadHandleStride ||
            next_guest_thread_id == UINT32_MAX) {
            guest_last_error = 8;
            return return_kernel32_dword(0, api, 24);
        }
        const size_t effective_stack_size = stack_size == 0
            ? kGuestDefaultThreadStackSize
            : std::max<uint32_t>(stack_size, 16 * 1024);
        uint32_t stack_address = 0;
        if (!allocate_guest_heap(kGuestProcessHeapHandle,
                                 effective_stack_size, stack_address)) {
            guest_last_error = 8;
            return return_kernel32_dword(0, api, 24);
        }
        uint32_t teb_address = 0;
        if (!allocate_guest_heap(kGuestProcessHeapHandle, kGuestTebSize,
                                 teb_address)) {
            const auto stack = heap_allocations.find(stack_address);
            if (stack != heap_allocations.end()) {
                free_heap_blocks.push_back(stack->second);
                heap_allocations.erase(stack);
            }
            guest_last_error = 8;
            return return_kernel32_dword(0, api, 24);
        }

        const uint32_t handle = next_guest_thread_handle;
        next_guest_thread_handle += kGuestThreadHandleStride;
        GuestThread thread{};
        thread.id = next_guest_thread_id++;
        thread.start_address = start_address;
        thread.parameter = parameter;
        thread.suspend_count = (flags & 0x4) != 0 ? 1 : 0;
        thread.stack = heap_allocations.at(stack_address);
        thread.teb = heap_allocations.at(teb_address);
        if (!initialize_guest_thread_teb(thread)) return -1;
        if (thread_id_address != 0 &&
            !write_guest_u32("ram", thread_id_address, thread.id)) {
            return -1;
        }
        const bool suspended = thread.suspend_count != 0;
        guest_threads.emplace(handle, std::move(thread));
        if (!suspended && !run_guest_thread(handle))
            return -1;
        return return_kernel32_dword(handle, api, 24);
    }

    int resume_thread() {
        constexpr const char* api = "KERNEL32.dll!ResumeThread";
        uint32_t handle = 0;
        if (!read_stack_argument(0, handle, api)) return -1;
        const auto thread = guest_threads.find(handle);
        if (thread == guest_threads.end()) {
            guest_last_error = 6;
            return return_kernel32_dword(UINT32_MAX, api, 4);
        }
        const uint32_t previous = thread->second.suspend_count;
        if (previous != 0) --thread->second.suspend_count;
        if (thread->second.suspend_count == 0 && !thread->second.completed) {
            if (!thread->second.started && !run_guest_thread(handle))
                return -1;
            if (thread->second.started && pe32_entry_point_started)
                enqueue_guest_thread(handle);
        }
        return return_kernel32_dword(previous, api, 4);
    }

    int suspend_thread() {
        constexpr const char* api = "KERNEL32.dll!SuspendThread";
        uint32_t handle = 0;
        if (!read_stack_argument(0, handle, api)) return -1;
        const auto thread = guest_threads.find(handle);
        if (thread == guest_threads.end() || thread->second.completed ||
            thread->second.suspend_count == UINT32_MAX) {
            guest_last_error = thread == guest_threads.end() ? 6 : 298;
            return return_kernel32_dword(UINT32_MAX, api, 4);
        }
        const uint32_t previous = thread->second.suspend_count++;
        return return_kernel32_dword(previous, api, 4);
    }

    int get_exit_code_thread() {
        constexpr const char* api = "KERNEL32.dll!GetExitCodeThread";
        uint32_t handle = 0;
        uint32_t exit_code_address = 0;
        if (!read_stack_argument(0, handle, api) ||
            !read_stack_argument(1, exit_code_address, api)) {
            return -1;
        }
        const auto thread = guest_threads.find(handle);
        if (thread == guest_threads.end()) {
            guest_last_error = 6;
            return return_kernel32_dword(0, api, 8);
        }
        if (!valid_guest_pointer(exit_code_address, sizeof(uint32_t)) ||
            !write_guest_u32("ram", exit_code_address,
                             thread->second.completed
                                 ? thread->second.exit_code
                                 : UINT32_C(259))) {
            guest_last_error = 87;
            return return_kernel32_dword(0, api, 8);
        }
        return return_kernel32_dword(1, api, 8);
    }

    int exit_thread() {
        constexpr const char* api = "KERNEL32.dll!ExitThread";
        uint32_t exit_code = 0;
        if (!read_stack_argument(0, exit_code, api)) return -1;
        if (!finish_stdcall(4, api)) return -1;
        if (current_guest_thread_handle != 0) {
            current_guest_thread_exit_code = exit_code;
            current_guest_thread_exit_requested = true;
            return kGuestThreadExitResult;
        }
        return 0;
    }

    int get_process_heap() {
        return return_kernel32_dword(kGuestProcessHeapHandle,
                                     "KERNEL32.dll!GetProcessHeap");
    }

    int create_mutex_a() {
        constexpr const char* api = "KERNEL32.dll!CreateMutexA";
        uint32_t security_attributes = 0;
        uint32_t initial_owner = 0;
        uint32_t name_address = 0;
        if (!read_stack_argument(0, security_attributes, api) ||
            !read_stack_argument(1, initial_owner, api) ||
            !read_stack_argument(2, name_address, api)) {
            return -1;
        }
        (void)security_attributes;

        std::string name;
        if (name_address != 0 && !read_guest_ascii(name_address, name, api))
            return -1;
        if (!name.empty()) {
            const auto existing = guest_named_mutexes.find(name);
            if (existing != guest_named_mutexes.end()) {
                guest_last_error = 183;
                return return_kernel32_dword(existing->second, api, 12);
            }
        }
        if (next_guest_mutex_handle >
            std::numeric_limits<uint32_t>::max() - sizeof(uint32_t)) {
            guest_last_error = 8;
            return return_kernel32_dword(0, api, 12);
        }
        const uint32_t handle =
            static_cast<uint32_t>(next_guest_mutex_handle);
        next_guest_mutex_handle += sizeof(uint32_t);
        guest_mutexes.emplace(
            handle, GuestMutex{initial_owner == 0 ? 0u : 1u});
        if (!name.empty()) guest_named_mutexes.emplace(std::move(name), handle);
        return return_kernel32_dword(handle, api, 12);
    }

    int wait_for_single_object() {
        constexpr const char* api = "KERNEL32.dll!WaitForSingleObject";
        uint32_t handle = 0;
        uint32_t timeout_ms = 0;
        if (!read_stack_argument(0, handle, api) ||
            !read_stack_argument(1, timeout_ms, api)) {
            return -1;
        }
        return return_kernel32_dword(
            wait_guest_object(handle, timeout_ms, api), api, 8);
    }

    int wait_for_single_object_ex() {
        constexpr const char* api = "KERNEL32.dll!WaitForSingleObjectEx";
        uint32_t handle = 0;
        uint32_t timeout_ms = 0;
        uint32_t alertable = 0;
        if (!read_stack_argument(0, handle, api) ||
            !read_stack_argument(1, timeout_ms, api) ||
            !read_stack_argument(2, alertable, api)) {
            return -1;
        }
        if (alertable != 0) {
            guest_last_error = 50;
            return return_kernel32_dword(UINT32_MAX, api, 12);
        }
        return return_kernel32_dword(
            wait_guest_object(handle, timeout_ms, api), api, 12);
    }

    uint32_t wait_guest_object(uint32_t handle, uint32_t timeout_ms,
                               const char* api) {
        const auto thread = guest_threads.find(handle);
        if (thread != guest_threads.end()) {
            if (thread->second.completed) return 0;
            if (guest_coroutine_active && scheduler_context_active &&
                timeout_ms != 0) {
                const uint32_t waiter_handle = current_guest_thread_handle;
                GuestThread* waiter =
                    guest_execution_state(waiter_handle);
                if (!waiter) {
                    error = std::string(api) +
                            " has no current guest thread state";
                    return UINT32_MAX;
                }
                waiter->waiting = true;
                waiter->runnable = false;
                waiter->wait_handle = handle;
                waiter->wait_result = 0x00000102;
                waiter->wait_deadline = timeout_ms == UINT32_MAX
                    ? std::chrono::steady_clock::time_point::max()
                    : std::chrono::steady_clock::now() +
                          std::chrono::milliseconds(timeout_ms);
                if (!yield_current_guest_thread(false)) return UINT32_MAX;
                const GuestThread* resumed_waiter =
                    guest_execution_state(waiter_handle);
                if (!resumed_waiter) return UINT32_MAX;
                return resumed_waiter->wait_result;
            }
            return 0x00000102;
        }
        const auto mutex = guest_mutexes.find(handle);
        if (mutex != guest_mutexes.end()) {
            if (mutex->second.recursion_count == UINT32_MAX) {
                guest_last_error = 298;
                return UINT32_MAX;
            }
            ++mutex->second.recursion_count;
            return 0;
        }
        const auto event = guest_events.find(handle);
        if (event != guest_events.end()) {
            if (event->second.signaled) {
                if (!event->second.manual_reset) event->second.signaled = false;
                return 0;
            }
            if (timeout_ms == UINT32_MAX) {
                guest_last_error = 50;
                return UINT32_MAX;
            }
            return 0x00000102;
        }
        guest_last_error = 6;
        (void)api;
        return UINT32_MAX;
    }

    int create_event(bool wide) {
        const char* api = wide ? "KERNEL32.dll!CreateEventW"
                               : "KERNEL32.dll!CreateEventA";
        uint32_t security_attributes = 0;
        uint32_t manual_reset = 0;
        uint32_t initial_state = 0;
        uint32_t name_address = 0;
        if (!read_stack_argument(0, security_attributes, api) ||
            !read_stack_argument(1, manual_reset, api) ||
            !read_stack_argument(2, initial_state, api) ||
            !read_stack_argument(3, name_address, api)) {
            return -1;
        }
        (void)security_attributes;
        if (name_address != 0) {
            guest_last_error = 50;
            return return_kernel32_dword(0, api, 16);
        }
        if (next_guest_event_handle >
            std::numeric_limits<uint32_t>::max() - sizeof(uint32_t)) {
            guest_last_error = 8;
            return return_kernel32_dword(0, api, 16);
        }
        const uint32_t handle = static_cast<uint32_t>(next_guest_event_handle);
        next_guest_event_handle += sizeof(uint32_t);
        guest_events.emplace(
            handle, GuestEvent{manual_reset != 0, initial_state != 0});
        return return_kernel32_dword(handle, api, 16);
    }

    int set_event(bool signaled) {
        const char* api = signaled ? "KERNEL32.dll!SetEvent"
                                   : "KERNEL32.dll!ResetEvent";
        uint32_t handle = 0;
        if (!read_stack_argument(0, handle, api)) return -1;
        const auto event = guest_events.find(handle);
        if (event == guest_events.end()) {
            guest_last_error = 6;
            return return_kernel32_dword(0, api, 4);
        }
        event->second.signaled = signaled;
        return return_kernel32_dword(1, api, 4);
    }

    int release_mutex() {
        constexpr const char* api = "KERNEL32.dll!ReleaseMutex";
        uint32_t handle = 0;
        if (!read_stack_argument(0, handle, api)) return -1;
        const auto mutex = guest_mutexes.find(handle);
        if (mutex == guest_mutexes.end()) {
            guest_last_error = 6;
            return return_kernel32_dword(0, api, 4);
        }
        if (mutex->second.recursion_count == 0) {
            guest_last_error = 288;
            return return_kernel32_dword(0, api, 4);
        }
        --mutex->second.recursion_count;
        return return_kernel32_dword(1, api, 4);
    }

    int close_handle() {
        constexpr const char* api = "KERNEL32.dll!CloseHandle";
        uint32_t handle = 0;
        if (!read_stack_argument(0, handle, api)) return -1;
        const auto file = guest_files.find(handle);
        if (file != guest_files.end()) {
            const int descriptor = file->second.descriptor;
            guest_files.erase(file);
            if (::close(descriptor) != 0) {
                guest_last_error = 6;
                return return_kernel32_dword(0, api, 4);
            }
            return return_kernel32_dword(1, api, 4);
        }
        const auto thread = guest_threads.find(handle);
        if (thread != guest_threads.end()) {
            if (!thread->second.completed) {
                thread->second.close_pending = true;
            } else {
                release_guest_thread_blocks(thread->second);
                guest_threads.erase(thread);
            }
            return return_kernel32_dword(1, api, 4);
        }
        const auto event = guest_events.find(handle);
        if (event != guest_events.end()) {
            guest_events.erase(event);
            return return_kernel32_dword(1, api, 4);
        }
        if (guest_mutexes.erase(handle) == 0) {
            guest_last_error = 6;
            return return_kernel32_dword(0, api, 4);
        }
        for (auto name = guest_named_mutexes.begin();
             name != guest_named_mutexes.end();) {
            if (name->second == handle) {
                name = guest_named_mutexes.erase(name);
            } else {
                ++name;
            }
        }
        return return_kernel32_dword(1, api, 4);
    }

    bool resolve_guest_file_path(const std::string& path,
                                 std::filesystem::path& resolved,
                                 const char* api) {
        std::string portable_path = path;
        std::replace(portable_path.begin(), portable_path.end(), '\\', '/');
        const std::filesystem::path guest_path(portable_path);
        if (guest_path.empty() || guest_path.is_absolute() ||
            guest_path.has_root_name()) {
            guest_last_error = 5;
            return false;
        }
        for (const auto& component : guest_path) {
            if (component == "..") {
                guest_last_error = 5;
                return false;
            }
        }
        std::error_code error_code;
        const std::filesystem::path current_directory =
            std::filesystem::current_path(error_code);
        if (error_code) {
            guest_last_error = 5;
            return false;
        }
        const std::filesystem::path root =
            std::filesystem::canonical(current_directory, error_code);
        if (error_code) {
            guest_last_error = 5;
            return false;
        }
        resolved = std::filesystem::canonical(root / guest_path, error_code);
        if (error_code) {
            guest_last_error =
                error_code == std::errc::no_such_file_or_directory ? 2 : 5;
            return false;
        }
        const std::filesystem::path relative = resolved.lexically_relative(root);
        if (relative.empty() || *relative.begin() == "..") {
            guest_last_error = 5;
            return false;
        }
        (void)api;
        return true;
    }

    int create_file_a() {
        constexpr const char* api = "KERNEL32.dll!CreateFileA";
        uint32_t path_address = 0;
        uint32_t desired_access = 0;
        uint32_t share_mode = 0;
        uint32_t security_attributes = 0;
        uint32_t creation_disposition = 0;
        uint32_t flags_and_attributes = 0;
        uint32_t template_file = 0;
        if (!read_stack_argument(0, path_address, api) ||
            !read_stack_argument(1, desired_access, api) ||
            !read_stack_argument(2, share_mode, api) ||
            !read_stack_argument(3, security_attributes, api) ||
            !read_stack_argument(4, creation_disposition, api) ||
            !read_stack_argument(5, flags_and_attributes, api) ||
            !read_stack_argument(6, template_file, api)) {
            return -1;
        }
        (void)share_mode;
        (void)flags_and_attributes;
        if (path_address == 0 || desired_access != 0x80000000 ||
            security_attributes != 0 || creation_disposition != 3 ||
            template_file != 0) {
            guest_last_error = 87;
            return return_kernel32_dword(UINT32_MAX, api, 28);
        }
        std::string guest_path;
        if (!read_guest_ascii(path_address, guest_path, api)) return -1;
        std::filesystem::path host_path;
        if (!resolve_guest_file_path(guest_path, host_path, api))
            return return_kernel32_dword(UINT32_MAX, api, 28);
        const int descriptor = ::open(host_path.c_str(), O_RDONLY | O_CLOEXEC);
        if (descriptor < 0) {
            guest_last_error = errno == ENOENT ? 2 : errno == EACCES ? 5 : 31;
            return return_kernel32_dword(UINT32_MAX, api, 28);
        }
        struct stat file_status {};
        if (::fstat(descriptor, &file_status) != 0 ||
            !S_ISREG(file_status.st_mode) || file_status.st_size < 0) {
            (void)::close(descriptor);
            guest_last_error = 5;
            return return_kernel32_dword(UINT32_MAX, api, 28);
        }
        if (next_guest_file_handle >
            std::numeric_limits<uint32_t>::max() - sizeof(uint32_t)) {
            (void)::close(descriptor);
            guest_last_error = 8;
            return return_kernel32_dword(UINT32_MAX, api, 28);
        }
        const uint32_t handle = static_cast<uint32_t>(next_guest_file_handle);
        next_guest_file_handle += sizeof(uint32_t);
        guest_files.emplace(handle,
                            GuestFile{descriptor,
                                      static_cast<uint64_t>(file_status.st_size)});
        guest_last_error = 0;
        return return_kernel32_dword(handle, api, 28);
    }

    int get_file_size() {
        constexpr const char* api = "KERNEL32.dll!GetFileSize";
        uint32_t handle = 0;
        uint32_t high_part_address = 0;
        if (!read_stack_argument(0, handle, api) ||
            !read_stack_argument(1, high_part_address, api)) {
            return -1;
        }
        const auto file = guest_files.find(handle);
        if (file == guest_files.end()) {
            guest_last_error = 6;
            return return_kernel32_dword(UINT32_MAX, api, 8);
        }
        if (high_part_address != 0 &&
            !write_guest_u32("ram", high_part_address,
                             static_cast<uint32_t>(file->second.size >> 32))) {
            error = std::string(api) + " cannot write the high-size output";
            return -1;
        }
        return return_kernel32_dword(static_cast<uint32_t>(file->second.size),
                                     api, 8);
    }

    int read_file() {
        constexpr const char* api = "KERNEL32.dll!ReadFile";
        uint32_t handle = 0;
        uint32_t output_address = 0;
        uint32_t bytes_to_read = 0;
        uint32_t bytes_read_address = 0;
        uint32_t overlapped = 0;
        if (!read_stack_argument(0, handle, api) ||
            !read_stack_argument(1, output_address, api) ||
            !read_stack_argument(2, bytes_to_read, api) ||
            !read_stack_argument(3, bytes_read_address, api) ||
            !read_stack_argument(4, overlapped, api)) {
            return -1;
        }
        const auto file = guest_files.find(handle);
        if (file == guest_files.end()) {
            guest_last_error = 6;
            return return_kernel32_dword(0, api, 20);
        }
        if (overlapped != 0 || bytes_read_address == 0 ||
            bytes_to_read > kMaximumGuestFileReadBytes ||
            (bytes_to_read != 0 && output_address == 0)) {
            guest_last_error = 87;
            return return_kernel32_dword(0, api, 20);
        }
        std::vector<uint8_t> bytes(bytes_to_read);
        size_t total_read = 0;
        while (total_read < bytes.size()) {
            const ssize_t result = ::read(
                file->second.descriptor, bytes.data() + total_read,
                bytes.size() - total_read);
            if (result < 0 && errno == EINTR) continue;
            if (result < 0) {
                guest_last_error = 31;
                return return_kernel32_dword(0, api, 20);
            }
            if (result == 0) break;
            total_read += static_cast<size_t>(result);
        }
        if (total_read != 0 &&
            !write_guest_bytes(output_address, bytes.data(), total_read, api))
            return -1;
        if (!write_guest_u32("ram", bytes_read_address,
                             static_cast<uint32_t>(total_read))) {
            error = std::string(api) + " cannot write the byte-count output";
            return -1;
        }
        return return_kernel32_dword(1, api, 20);
    }

    int set_unhandled_exception_filter() {
        constexpr const char* api =
            "KERNEL32.dll!SetUnhandledExceptionFilter";
        uint32_t filter = 0;
        if (!read_stack_argument(0, filter, api)) return -1;
        const uint32_t previous_filter = guest_unhandled_exception_filter;
        guest_unhandled_exception_filter = filter;
        return return_kernel32_dword(previous_filter, api, 4);
    }

    int get_module_handle_a() {
        constexpr const char* api = "KERNEL32.dll!GetModuleHandleA";
        uint32_t name_address = 0;
        if (!read_stack_argument(0, name_address, api)) return -1;
        uint32_t handle = pe_image_base;
        if (name_address != 0) {
            std::string module_name;
            if (!read_guest_ascii(name_address, module_name, api)) return -1;
            const auto module = guest_module_handles.find(
                lowercase_ascii(std::move(module_name)));
            handle = module == guest_module_handles.end() ? 0 : module->second;
        }
        if (!write_guest_u32("register", kX86EaxRegisterOffset, handle)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(4, api) ? 0 : -1;
    }

    int get_module_file_name_a() {
        constexpr const char* api = "KERNEL32.dll!GetModuleFileNameA";
        uint32_t module_handle = 0;
        uint32_t output_address = 0;
        uint32_t output_size = 0;
        if (!read_stack_argument(0, module_handle, api) ||
            !read_stack_argument(1, output_address, api) ||
            !read_stack_argument(2, output_size, api)) {
            return -1;
        }
        if (module_handle != 0 && module_handle != pe_image_base) {
            guest_last_error = 126;
            return return_kernel32_dword(0, api, 12) ? 0 : -1;
        }
        if (output_size == 0) return return_kernel32_dword(0, api, 12);

        const size_t copied_size = std::min<size_t>(
            pe_image_file_name.size(), output_size);
        if (copied_size != 0 &&
            !write_guest_bytes(output_address,
                               reinterpret_cast<const uint8_t*>(
                                   pe_image_file_name.data()),
                               copied_size, api)) {
            return -1;
        }
        if (pe_image_file_name.size() < output_size) {
            const uint8_t terminator = 0;
            if (!write_guest_bytes(output_address + copied_size, &terminator,
                                   sizeof(terminator), api)) {
                return -1;
            }
        }
        return return_kernel32_dword(static_cast<uint32_t>(copied_size), api,
                                     12);
    }

    int get_proc_address() {
        constexpr const char* api = "KERNEL32.dll!GetProcAddress";
        uint32_t module_handle = 0;
        uint32_t procedure = 0;
        if (!read_stack_argument(0, module_handle, api) ||
            !read_stack_argument(1, procedure, api)) {
            return -1;
        }
        uint32_t procedure_address = 0;
        const auto module = guest_module_names.find(module_handle);
        if (module != guest_module_names.end()) {
            std::string symbol;
            if (procedure <= 0xffff) {
                symbol = "#" + std::to_string(procedure);
            } else if (!read_guest_ascii(procedure, symbol, api)) {
                return -1;
            }
            for (const auto& trap : import_traps) {
                const size_t separator = trap.second.find('!');
                if (separator == std::string::npos) continue;
                if (lowercase_ascii(trap.second.substr(0, separator)) ==
                        module->second &&
                    trap.second.substr(separator + 1) == symbol) {
                    procedure_address = trap.first;
                    break;
                }
            }
            if (procedure_address == 0 &&
                module->second == "kernel32.dll" &&
                is_supported_kernel32_api(symbol)) {
                const std::string imported_name =
                    "KERNEL32.dll!" + symbol;
                if (!allocate_dynamic_import_stub(imported_name,
                                                  procedure_address)) {
                    error = std::string(api) +
                            " has no address range for a dynamic import trap";
                    return -1;
                }
            }
        }
        if (!write_guest_u32("register", kX86EaxRegisterOffset,
                             procedure_address)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(8, api) ? 0 : -1;
    }

    int tls_alloc() {
        constexpr const char* api = "KERNEL32.dll!TlsAlloc";
        uint32_t index = UINT32_MAX;
        if (!free_tls_indices.empty()) {
            index = free_tls_indices.back();
            free_tls_indices.pop_back();
        } else if (next_tls_index < kMaximumGuestTlsSlots) {
            index = next_tls_index++;
        }
        if (index != UINT32_MAX) allocated_tls_indices.emplace(index);
        return return_kernel32_dword(index, api);
    }

    int tls_get_value() {
        constexpr const char* api = "KERNEL32.dll!TlsGetValue";
        uint32_t index = 0;
        if (!read_stack_argument(0, index, api)) return -1;
        const auto value = allocated_tls_indices.find(index) ==
                                   allocated_tls_indices.end()
                               ? tls_values.end()
                               : tls_values.find(index);
        return return_kernel32_dword(
            value == tls_values.end() ? 0 : value->second, api, 4);
    }

    int tls_set_value() {
        constexpr const char* api = "KERNEL32.dll!TlsSetValue";
        uint32_t index = 0;
        uint32_t value = 0;
        if (!read_stack_argument(0, index, api) ||
            !read_stack_argument(1, value, api)) {
            return -1;
        }
        const bool allocated = allocated_tls_indices.find(index) !=
                               allocated_tls_indices.end();
        if (allocated) {
            if (value != 0)
                tls_values[index] = value;
            else
                tls_values.erase(index);
        }
        if (!write_guest_u32("register", kX86EaxRegisterOffset,
                             allocated ? 1 : 0)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(8, api) ? 0 : -1;
    }

    int tls_free() {
        constexpr const char* api = "KERNEL32.dll!TlsFree";
        uint32_t index = 0;
        if (!read_stack_argument(0, index, api)) return -1;
        const auto allocated = allocated_tls_indices.find(index);
        const bool success = allocated != allocated_tls_indices.end();
        if (success) {
            allocated_tls_indices.erase(allocated);
            tls_values.erase(index);
            free_tls_indices.push_back(index);
        }
        if (!write_guest_u32("register", kX86EaxRegisterOffset,
                             success ? 1 : 0)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(4, api) ? 0 : -1;
    }

    bool write_critical_section(uint32_t address,
                                const GuestCriticalSection& section,
                                const char* api) {
        const long host_thread_id = syscall(SYS_gettid);
        if (host_thread_id < 0) {
            error = std::string(api) + " could not identify the guest thread";
            return false;
        }
        const uint32_t fields[] = {
            0,
            section.recursion_count == 0
                ? UINT32_MAX : section.recursion_count - 1,
            section.recursion_count,
            section.recursion_count == 0
                ? 0 : static_cast<uint32_t>(host_thread_id),
            0,
            section.spin_count};
        for (size_t index = 0; index < std::size(fields); ++index) {
            if (!write_guest_u32("ram", static_cast<uint64_t>(address) +
                                            index * 4,
                                 fields[index])) {
                error = std::string(api) + " cannot write CRITICAL_SECTION";
                return false;
            }
        }
        return true;
    }

    int initialize_critical_section_and_spin_count() {
        constexpr const char* api =
            "KERNEL32.dll!InitializeCriticalSectionAndSpinCount";
        uint32_t address = 0;
        uint32_t spin_count = 0;
        if (!read_stack_argument(0, address, api) ||
            !read_stack_argument(1, spin_count, api)) {
            return -1;
        }
        if (!valid_guest_pointer(address, 24)) {
            error = std::string(api) + " has an invalid output pointer";
            return -1;
        }
        GuestCriticalSection section;
        section.spin_count = spin_count;
        if (!write_critical_section(address, section, api)) return -1;
        critical_sections[address] = section;
        if (!write_guest_u32("register", kX86EaxRegisterOffset, 1)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(8, api) ? 0 : -1;
    }

    int interlocked_increment() {
        constexpr const char* api = "KERNEL32.dll!InterlockedIncrement";
        uint32_t address = 0;
        if (!read_stack_argument(0, address, api)) return -1;
        if (!valid_guest_pointer(address, sizeof(uint32_t))) {
            error = std::string(api) + " has an invalid operand pointer";
            return -1;
        }
        uint32_t value = 0;
        if (!read_guest_u32("ram", address, value)) {
            error = std::string(api) + " cannot read its operand";
            return -1;
        }
        ++value;
        if (!write_guest_u32("ram", address, value) ||
            !write_guest_u32("register", kX86EaxRegisterOffset, value)) {
            error = std::string(api) + " cannot write its result";
            return -1;
        }
        return finish_stdcall(4, api) ? 0 : -1;
    }

    int interlocked_decrement() {
        constexpr const char* api = "KERNEL32.dll!InterlockedDecrement";
        uint32_t address = 0;
        if (!read_stack_argument(0, address, api)) return -1;
        if (!valid_guest_pointer(address, sizeof(uint32_t))) {
            error = std::string(api) + " has an invalid operand pointer";
            return -1;
        }
        uint32_t value = 0;
        if (!read_guest_u32("ram", address, value)) {
            error = std::string(api) + " cannot read its operand";
            return -1;
        }
        --value;
        if (!write_guest_u32("ram", address, value) ||
            !write_guest_u32("register", kX86EaxRegisterOffset, value)) {
            error = std::string(api) + " cannot write its result";
            return -1;
        }
        return finish_stdcall(4, api) ? 0 : -1;
    }

    int interlocked_compare_exchange() {
        constexpr const char* api =
            "KERNEL32.dll!InterlockedCompareExchange";
        uint32_t address = 0;
        uint32_t exchange = 0;
        uint32_t comparand = 0;
        if (!read_stack_argument(0, address, api) ||
            !read_stack_argument(1, exchange, api) ||
            !read_stack_argument(2, comparand, api)) {
            return -1;
        }
        if (!valid_guest_pointer(address, sizeof(uint32_t))) {
            error = std::string(api) + " has an invalid operand pointer";
            return -1;
        }
        uint32_t previous = 0;
        if (!read_guest_u32("ram", address, previous) ||
            (previous == comparand &&
             !write_guest_u32("ram", address, exchange)) ||
            !write_guest_u32("register", kX86EaxRegisterOffset, previous)) {
            error = std::string(api) + " cannot update its operand";
            return -1;
        }
        return finish_stdcall(12, api) ? 0 : -1;
    }

    int interlocked_exchange() {
        constexpr const char* api = "KERNEL32.dll!InterlockedExchange";
        uint32_t address = 0;
        uint32_t exchange = 0;
        if (!read_stack_argument(0, address, api) ||
            !read_stack_argument(1, exchange, api)) {
            return -1;
        }
        if (!valid_guest_pointer(address, sizeof(uint32_t))) {
            error = std::string(api) + " has an invalid operand pointer";
            return -1;
        }
        uint32_t previous = 0;
        if (!read_guest_u32("ram", address, previous) ||
            !write_guest_u32("ram", address, exchange) ||
            !write_guest_u32("register", kX86EaxRegisterOffset, previous)) {
            error = std::string(api) + " cannot update its operand";
            return -1;
        }
        return finish_stdcall(2 * sizeof(uint32_t), api) ? 0 : -1;
    }

    int initialize_critical_section() {
        constexpr const char* api = "KERNEL32.dll!InitializeCriticalSection";
        uint32_t address = 0;
        if (!read_stack_argument(0, address, api)) return -1;
        if (!valid_guest_pointer(address, 24)) {
            error = std::string(api) + " has an invalid output pointer";
            return -1;
        }
        const GuestCriticalSection section{};
        if (!write_critical_section(address, section, api)) return -1;
        critical_sections[address] = section;
        return finish_stdcall(4, api) ? 0 : -1;
    }

    int enter_critical_section(bool try_only) {
        const char* api = try_only
            ? "KERNEL32.dll!TryEnterCriticalSection"
            : "KERNEL32.dll!EnterCriticalSection";
        uint32_t address = 0;
        if (!read_stack_argument(0, address, api)) return -1;
        const auto found = critical_sections.find(address);
        if (found == critical_sections.end()) {
            error = std::string(api) + " received an uninitialized object";
            return -1;
        }
        if (found->second.recursion_count == UINT32_MAX) {
            error = std::string(api) + " recursion count overflowed";
            return -1;
        }
        ++found->second.recursion_count;
        if (!write_critical_section(address, found->second, api)) return -1;
        if (try_only &&
            !write_guest_u32("register", kX86EaxRegisterOffset, 1)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(4, api) ? 0 : -1;
    }

    int leave_critical_section() {
        constexpr const char* api = "KERNEL32.dll!LeaveCriticalSection";
        uint32_t address = 0;
        if (!read_stack_argument(0, address, api)) return -1;
        const auto found = critical_sections.find(address);
        if (found == critical_sections.end() ||
            found->second.recursion_count == 0) {
            error = std::string(api) + " received an unowned object";
            return -1;
        }
        --found->second.recursion_count;
        return write_critical_section(address, found->second, api) &&
                       finish_stdcall(4, api)
                   ? 0 : -1;
    }

    int delete_critical_section() {
        constexpr const char* api = "KERNEL32.dll!DeleteCriticalSection";
        uint32_t address = 0;
        if (!read_stack_argument(0, address, api)) return -1;
        const auto found = critical_sections.find(address);
        if (found == critical_sections.end()) {
            error = std::string(api) + " received an uninitialized object";
            return -1;
        }
        critical_sections.erase(found);
        std::array<uint8_t, 24> zeroes{};
        for (size_t offset = 0; offset < zeroes.size();
             offset += kMaximumPcodeValueSize) {
            const size_t size = std::min(kMaximumPcodeValueSize,
                                         zeroes.size() - offset);
            if (!write_guest("ram", static_cast<uint64_t>(address) + offset,
                             size, zeroes.data() + offset)) {
                error = std::string(api) + " cannot clear CRITICAL_SECTION";
                return -1;
            }
        }
        return finish_stdcall(4, api) ? 0 : -1;
    }

    int set_critical_section_spin_count() {
        constexpr const char* api = "KERNEL32.dll!SetCriticalSectionSpinCount";
        uint32_t address = 0;
        uint32_t spin_count = 0;
        if (!read_stack_argument(0, address, api) ||
            !read_stack_argument(1, spin_count, api)) {
            return -1;
        }
        const auto found = critical_sections.find(address);
        if (found == critical_sections.end()) {
            error = std::string(api) + " received an uninitialized object";
            return -1;
        }
        const uint32_t previous_spin_count = found->second.spin_count;
        found->second.spin_count = spin_count;
        if (!write_critical_section(address, found->second, api) ||
            !write_guest_u32("register", kX86EaxRegisterOffset,
                             previous_spin_count)) {
            error = std::string(api) + " cannot write its result";
            return -1;
        }
        return finish_stdcall(8, api) ? 0 : -1;
    }

    int get_std_handle() {
        constexpr const char* api = "KERNEL32.dll!GetStdHandle";
        uint32_t standard_stream = 0;
        if (!read_stack_argument(0, standard_stream, api)) return -1;
        uint32_t handle = 0;
        if (standard_stream == static_cast<uint32_t>(-10))
            handle = kGuestStdInputHandle;
        else if (standard_stream == static_cast<uint32_t>(-11))
            handle = kGuestStdOutputHandle;
        else if (standard_stream == static_cast<uint32_t>(-12))
            handle = kGuestStdErrorHandle;
        if (!write_guest_u32("register", kX86EaxRegisterOffset, handle)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(4, api) ? 0 : -1;
    }

    int get_file_type() {
        constexpr const char* api = "KERNEL32.dll!GetFileType";
        uint32_t handle = 0;
        if (!read_stack_argument(0, handle, api)) return -1;
        uint32_t type = 0;
        if (handle == kGuestStdInputHandle ||
            handle == kGuestStdOutputHandle ||
            handle == kGuestStdErrorHandle) {
            type = 2;  // FILE_TYPE_CHAR for the synthetic console streams.
        }
        if (!write_guest_u32("register", kX86EaxRegisterOffset, type)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(4, api) ? 0 : -1;
    }

    int set_handle_count() {
        constexpr const char* api = "KERNEL32.dll!SetHandleCount";
        uint32_t count = 0;
        if (!read_stack_argument(0, count, api)) return -1;
        if (!write_guest_u32("register", kX86EaxRegisterOffset, count)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(4, api) ? 0 : -1;
    }

    int get_command_line_a() {
        constexpr const char* api = "KERNEL32.dll!GetCommandLineA";
        static constexpr char command_line[] = "SHIFT.exe";
        if (!command_line_initialized) {
            if (!write_guest("ram", kGuestCommandLineAddress,
                             sizeof(command_line),
                             reinterpret_cast<const uint8_t*>(command_line))) {
                error = std::string(api) + " cannot initialize command line";
                return -1;
            }
            command_line_initialized = true;
        }
        if (!write_guest_u32("register", kX86EaxRegisterOffset,
                             kGuestCommandLineAddress)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(0, api) ? 0 : -1;
    }

    int get_environment_strings(bool wide) {
        const char* api = wide ? "KERNEL32.dll!GetEnvironmentStringsW"
                               : "KERNEL32.dll!GetEnvironmentStringsA";
        if (!guest_environment_variables.empty()) {
            std::vector<std::pair<std::string, std::string>> variables;
            variables.reserve(guest_environment_variables.size());
            for (const auto& [key, value] : guest_environment_variables) {
                (void)key;
                variables.push_back(value);
            }
            std::sort(variables.begin(), variables.end(),
                      [](const auto& left, const auto& right) {
                          return lowercase_ascii(left.first) <
                                 lowercase_ascii(right.first);
                      });
            std::vector<uint8_t> bytes;
            for (const auto& [name, value] : variables) {
                const std::string entry = name + "=" + value;
                if (wide) {
                    for (const unsigned char byte : entry) {
                        const uint16_t character = decode_windows_1252(byte);
                        bytes.push_back(static_cast<uint8_t>(character));
                        bytes.push_back(static_cast<uint8_t>(character >> 8));
                    }
                    bytes.insert(bytes.end(), {0, 0});
                } else {
                    bytes.insert(bytes.end(), entry.begin(), entry.end());
                    bytes.push_back(0);
                }
            }
            bytes.insert(bytes.end(), wide ? std::initializer_list<uint8_t>{0, 0}
                                           : std::initializer_list<uint8_t>{0});
            uint32_t address = 0;
            if (!allocate_guest_heap(kGuestProcessHeapHandle, bytes.size(),
                                     address) ||
                !write_guest_bytes(address, bytes.data(), bytes.size(), api)) {
                error = std::string(api) + " cannot create an environment block";
                return -1;
            }
            guest_environment_blocks.emplace(address);
            if (!write_guest_u32("register", kX86EaxRegisterOffset,
                                 address)) {
                error = std::string(api) + " cannot write EAX";
                return -1;
            }
            return finish_stdcall(0, api) ? 0 : -1;
        }
        const uint32_t address = wide ? kGuestEnvironmentWideAddress
                                      : kGuestEnvironmentAnsiAddress;
        if (!environment_initialized) {
            constexpr std::array<uint8_t, 2> empty_ansi = {0, 0};
            constexpr std::array<uint8_t, 4> empty_wide = {0, 0, 0, 0};
            if (!write_guest("ram", kGuestEnvironmentAnsiAddress,
                             empty_ansi.size(), empty_ansi.data()) ||
                !write_guest("ram", kGuestEnvironmentWideAddress,
                             empty_wide.size(), empty_wide.data())) {
                error = std::string(api) + " cannot initialize environment block";
                return -1;
            }
            environment_initialized = true;
        }
        if (!write_guest_u32("register", kX86EaxRegisterOffset, address)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(0, api) ? 0 : -1;
    }

    int free_environment_strings(bool wide) {
        const char* api = wide ? "KERNEL32.dll!FreeEnvironmentStringsW"
                               : "KERNEL32.dll!FreeEnvironmentStringsA";
        uint32_t address = 0;
        if (!read_stack_argument(0, address, api)) return -1;
        const uint32_t expected = wide ? kGuestEnvironmentWideAddress
                                       : kGuestEnvironmentAnsiAddress;
        uint32_t result = 0;
        if (address == expected) {
            result = 1;
        } else if (guest_environment_blocks.erase(address) != 0) {
            const auto allocation = heap_allocations.find(address);
            if (allocation != heap_allocations.end()) {
                free_heap_blocks.push_back(allocation->second);
                heap_allocations.erase(allocation);
                result = 1;
            }
        }
        if (!write_guest_u32("register", kX86EaxRegisterOffset,
                             result)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(4, api) ? 0 : -1;
    }

    int get_environment_variable_a() {
        constexpr const char* api = "KERNEL32.dll!GetEnvironmentVariableA";
        uint32_t name_address = 0;
        uint32_t output_address = 0;
        uint32_t output_size = 0;
        if (!read_stack_argument(0, name_address, api) ||
            !read_stack_argument(1, output_address, api) ||
            !read_stack_argument(2, output_size, api)) {
            return -1;
        }
        (void)output_address;
        (void)output_size;
        std::string name;
        if (name_address == 0 || !read_guest_ascii(name_address, name, api))
            return -1;
        const auto variable =
            guest_environment_variables.find(lowercase_ascii(name));
        if (variable == guest_environment_variables.end()) {
            guest_last_error = 203;
            return return_kernel32_dword(0, api, 12);
        }
        const std::string& value = variable->second.second;
        const uint32_t required_size = static_cast<uint32_t>(value.size() + 1);
        if (output_size < required_size) {
            guest_last_error = 122;
            return return_kernel32_dword(required_size, api, 12);
        }
        if (output_address == 0 ||
            !write_guest_bytes(output_address,
                               reinterpret_cast<const uint8_t*>(value.c_str()),
                               required_size, api)) {
            return -1;
        }
        return return_kernel32_dword(static_cast<uint32_t>(value.size()), api,
                                     12);
    }

    int set_environment_variable_a() {
        constexpr const char* api = "KERNEL32.dll!SetEnvironmentVariableA";
        uint32_t name_address = 0;
        uint32_t value_address = 0;
        if (!read_stack_argument(0, name_address, api) ||
            !read_stack_argument(1, value_address, api)) {
            return -1;
        }
        std::string name;
        if (name_address == 0 || !read_guest_ascii(name_address, name, api))
            return -1;
        if (name.empty() || name.find('=') != std::string::npos) {
            guest_last_error = 87;
            return return_kernel32_dword(0, api, 8);
        }
        const std::string key = lowercase_ascii(name);
        if (value_address == 0) {
            guest_environment_variables.erase(key);
        } else {
            std::string value;
            if (!read_guest_ascii(value_address, value, api)) return -1;
            guest_environment_variables[key] = {std::move(name),
                                                std::move(value)};
        }
        return return_kernel32_dword(1, api, 8);
    }

    int multi_byte_to_wide_char() {
        constexpr const char* api = "KERNEL32.dll!MultiByteToWideChar";
        std::array<uint32_t, 6> arguments{};
        for (uint32_t index = 0; index < arguments.size(); ++index) {
            if (!read_stack_argument(index, arguments[index], api)) return -1;
        }
        const uint32_t code_page = arguments[0];
        const uint32_t flags = arguments[1];
        const uint32_t source = arguments[2];
        const uint32_t source_count = arguments[3];
        const uint32_t destination = arguments[4];
        const uint32_t destination_count = arguments[5];
        if ((code_page != 0 && code_page != kWindowsAnsiCodePage) ||
            (flags != 0 && flags != 1) || source == 0) {
            error = std::string(api) +
                    " only supports the configured Windows-1252 profile";
            return -1;
        }

        std::vector<uint8_t> input;
        if (source_count == UINT32_MAX) {
            input.reserve(256);
            for (size_t index = 0; index < kMaximumWin32TextUnits; ++index) {
                uint8_t byte = 0;
                if (!read_guest("ram", static_cast<uint64_t>(source) + index,
                                1, &byte)) {
                    error = std::string(api) + " has an invalid input string";
                    return -1;
                }
                input.push_back(byte);
                if (byte == 0) break;
            }
            if (input.empty() || input.back() != 0) {
                error = std::string(api) + " input string is not terminated";
                return -1;
            }
        } else {
            if (source_count == 0 ||
                source_count > kMaximumWin32TextUnits) {
                error = std::string(api) + " has an unsupported input length";
                return -1;
            }
            input.resize(source_count);
            if (!read_guest_bytes(source, input.data(), input.size(), api))
                return -1;
        }

        const size_t output_count = input.size();
        if (destination == 0 && destination_count != 0) {
            error = std::string(api) + " has an invalid output buffer";
            return -1;
        }
        if (destination != 0 && destination_count != 0) {
            if (destination_count < output_count) {
                guest_last_error = 122;
                if (!write_guest_u32("register", kX86EaxRegisterOffset, 0)) {
                    error = std::string(api) + " cannot write EAX";
                    return -1;
                }
                return finish_stdcall(24, api) ? 0 : -1;
            }
            std::vector<uint8_t> output(output_count * sizeof(uint16_t));
            for (size_t index = 0; index < input.size(); ++index) {
                const uint16_t character = decode_windows_1252(input[index]);
                output[index * 2] = static_cast<uint8_t>(character);
                output[index * 2 + 1] = static_cast<uint8_t>(character >> 8);
            }
            if (!write_guest_bytes(destination, output.data(), output.size(),
                                   api)) {
                return -1;
            }
        }
        if (!write_guest_u32("register", kX86EaxRegisterOffset,
                             static_cast<uint32_t>(output_count))) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(24, api) ? 0 : -1;
    }

    int wide_char_to_multi_byte() {
        constexpr const char* api = "KERNEL32.dll!WideCharToMultiByte";
        std::array<uint32_t, 8> arguments{};
        for (uint32_t index = 0; index < arguments.size(); ++index) {
            if (!read_stack_argument(index, arguments[index], api)) return -1;
        }
        const uint32_t code_page = arguments[0];
        const uint32_t flags = arguments[1];
        const uint32_t source = arguments[2];
        const uint32_t source_count = arguments[3];
        const uint32_t destination = arguments[4];
        const uint32_t destination_size = arguments[5];
        if ((code_page != 0 && code_page != kWindowsAnsiCodePage) ||
            flags != 0 || source == 0) {
            error = std::string(api) +
                    " only supports the configured Windows-1252 profile";
            return -1;
        }

        std::vector<uint8_t> input;
        if (source_count == UINT32_MAX) {
            input.reserve(256);
            for (size_t index = 0; index < kMaximumWin32TextUnits; ++index) {
                std::array<uint8_t, 2> character{};
                if (!read_guest("ram", static_cast<uint64_t>(source) +
                                           index * character.size(),
                                character.size(), character.data())) {
                    error = std::string(api) + " has an invalid input string";
                    return -1;
                }
                input.insert(input.end(), character.begin(), character.end());
                if (character == std::array<uint8_t, 2>{0, 0}) break;
            }
            if (input.empty() || input[input.size() - 1] != 0 ||
                input[input.size() - 2] != 0) {
                error = std::string(api) + " input string is not terminated";
                return -1;
            }
        } else {
            if (source_count == 0 ||
                source_count > kMaximumWin32TextUnits) {
                error = std::string(api) + " has an unsupported input length";
                return -1;
            }
            input.resize(static_cast<size_t>(source_count) * 2);
            if (!read_guest_bytes(source, input.data(), input.size(), api))
                return -1;
        }

        uint8_t default_character = '?';
        if (arguments[6] != 0 &&
            !read_guest("ram", arguments[6], 1, &default_character)) {
            error = std::string(api) + " has an invalid default character";
            return -1;
        }
        std::vector<uint8_t> output;
        output.reserve(input.size() / 2);
        bool used_default = false;
        for (size_t index = 0; index + 1 < input.size(); index += 2) {
            const uint16_t character = static_cast<uint16_t>(input[index]) |
                (static_cast<uint16_t>(input[index + 1]) << 8);
            uint8_t byte = 0;
            if (!encode_windows_1252(character, byte)) {
                byte = default_character;
                used_default = true;
                if (character >= 0xd800 && character <= 0xdbff &&
                    index + 3 < input.size()) {
                    const uint16_t next =
                        static_cast<uint16_t>(input[index + 2]) |
                        (static_cast<uint16_t>(input[index + 3]) << 8);
                    if (next >= 0xdc00 && next <= 0xdfff) index += 2;
                }
            }
            output.push_back(byte);
        }

        if (destination == 0 && destination_size != 0) {
            error = std::string(api) + " has an invalid output buffer";
            return -1;
        }
        if (destination != 0 && destination_size != 0) {
            if (destination_size < output.size()) {
                guest_last_error = 122;
                if (!write_guest_u32("register", kX86EaxRegisterOffset, 0)) {
                    error = std::string(api) + " cannot write EAX";
                    return -1;
                }
                return finish_stdcall(32, api) ? 0 : -1;
            }
            if (!write_guest_bytes(destination, output.data(), output.size(),
                                   api)) {
                return -1;
            }
            if (arguments[7] != 0 &&
                !write_guest_u32("ram", arguments[7],
                                 used_default ? 1 : 0)) {
                error = std::string(api) + " has an invalid used-default pointer";
                return -1;
            }
        }
        if (!write_guest_u32("register", kX86EaxRegisterOffset,
                             static_cast<uint32_t>(output.size()))) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(32, api) ? 0 : -1;
    }

    int get_last_error() {
        constexpr const char* api = "KERNEL32.dll!GetLastError";
        if (!write_guest_u32("register", kX86EaxRegisterOffset,
                             guest_last_error)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(0, api) ? 0 : -1;
    }

    int set_last_error() {
        constexpr const char* api = "KERNEL32.dll!SetLastError";
        if (!read_stack_argument(0, guest_last_error, api)) return -1;
        return finish_stdcall(4, api) ? 0 : -1;
    }

    int raise_exception() {
        constexpr const char* api = "KERNEL32.dll!RaiseException";
        uint32_t code = 0;
        uint32_t flags = 0;
        uint32_t argument_count = 0;
        uint32_t arguments_address = 0;
        if (!read_stack_argument(0, code, api) ||
            !read_stack_argument(1, flags, api) ||
            !read_stack_argument(2, argument_count, api) ||
            !read_stack_argument(3, arguments_address, api)) {
            return -1;
        }
        if (code != UINT32_C(0x406d1388) || flags != 0 ||
            argument_count != 4) {
            error = std::string(api) +
                    " only supports the MSVC thread-name exception";
            return -1;
        }
        if (!valid_guest_pointer(arguments_address, 4 * sizeof(uint32_t))) {
            error = std::string(api) +
                    " has an invalid thread-name information pointer";
            return -1;
        }
        std::array<uint8_t, 4 * sizeof(uint32_t)> information{};
        if (!read_guest("ram", arguments_address, information.size(),
                        information.data())) {
            error = std::string(api) +
                    " cannot read thread-name information";
            return -1;
        }
        const auto word = [&](size_t offset) {
            return static_cast<uint32_t>(information[offset]) |
                   (static_cast<uint32_t>(information[offset + 1]) << 8) |
                   (static_cast<uint32_t>(information[offset + 2]) << 16) |
                   (static_cast<uint32_t>(information[offset + 3]) << 24);
        };
        const uint32_t type = word(0);
        const uint32_t name_address = word(4);
        const uint32_t info_flags = word(12);
        if (type != UINT32_C(0x1000) || name_address == 0 || info_flags != 0) {
            error = std::string(api) +
                    " received invalid MSVC thread-name information";
            return -1;
        }
        std::string thread_name;
        if (!read_guest_ascii(name_address, thread_name, api)) return -1;
        if (thread_name.empty()) {
            error = std::string(api) + " received an empty thread name";
            return -1;
        }
        return return_kernel32_dword(0, api, 4 * sizeof(uint32_t));
    }

    int get_ansi_code_page() {
        return return_kernel32_dword(kWindowsAnsiCodePage,
                                     "KERNEL32.dll!GetACP");
    }

    int is_valid_code_page() {
        constexpr const char* api = "KERNEL32.dll!IsValidCodePage";
        uint32_t code_page = 0;
        if (!read_stack_argument(0, code_page, api)) return -1;
        if (!write_guest_u32("register", kX86EaxRegisterOffset,
                             code_page == kWindowsAnsiCodePage ? 1 : 0)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(4, api) ? 0 : -1;
    }

    int get_code_page_info() {
        constexpr const char* api = "KERNEL32.dll!GetCPInfo";
        uint32_t code_page = 0;
        uint32_t output_address = 0;
        if (!read_stack_argument(0, code_page, api) ||
            !read_stack_argument(1, output_address, api)) {
            return -1;
        }
        if (code_page == kWindowsAnsiCodePage &&
            !valid_guest_pointer(output_address, 20)) {
            error = std::string(api) + " has an invalid CPINFO pointer";
            return -1;
        }
        if (code_page != kWindowsAnsiCodePage) {
            if (!write_guest_u32("register", kX86EaxRegisterOffset, 0)) {
                error = std::string(api) + " cannot write EAX";
                return -1;
            }
            return finish_stdcall(8, api) ? 0 : -1;
        }
        std::array<uint8_t, 20> info{};
        info[0] = 1;
        info[4] = '?';
        for (size_t offset = 0; offset < info.size();
             offset += kMaximumPcodeValueSize) {
            const size_t size = std::min(kMaximumPcodeValueSize,
                                         info.size() - offset);
            if (!write_guest("ram", static_cast<uint64_t>(output_address) +
                                        offset,
                             size, info.data() + offset)) {
                error = std::string(api) + " cannot write CPINFO";
                return -1;
            }
        }
        if (!write_guest_u32("register", kX86EaxRegisterOffset, 1)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(8, api) ? 0 : -1;
    }

    int get_string_type_w() {
        constexpr const char* api = "KERNEL32.dll!GetStringTypeW";
        uint32_t info_type = 0;
        uint32_t source = 0;
        uint32_t character_count = 0;
        uint32_t output_address = 0;
        if (!read_stack_argument(0, info_type, api) ||
            !read_stack_argument(1, source, api) ||
            !read_stack_argument(2, character_count, api) ||
            !read_stack_argument(3, output_address, api)) {
            return -1;
        }
        if (info_type != 1 || source == 0 || output_address == 0) {
            error = std::string(api) +
                    " only supports CT_CTYPE1 with guest buffers";
            return -1;
        }
        std::vector<uint8_t> input;
        if (character_count == UINT32_MAX) {
            input.reserve(64);
            for (size_t index = 0; index < kMaximumWin32TextUnits; ++index) {
                std::array<uint8_t, 2> character{};
                if (!read_guest("ram", static_cast<uint64_t>(source) +
                                           index * character.size(),
                                character.size(), character.data())) {
                    error = std::string(api) + " has an invalid input string";
                    return -1;
                }
                input.insert(input.end(), character.begin(), character.end());
                if (character == std::array<uint8_t, 2>{0, 0}) break;
            }
            if (input.empty() || input[input.size() - 1] != 0 ||
                input[input.size() - 2] != 0) {
                error = std::string(api) + " input string is not terminated";
                return -1;
            }
        } else {
            if (character_count == 0 ||
                character_count > kMaximumWin32TextUnits) {
                error = std::string(api) + " has an unsupported input length";
                return -1;
            }
            input.resize(static_cast<size_t>(character_count) * 2);
            if (!read_guest_bytes(source, input.data(), input.size(), api))
                return -1;
        }
        std::vector<uint8_t> output(input.size());
        for (size_t index = 0; index + 1 < input.size(); index += 2) {
            const uint16_t character = static_cast<uint16_t>(input[index]) |
                (static_cast<uint16_t>(input[index + 1]) << 8);
            const uint16_t type = classify_windows_ctype1(character);
            output[index] = static_cast<uint8_t>(type);
            output[index + 1] = static_cast<uint8_t>(type >> 8);
        }
        if (!write_guest_bytes(output_address, output.data(), output.size(),
                               api) ||
            !write_guest_u32("register", kX86EaxRegisterOffset, 1)) {
            if (error.empty()) error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(16, api) ? 0 : -1;
    }

    int locale_map_string_w() {
        constexpr const char* api = "KERNEL32.dll!LCMapStringW";
        std::array<uint32_t, 6> arguments{};
        for (uint32_t index = 0; index < arguments.size(); ++index) {
            if (!read_stack_argument(index, arguments[index], api)) return -1;
        }
        const uint32_t locale = arguments[0];
        const uint32_t map_flags = arguments[1];
        const uint32_t source = arguments[2];
        const uint32_t source_count = arguments[3];
        const uint32_t destination = arguments[4];
        const uint32_t destination_count = arguments[5];
        if ((locale != 0 && locale != 0x007f && locale != 0x0409) ||
            (map_flags != 0x100 && map_flags != 0x200) || source == 0) {
            error = std::string(api) +
                    " only supports Windows-1252 lowercase and uppercase mapping";
            return -1;
        }

        std::vector<uint8_t> input;
        if (source_count == UINT32_MAX) {
            input.reserve(64);
            for (size_t index = 0; index < kMaximumWin32TextUnits; ++index) {
                std::array<uint8_t, 2> character{};
                if (!read_guest("ram", static_cast<uint64_t>(source) +
                                           index * character.size(),
                                character.size(), character.data())) {
                    error = std::string(api) + " has an invalid input string";
                    return -1;
                }
                input.insert(input.end(), character.begin(), character.end());
                if (character == std::array<uint8_t, 2>{0, 0}) break;
            }
            if (input.empty() || input[input.size() - 1] != 0 ||
                input[input.size() - 2] != 0) {
                error = std::string(api) + " input string is not terminated";
                return -1;
            }
        } else {
            if (source_count == 0 ||
                source_count > kMaximumWin32TextUnits) {
                error = std::string(api) + " has an unsupported input length";
                return -1;
            }
            input.resize(static_cast<size_t>(source_count) * 2);
            if (!read_guest_bytes(source, input.data(), input.size(), api))
                return -1;
        }

        std::vector<uint8_t> output(input.size());
        for (size_t index = 0; index + 1 < input.size(); index += 2) {
            const uint16_t character = static_cast<uint16_t>(input[index]) |
                (static_cast<uint16_t>(input[index + 1]) << 8);
            const uint16_t mapped = map_windows_1252_case(
                character, map_flags == 0x100);
            output[index] = static_cast<uint8_t>(mapped);
            output[index + 1] = static_cast<uint8_t>(mapped >> 8);
        }

        if (destination == 0 && destination_count != 0) {
            error = std::string(api) + " has an invalid output buffer";
            return -1;
        }
        if (destination != 0 && destination_count != 0) {
            if (destination_count < output.size() / 2) {
                guest_last_error = 122;
                if (!write_guest_u32("register", kX86EaxRegisterOffset, 0)) {
                    error = std::string(api) + " cannot write EAX";
                    return -1;
                }
                return finish_stdcall(24, api) ? 0 : -1;
            }
            if (!write_guest_bytes(destination, output.data(), output.size(),
                                   api)) {
                return -1;
            }
        }
        if (!write_guest_u32("register", kX86EaxRegisterOffset,
                             static_cast<uint32_t>(output.size() / 2))) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(24, api) ? 0 : -1;
    }

    int heap_create() {
        constexpr const char* api = "KERNEL32.dll!HeapCreate";
        uint32_t flags = 0;
        uint32_t initial_size = 0;
        uint32_t maximum_size = 0;
        if (!read_stack_argument(0, flags, api) ||
            !read_stack_argument(1, initial_size, api) ||
            !read_stack_argument(2, maximum_size, api)) {
            return -1;
        }
        if ((flags & ~UINT32_C(0x00040005)) != 0 ||
            (maximum_size != 0 && initial_size > maximum_size)) {
            error = std::string(api) + " received unsupported options or sizes";
            return -1;
        }
        if (next_guest_heap_handle >
            std::numeric_limits<uint32_t>::max() - sizeof(uint32_t)) {
            error = std::string(api) + " exhausted guest heap handles";
            return -1;
        }
        const uint32_t heap = static_cast<uint32_t>(next_guest_heap_handle);
        next_guest_heap_handle += sizeof(uint32_t);
        guest_heap_handles.emplace(heap);
        if (!write_guest_u32("register", kX86EaxRegisterOffset, heap)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(12, api) ? 0 : -1;
    }

    bool allocate_guest_heap(uint32_t heap, size_t requested_size,
                             uint32_t& address) {
        const uint64_t minimum_size = std::max<size_t>(requested_size, 1);
        const uint64_t allocation_size = (minimum_size + 15) & ~UINT64_C(15);
        for (auto free_block = free_heap_blocks.begin();
             free_block != free_heap_blocks.end(); ++free_block) {
            if (free_block->heap != heap ||
                free_block->size < allocation_size) continue;
            const uint32_t block_address = free_block->address;
            const size_t block_size = free_block->size;
            free_heap_blocks.erase(free_block);
            if (block_size > allocation_size) {
                free_heap_blocks.push_back({
                    static_cast<uint32_t>(block_address + allocation_size),
                    block_size - static_cast<size_t>(allocation_size), heap});
            }
            address = block_address;
            heap_allocations.emplace(address, GuestHeapBlock{
                address, static_cast<size_t>(allocation_size), heap,
                requested_size});
            return true;
        }
        uint64_t candidate =
            (static_cast<uint64_t>(guest_heap_next_address) + 15) &
            ~UINT64_C(15);
        while (candidate + allocation_size <= kGuestRamSize) {
            if (pe_image_size != 0) {
                const uint64_t image_begin = pe_image_base;
                const uint64_t image_end = image_begin + pe_image_size;
                if (candidate < image_end && image_begin <
                                                 candidate + allocation_size) {
                    candidate = (image_end + 15) & ~UINT64_C(15);
                    continue;
                }
            }
            bool moved_past_import_stub = false;
            for (const auto& trap : import_traps) {
                const uint64_t trap_begin = trap.first;
                const uint64_t trap_end = trap_begin + kImportStubStride;
                if (candidate < trap_end && trap_begin <
                                                candidate + allocation_size) {
                    candidate = (trap_end + 15) & ~UINT64_C(15);
                    moved_past_import_stub = true;
                    break;
                }
            }
            if (moved_past_import_stub) continue;
            bool moved_past_virtual_region = false;
            for (const auto& region : guest_virtual_allocations) {
                const uint64_t region_begin = region.first;
                const uint64_t region_end = region_begin + region.second;
                if (candidate < region_end &&
                    region_begin < candidate + allocation_size) {
                    candidate = (region_end + 15) & ~UINT64_C(15);
                    moved_past_virtual_region = true;
                    break;
                }
            }
            if (moved_past_virtual_region) continue;
            address = static_cast<uint32_t>(candidate);
            guest_heap_next_address = candidate + allocation_size;
            heap_allocations.emplace(address, GuestHeapBlock{
                address, static_cast<size_t>(allocation_size), heap,
                requested_size});
            return true;
        }
        return false;
    }

    int virtual_alloc() {
        constexpr const char* api = "KERNEL32.dll!VirtualAlloc";
        uint32_t requested_address = 0;
        uint32_t size = 0;
        uint32_t allocation_type = 0;
        uint32_t protection = 0;
        if (!read_stack_argument(0, requested_address, api) ||
            !read_stack_argument(1, size, api) ||
            !read_stack_argument(2, allocation_type, api) ||
            !read_stack_argument(3, protection, api)) {
            return -1;
        }
        if (size == 0 || protection == 0 ||
            (allocation_type & ~UINT32_C(0x3000)) != 0 ||
            allocation_type == 0) {
            guest_last_error = 87;
            return return_kernel32_dword(0, api, 16);
        }
        if (size > kMaximumGuestVirtualAllocationSize) {
            guest_last_error = 8;
            return return_kernel32_dword(0, api, 16);
        }

        const uint64_t allocation_size =
            (static_cast<uint64_t>(size) + 0xfff) & ~UINT64_C(0xfff);
        uint64_t candidate = requested_address == 0
            ? (guest_virtual_next_address + 0xffff) & ~UINT64_C(0xffff)
            : static_cast<uint64_t>(requested_address) & ~UINT64_C(0xffff);
        const auto overlaps = [&](uint64_t begin, uint64_t end) {
            if (pe_image_size != 0 && begin <
                    static_cast<uint64_t>(pe_image_base) + pe_image_size &&
                pe_image_base < end) {
                return true;
            }
            for (const auto& block : heap_allocations) {
                const uint64_t block_begin = block.first;
                const uint64_t block_end =
                    block_begin + block.second.size;
                if (begin < block_end && block_begin < end) return true;
            }
            for (const auto& block : free_heap_blocks) {
                const uint64_t block_begin = block.address;
                const uint64_t block_end = block_begin + block.size;
                if (begin < block_end && block_begin < end) return true;
            }
            for (const auto& region : guest_virtual_allocations) {
                const uint64_t region_begin = region.first;
                const uint64_t region_end = region_begin + region.second;
                if (begin < region_end && region_begin < end) return true;
            }
            for (const auto& trap : import_traps) {
                const uint64_t trap_begin = trap.first;
                const uint64_t trap_end = trap_begin + kImportStubStride;
                if (begin < trap_end && trap_begin < end) return true;
            }
            return false;
        };
        while (candidate + allocation_size <= kGuestRamSize &&
               overlaps(candidate, candidate + allocation_size)) {
            candidate = (candidate + allocation_size + 0xffff) &
                        ~UINT64_C(0xffff);
            if (requested_address != 0) break;
        }
        if (candidate + allocation_size > kGuestRamSize ||
            overlaps(candidate, candidate + allocation_size)) {
            guest_last_error = 8;
            return return_kernel32_dword(0, api, 16);
        }
        const uint32_t address = static_cast<uint32_t>(candidate);
        guest_virtual_allocations.emplace(address, allocation_size);
        if (requested_address == 0)
            guest_virtual_next_address = candidate + allocation_size;
        std::memset(static_cast<uint8_t*>(ram) + address, 0,
                    static_cast<size_t>(allocation_size));
        return return_kernel32_dword(address, api, 16);
    }

    int virtual_free() {
        constexpr const char* api = "KERNEL32.dll!VirtualFree";
        uint32_t address = 0;
        uint32_t size = 0;
        uint32_t free_type = 0;
        if (!read_stack_argument(0, address, api) ||
            !read_stack_argument(1, size, api) ||
            !read_stack_argument(2, free_type, api)) {
            return -1;
        }
        const auto region = guest_virtual_allocations.find(address);
        if (free_type != 0x8000 || size != 0 ||
            region == guest_virtual_allocations.end()) {
            guest_last_error = 87;
            return return_kernel32_dword(0, api, 12);
        }
        guest_virtual_allocations.erase(region);
        return return_kernel32_dword(1, api, 12);
    }

    int heap_alloc() {
        constexpr const char* api = "KERNEL32.dll!HeapAlloc";
        uint32_t heap = 0;
        uint32_t flags = 0;
        uint32_t size = 0;
        if (!read_stack_argument(0, heap, api) ||
            !read_stack_argument(1, flags, api) ||
            !read_stack_argument(2, size, api)) {
            return -1;
        }
        if (guest_heap_handles.find(heap) == guest_heap_handles.end()) {
            error = std::string(api) + " received an unknown guest heap handle";
            return -1;
        }
        if ((flags & ~UINT32_C(0x0d)) != 0) {
            error = std::string(api) + " received unsupported flags";
            return -1;
        }
        uint32_t address = 0;
        if (!allocate_guest_heap(heap, size, address)) {
            if (!write_guest_u32("register", kX86EaxRegisterOffset, 0)) {
                error = std::string(api) + " cannot write EAX";
                return -1;
            }
            return finish_stdcall(12, api) ? 0 : -1;
        }
        if ((flags & 0x8) != 0 && size != 0)
            std::memset(static_cast<uint8_t*>(ram) + address, 0, size);
        if (!write_guest_u32("register", kX86EaxRegisterOffset, address)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(12, api) ? 0 : -1;
    }

    int heap_realloc() {
        constexpr const char* api = "KERNEL32.dll!HeapReAlloc";
        uint32_t heap = 0;
        uint32_t flags = 0;
        uint32_t address = 0;
        uint32_t size = 0;
        if (!read_stack_argument(0, heap, api) ||
            !read_stack_argument(1, flags, api) ||
            !read_stack_argument(2, address, api) ||
            !read_stack_argument(3, size, api)) {
            return -1;
        }
        if ((flags & ~UINT32_C(0x1d)) != 0 ||
            guest_heap_handles.find(heap) == guest_heap_handles.end()) {
            return return_kernel32_dword(0, api, 16);
        }
        auto allocation = heap_allocations.find(address);
        if (address == 0 || allocation == heap_allocations.end() ||
            allocation->second.heap != heap) {
            return return_kernel32_dword(0, api, 16);
        }

        const uint64_t requested_size = std::max<uint32_t>(size, 1);
        const uint64_t allocation_size = (requested_size + 15) & ~UINT64_C(15);
        if (allocation_size <= allocation->second.size) {
            if ((flags & 0x8) != 0 && size > allocation->second.requested_size) {
                std::memset(static_cast<uint8_t*>(ram) + address +
                                allocation->second.requested_size,
                            0, size - allocation->second.requested_size);
            }
            allocation->second.requested_size = size;
            return return_kernel32_dword(address, api, 16);
        }
        if ((flags & 0x10) != 0) {
            return return_kernel32_dword(0, api, 16);
        }

        uint32_t replacement = 0;
        if (!allocate_guest_heap(heap, size, replacement)) {
            return return_kernel32_dword(0, api, 16);
        }
        const size_t bytes_to_copy = std::min<size_t>(
            allocation->second.requested_size, size);
        if (bytes_to_copy != 0) {
            std::memcpy(static_cast<uint8_t*>(ram) + replacement,
                        static_cast<uint8_t*>(ram) + address, bytes_to_copy);
        }
        if ((flags & 0x8) != 0 && size > bytes_to_copy) {
            std::memset(static_cast<uint8_t*>(ram) + replacement +
                            bytes_to_copy,
                        0, size - bytes_to_copy);
        }
        free_heap_blocks.push_back(allocation->second);
        heap_allocations.erase(allocation);
        return return_kernel32_dword(replacement, api, 16);
    }

    int heap_size() {
        constexpr const char* api = "KERNEL32.dll!HeapSize";
        uint32_t heap = 0;
        uint32_t flags = 0;
        uint32_t address = 0;
        if (!read_stack_argument(0, heap, api) ||
            !read_stack_argument(1, flags, api) ||
            !read_stack_argument(2, address, api)) {
            return -1;
        }
        if ((flags & ~UINT32_C(1)) != 0) {
            guest_last_error = 87;
            return return_kernel32_dword(UINT32_MAX, api, 12);
        }
        if (guest_heap_handles.find(heap) == guest_heap_handles.end()) {
            guest_last_error = 6;
            return return_kernel32_dword(UINT32_MAX, api, 12);
        }
        const auto allocation = heap_allocations.find(address);
        if (allocation == heap_allocations.end() ||
            allocation->second.heap != heap) {
            guest_last_error = 87;
            return return_kernel32_dword(UINT32_MAX, api, 12);
        }
        return return_kernel32_dword(
            static_cast<uint32_t>(allocation->second.size), api, 12);
    }

    int heap_free() {
        constexpr const char* api = "KERNEL32.dll!HeapFree";
        uint32_t heap = 0;
        uint32_t flags = 0;
        uint32_t address = 0;
        if (!read_stack_argument(0, heap, api) ||
            !read_stack_argument(1, flags, api) ||
            !read_stack_argument(2, address, api)) {
            return -1;
        }
        if (guest_heap_handles.find(heap) == guest_heap_handles.end()) {
            error = std::string(api) + " received an unknown guest heap handle";
            return -1;
        }
        if ((flags & ~UINT32_C(1)) != 0) {
            error = std::string(api) + " received unsupported flags";
            return -1;
        }
        const auto allocation = heap_allocations.find(address);
        if (allocation == heap_allocations.end() ||
            allocation->second.heap != heap) {
            error = std::string(api) + " received an unallocated guest pointer";
            return -1;
        }
        free_heap_blocks.push_back(allocation->second);
        heap_allocations.erase(allocation);
        if (!write_guest_u32("register", kX86EaxRegisterOffset, 1)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(12, api) ? 0 : -1;
    }

    int get_version_ex_a() {
        constexpr const char* api = "KERNEL32.dll!GetVersionExA";
        uint32_t output_address = 0;
        if (!read_stack_argument(0, output_address, api)) return -1;
        if (!valid_guest_pointer(output_address, sizeof(uint32_t))) {
            error = std::string(api) + " has an invalid output pointer";
            return -1;
        }
        uint32_t structure_size = 0;
        if (!read_guest_u32("ram", output_address, structure_size)) {
            error = std::string(api) + " cannot read OSVERSIONINFOA size";
            return -1;
        }
        if (structure_size != kOsVersionInfoABytes &&
            structure_size != kOsVersionInfoExABytes) {
            error = std::string(api) + " received an invalid structure size";
            return -1;
        }
        if (!valid_guest_pointer(output_address, structure_size)) {
            error = std::string(api) + " has an invalid output pointer";
            return -1;
        }
        std::array<uint8_t, kOsVersionInfoExABytes> version{};
        const auto put_u32 = [&version](size_t offset, uint32_t value) {
            for (size_t index = 0; index < 4; ++index)
                version[offset + index] =
                    static_cast<uint8_t>(value >> (index * 8));
        };
        put_u32(0, structure_size);
        put_u32(4, 5);     // Windows XP
        put_u32(8, 1);
        put_u32(12, 2600);
        put_u32(16, 2);    // VER_PLATFORM_WIN32_NT
        constexpr char service_pack[] = "Service Pack 3";
        std::copy_n(service_pack, sizeof(service_pack), version.begin() + 20);
        if (structure_size == kOsVersionInfoExABytes) {
            version[148] = 3; // wServicePackMajor
            version[154] = 1; // VER_NT_WORKSTATION
        }
        for (size_t offset = 0; offset < structure_size;
             offset += kMaximumPcodeValueSize) {
            const size_t size = std::min(kMaximumPcodeValueSize,
                                         structure_size - offset);
            if (!write_guest("ram", static_cast<uint64_t>(output_address) +
                                        offset, size,
                             version.data() + offset)) {
                error = std::string(api) + " cannot write OSVERSIONINFOA";
                return -1;
            }
        }
        if (!write_guest_u32("register", kX86EaxRegisterOffset, 1)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(4, api) ? 0 : -1;
    }

    int get_current_thread_id() {
        if (current_guest_thread_id == 0) {
            const long thread_id = syscall(SYS_gettid);
            if (thread_id < 0) {
                error = "KERNEL32.dll!GetCurrentThreadId host syscall failed";
                return -1;
            }
            current_guest_thread_id = static_cast<uint32_t>(thread_id);
        }
        return return_kernel32_dword(current_guest_thread_id,
                                     "KERNEL32.dll!GetCurrentThreadId");
    }

    int get_tick_count() {
        return return_kernel32_dword(monotonic_tick_milliseconds(),
                                     "KERNEL32.dll!GetTickCount");
    }

    uint32_t monotonic_tick_milliseconds() const {
        const auto elapsed = std::chrono::duration_cast<
            std::chrono::milliseconds>(
                std::chrono::steady_clock::now().time_since_epoch()).count();
        return static_cast<uint32_t>(elapsed);
    }

    int write_performance_value(uint64_t value, const char* api) {
        uint32_t output_address = 0;
        if (!read_stack_argument(0, output_address, api)) return -1;
        if (!valid_guest_pointer(output_address, sizeof(value))) {
            error = std::string(api) + " has an invalid output pointer";
            return -1;
        }
        if (!write_guest_u64("ram", output_address, value)) {
            error = std::string(api) + " cannot write its output value";
            return -1;
        }
        if (!write_guest_u32("register", kX86EaxRegisterOffset, 1)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(4, api) ? 0 : -1;
    }

    int query_performance_counter() {
        const auto ticks = std::chrono::duration_cast<
            std::chrono::nanoseconds>(
                std::chrono::steady_clock::now().time_since_epoch()).count();
        return write_performance_value(static_cast<uint64_t>(ticks),
            "KERNEL32.dll!QueryPerformanceCounter");
    }

    int query_performance_frequency() {
        return write_performance_value(kWindowsPerformanceCounterFrequency,
            "KERNEL32.dll!QueryPerformanceFrequency");
    }

    int get_startup_info_a() {
        constexpr const char* api = "KERNEL32.dll!GetStartupInfoA";
        constexpr size_t startup_info_size = 68;
        uint32_t output_address = 0;
        if (!read_stack_argument(0, output_address, api)) return -1;
        if (!valid_guest_pointer(output_address, startup_info_size)) {
            error = std::string(api) + " has an invalid output pointer";
            return -1;
        }
        std::array<uint8_t, startup_info_size> startup_info{};
        startup_info[0] = static_cast<uint8_t>(startup_info_size);
        startup_info[1] = static_cast<uint8_t>(startup_info_size >> 8);
        startup_info[2] = static_cast<uint8_t>(startup_info_size >> 16);
        startup_info[3] = static_cast<uint8_t>(startup_info_size >> 24);
        for (size_t offset = 0; offset < startup_info.size();
             offset += kMaximumPcodeValueSize) {
            const size_t size = std::min(kMaximumPcodeValueSize,
                                         startup_info.size() - offset);
            if (!write_guest("ram", static_cast<uint64_t>(output_address) +
                                        offset, size,
                             startup_info.data() + offset)) {
                error = std::string(api) + " cannot write STARTUPINFOA";
                return -1;
            }
        }
        return finish_stdcall(4, api) ? 0 : -1;
    }

    int get_system_time_as_file_time() {
        constexpr const char* api =
            "KERNEL32.dll!GetSystemTimeAsFileTime";
        uint32_t output_address = 0;
        if (!read_stack_argument(0, output_address, api)) return -1;
        if (!valid_guest_pointer(output_address, sizeof(uint64_t))) {
            error = std::string(api) + " has an invalid output pointer";
            return -1;
        }
        using FileTimeDuration = std::chrono::duration<
            int64_t, std::ratio<1, kWindowsFileTimeTicksPerSecond>>;
        const auto unix_ticks = std::chrono::duration_cast<FileTimeDuration>(
            std::chrono::system_clock::now().time_since_epoch()).count();
        if (unix_ticks < 0) {
            error = std::string(api) + " host clock predates Unix epoch";
            return -1;
        }
        const uint64_t filetime = kWindowsFileTimeUnixEpoch +
                                  static_cast<uint64_t>(unix_ticks);
        if (!write_guest_u64("ram", output_address, filetime)) {
            error = std::string(api) + " cannot write FILETIME";
            return -1;
        }
        return finish_stdcall(4, api) ? 0 : -1;
    }

    Pe32ImageInfo load_pe32_image(const std::string& path) {
        if (pe_image_load_attempted) {
            throw std::runtime_error(
                "a PE32 image load has already been attempted");
        }
        pe_image_load_attempted = true;

        std::ifstream file(path, std::ios::binary | std::ios::ate);
        require_pe(static_cast<bool>(file), "cannot open image file");
        const std::streampos end = file.tellg();
        require_pe(end >= 0, "cannot determine image file size");
        const uint64_t file_size =
            static_cast<uint64_t>(static_cast<std::streamoff>(end));
        require_pe(file_size >= 64, "DOS header is truncated");

        std::array<uint8_t, 64> dos_header{};
        read_file_range(file, file_size, 0, dos_header.data(),
                        dos_header.size());
        require_pe(dos_header[0] == 'M' && dos_header[1] == 'Z',
                   "missing MZ signature");
        const uint32_t pe_offset =
            static_cast<uint32_t>(dos_header[0x3c]) |
            (static_cast<uint32_t>(dos_header[0x3d]) << 8) |
            (static_cast<uint32_t>(dos_header[0x3e]) << 16) |
            (static_cast<uint32_t>(dos_header[0x3f]) << 24);

        require_file_range(pe_offset, 24, file_size);
        std::array<uint8_t, 4> signature{};
        read_file_range(file, file_size, pe_offset, signature.data(),
                        signature.size());
        require_pe(signature == std::array<uint8_t, 4>{'P', 'E', 0, 0},
                   "missing PE signature");

        const uint64_t coff_offset = static_cast<uint64_t>(pe_offset) + 4;
        require_pe(read_u16(file, file_size, coff_offset) == kPeI386,
                   "expected machine type I386");
        const uint16_t section_count =
            read_u16(file, file_size, coff_offset + 2);
        const uint16_t optional_header_size =
            read_u16(file, file_size, coff_offset + 16);
        require_pe(section_count > 0 &&
                       section_count <= kMaximumPeSectionCount,
                   "section count is outside the supported range");
        require_pe(optional_header_size >= 64,
                   "optional header is truncated");

        const uint64_t optional_offset = coff_offset + 20;
        require_file_range(optional_offset, optional_header_size, file_size);
        require_pe(read_u16(file, file_size, optional_offset) == kPe32Magic,
                   "expected PE32 optional header");
        const uint32_t entry_rva =
            read_u32(file, file_size, optional_offset + 16);
        const uint32_t image_base =
            read_u32(file, file_size, optional_offset + 28);
        const uint32_t image_size =
            read_u32(file, file_size, optional_offset + 56);
        const uint32_t headers_size =
            read_u32(file, file_size, optional_offset + 60);
        uint32_t import_directory_rva = 0;
        uint32_t import_directory_size = 0;
        const uint32_t data_directory_count = optional_header_size >= 96
            ? read_u32(file, file_size, optional_offset + 92)
            : 0;
        if (data_directory_count > 1) {
            require_pe(optional_header_size >= 112,
                       "optional header truncates the import directory");
            import_directory_rva =
                read_u32(file, file_size, optional_offset + 104);
            import_directory_size =
                read_u32(file, file_size, optional_offset + 108);
        }
        require_pe(image_size != 0 &&
                       static_cast<uint64_t>(image_base) + image_size <=
                           kGuestRamSize,
                   "image does not fit in the x86-32 guest address space");
        require_pe(headers_size >= optional_offset + optional_header_size +
                                      static_cast<uint64_t>(section_count) *
                                          kPeSectionHeaderSize &&
                       headers_size <= image_size &&
                       headers_size <= file_size,
                   "headers size is inconsistent with the PE tables");
        require_pe(entry_rva == 0 || entry_rva < image_size,
                   "entry point is outside the image");
        require_pe((import_directory_rva == 0) ==
                       (import_directory_size == 0),
                   "import directory RVA and size disagree");
        if (import_directory_rva != 0) {
            require_pe(import_directory_size >=
                           2 * kPeImportDescriptorSize &&
                           static_cast<uint64_t>(import_directory_rva) +
                                   import_directory_size <=
                               image_size,
                       "import directory exceeds the PE image");
        }

        const uint64_t section_table_offset =
            optional_offset + optional_header_size;
        require_file_range(section_table_offset,
                           static_cast<uint64_t>(section_count) *
                               kPeSectionHeaderSize,
                           file_size);

        std::vector<PeSection> sections;
        sections.reserve(section_count);
        for (uint16_t index = 0; index < section_count; ++index) {
            const uint64_t section_offset = section_table_offset +
                static_cast<uint64_t>(index) * kPeSectionHeaderSize;
            PeSection section;
            section.virtual_size =
                read_u32(file, file_size, section_offset + 8);
            section.virtual_address =
                read_u32(file, file_size, section_offset + 12);
            section.raw_size =
                read_u32(file, file_size, section_offset + 16);
            section.raw_offset =
                read_u32(file, file_size, section_offset + 20);
            const uint64_t mapped_size = section.mapped_size();
            require_pe(section.virtual_address <= image_size &&
                           mapped_size <= image_size - section.virtual_address,
                       "section exceeds SizeOfImage");
            if (mapped_size != 0) {
                require_pe(section.virtual_address >= headers_size,
                           "section overlaps the mapped headers");
            }
            require_file_range(section.raw_offset, section.raw_size, file_size);
            sections.push_back(section);
        }

        std::vector<ImportedThunk> imported_thunks;
        std::vector<std::string> import_modules;
        std::unordered_set<uint32_t> imported_iat_slots;
        if (import_directory_rva != 0) {
            require_pe(import_directory_size % kPeImportDescriptorSize == 0,
                       "import directory size is not descriptor aligned");
            const size_t descriptor_count =
                import_directory_size / kPeImportDescriptorSize;
            require_pe(descriptor_count <= kMaximumImportDescriptors,
                       "import directory has too many descriptors");
            bool found_terminator = false;
            for (size_t descriptor_index = 0;
                 descriptor_index < descriptor_count; ++descriptor_index) {
                const uint64_t descriptor_rva =
                    static_cast<uint64_t>(import_directory_rva) +
                    descriptor_index * kPeImportDescriptorSize;
                require_pe(descriptor_rva <=
                               std::numeric_limits<uint32_t>::max(),
                           "import descriptor RVA overflows");
                const uint64_t descriptor_offset = file_offset_for_rva(
                    static_cast<uint32_t>(descriptor_rva),
                    kPeImportDescriptorSize, headers_size, sections);
                const uint32_t lookup_table_rva =
                    read_u32(file, file_size, descriptor_offset);
                const uint32_t timestamp =
                    read_u32(file, file_size, descriptor_offset + 4);
                const uint32_t forwarder_chain =
                    read_u32(file, file_size, descriptor_offset + 8);
                const uint32_t module_name_rva =
                    read_u32(file, file_size, descriptor_offset + 12);
                const uint32_t first_thunk_rva =
                    read_u32(file, file_size, descriptor_offset + 16);
                if (lookup_table_rva == 0 && timestamp == 0 &&
                    forwarder_chain == 0 && module_name_rva == 0 &&
                    first_thunk_rva == 0) {
                    found_terminator = true;
                    break;
                }
                require_pe(module_name_rva != 0 && first_thunk_rva != 0,
                           "import descriptor omits a name or IAT");
                const std::string module_name = read_import_name(
                    file, file_size, module_name_rva, headers_size, sections);
                if (std::find(import_modules.begin(), import_modules.end(),
                              module_name) == import_modules.end()) {
                    import_modules.push_back(module_name);
                }
                const uint32_t thunk_table_rva =
                    lookup_table_rva != 0 ? lookup_table_rva : first_thunk_rva;
                bool found_thunk_terminator = false;
                for (size_t thunk_index = 0;
                     thunk_index < kMaximumImportThunksPerModule;
                     ++thunk_index) {
                    const uint64_t thunk_rva =
                        static_cast<uint64_t>(thunk_table_rva) +
                        thunk_index * sizeof(uint32_t);
                    const uint64_t iat_rva =
                        static_cast<uint64_t>(first_thunk_rva) +
                        thunk_index * sizeof(uint32_t);
                    require_pe(thunk_rva <=
                                   std::numeric_limits<uint32_t>::max() &&
                                   thunk_rva + sizeof(uint32_t) <= image_size &&
                                   iat_rva <=
                                       std::numeric_limits<uint32_t>::max() &&
                                   iat_rva + sizeof(uint32_t) <= image_size,
                               "import thunk exceeds the PE image");
                    const uint32_t thunk_value = read_rva_u32(
                        file, file_size, static_cast<uint32_t>(thunk_rva),
                        headers_size, sections);
                    if (thunk_value == 0) {
                        found_thunk_terminator = true;
                        break;
                    }
                    require_pe(imported_thunks.size() <
                                   kMaximumImportFunctions,
                               "PE image has too many imported functions");
                    std::string function_name;
                    if ((thunk_value & 0x80000000u) != 0) {
                        require_pe((thunk_value & 0x7fff0000u) == 0,
                                   "ordinal import has reserved bits set");
                        function_name = "#" +
                            std::to_string(thunk_value & 0xffffu);
                    } else {
                        require_pe(static_cast<uint64_t>(thunk_value) + 2 <=
                                       image_size,
                                   "import-by-name entry exceeds the PE image");
                        (void)file_offset_for_rva(
                            thunk_value, 2, headers_size, sections);
                        function_name = read_import_name(
                            file, file_size, thunk_value + 2, headers_size,
                            sections);
                    }
                    require_pe(imported_iat_slots.emplace(
                                   static_cast<uint32_t>(iat_rva)).second,
                               "multiple imports share one IAT slot");
                    imported_thunks.push_back({
                        static_cast<uint32_t>(iat_rva),
                        module_name + "!" + function_name});
                }
                require_pe(found_thunk_terminator,
                           "import thunk array has no terminator");
            }
            require_pe(found_terminator,
                       "import descriptor table has no terminator");
        }

        std::vector<PeSection> virtual_order = sections;
        std::sort(virtual_order.begin(), virtual_order.end(),
                  [](const PeSection& left, const PeSection& right) {
                      return left.virtual_address < right.virtual_address;
                  });
        uint64_t previous_end = headers_size;
        for (const auto& section : virtual_order) {
            if (section.mapped_size() == 0) continue;
            require_pe(section.virtual_address >= previous_end,
                       "virtual sections overlap");
            previous_end = section.virtual_address + section.mapped_size();
        }

        std::array<uint8_t, kCopyChunkSize> buffer{};
        auto copy_range = [&](uint64_t file_offset, uint64_t guest_offset,
                              uint64_t size) {
            while (size != 0) {
                const size_t chunk = static_cast<size_t>(
                    std::min<uint64_t>(size, buffer.size()));
                read_file_range(file, file_size, file_offset,
                                buffer.data(), chunk);
                std::memcpy(static_cast<uint8_t*>(ram) + guest_offset,
                            buffer.data(), chunk);
                file_offset += chunk;
                guest_offset += chunk;
                size -= chunk;
            }
        };
        copy_range(0, image_base, headers_size);
        for (const auto& section : sections) {
            if (section.raw_size == 0) continue;
            copy_range(section.raw_offset,
                       static_cast<uint64_t>(image_base) +
                           section.virtual_address,
                       section.raw_size);
        }

        std::vector<std::string> unique_imports;
        std::unordered_map<std::string, size_t> import_indices;
        for (const auto& thunk : imported_thunks) {
            const size_t index = unique_imports.size();
            if (import_indices.emplace(thunk.name, index).second) {
                unique_imports.push_back(thunk.name);
            }
        }
        const uint32_t import_stub_base = choose_import_stub_base(
            image_base, image_size, unique_imports.size());
        for (size_t index = 0; index < unique_imports.size(); ++index) {
            const uint32_t stub = static_cast<uint32_t>(
                static_cast<uint64_t>(import_stub_base) +
                index * kImportStubStride);
            import_traps.emplace(stub, unique_imports[index]);
        }
        // Ghidra's lowered external-call thunks use one-based import indices.
        for (size_t index = 0; index < imported_thunks.size(); ++index) {
            const size_t stub_index = import_indices.at(
                imported_thunks[index].name);
            const uint32_t stub = static_cast<uint32_t>(
                static_cast<uint64_t>(import_stub_base) +
                stub_index * kImportStubStride);
            import_id_traps.emplace(static_cast<uint32_t>(index + 1), stub);
        }
        const uint32_t module_handle_base = choose_guest_module_handle_base(
            image_base, image_size, import_stub_base, unique_imports.size(),
            import_modules.size());
        for (size_t index = 0; index < import_modules.size(); ++index) {
            const uint32_t handle = static_cast<uint32_t>(
                static_cast<uint64_t>(module_handle_base) +
                index * kGuestModuleHandleStride);
            guest_module_handles.emplace(
                lowercase_ascii(import_modules[index]), handle);
            guest_module_names.emplace(
                handle, lowercase_ascii(import_modules[index]));
        }
        next_dynamic_import_stub_address = kGuestDynamicImportStubBase;
        for (const auto& thunk : imported_thunks) {
            const size_t index = import_indices.at(thunk.name);
            const uint32_t stub = static_cast<uint32_t>(
                static_cast<uint64_t>(import_stub_base) +
                index * kImportStubStride);
            const std::array<uint8_t, 4> bytes = {
                static_cast<uint8_t>(stub),
                static_cast<uint8_t>(stub >> 8),
                static_cast<uint8_t>(stub >> 16),
                static_cast<uint8_t>(stub >> 24),
            };
            const uint64_t guest_offset =
                static_cast<uint64_t>(image_base) + thunk.iat_rva;
            std::memcpy(static_cast<uint8_t*>(ram) + guest_offset,
                        bytes.data(), bytes.size());
        }

        pe_image_base = image_base;
        pe_image_size = image_size;
        pe_image_file_name = path;
        pe_image_entry_point = entry_rva == 0 ? 0 : image_base + entry_rva;
        return {image_base, image_size,
                pe_image_entry_point,
                section_count,
                static_cast<uint32_t>(import_modules.size()),
                static_cast<uint32_t>(imported_thunks.size()),
                import_stub_base};
    }

    bool initialize_pe32_guest_thread_state() {
        const uint64_t teb_end =
            static_cast<uint64_t>(kGuestTebAddress) + kGuestTebSize;
        const uint64_t image_begin = pe_image_base;
        const uint64_t image_end = image_begin + pe_image_size;
        if (pe_image_size != 0 && kGuestTebAddress < image_end &&
            image_begin < teb_end) {
            error = "PE32 guest TEB overlaps the loaded image";
            return false;
        }

        std::array<uint8_t, kGuestTebSize> teb{};
        const auto store_teb_u32 = [&teb](size_t offset, uint32_t value) {
            for (size_t index = 0; index < sizeof(value); ++index) {
                teb[offset + index] =
                    static_cast<uint8_t>(value >> (index * 8));
            }
        };
        store_teb_u32(0x00, UINT32_MAX);  // ExceptionList sentinel.
        store_teb_u32(0x04, kGuestInitialStackPointer);
        store_teb_u32(0x08, kGuestStackLimit);
        store_teb_u32(0x18, kGuestTebAddress);
        const long host_thread_id = syscall(SYS_gettid);
        if (host_thread_id < 0) {
            error = "cannot initialize guest thread identity";
            return false;
        }
        current_guest_thread_id = static_cast<uint32_t>(host_thread_id);
        store_teb_u32(0x20, static_cast<uint32_t>(getpid()));
        store_teb_u32(0x24, current_guest_thread_id);

        constexpr std::array<uint8_t, 4> fs_base_bytes = {
            static_cast<uint8_t>(kGuestTebAddress),
            static_cast<uint8_t>(kGuestTebAddress >> 8),
            static_cast<uint8_t>(kGuestTebAddress >> 16),
            static_cast<uint8_t>(kGuestTebAddress >> 24)};
        if (!write_guest("register", kX86FsBaseRegisterOffset,
                         fs_base_bytes.size(), fs_base_bytes.data()) ||
            !write_guest_bytes(kGuestTebAddress, teb.data(), teb.size(),
                               "PE32 startup TEB")) {
            return false;
        }

        // Ghidra x86:LE:32:default stores the x87 CW, SW, and TW contiguously.
        constexpr std::array<uint8_t, 6> x87_environment = {
            0x7f, 0x03,  // FINIT control word: masked, 64-bit precision.
            0x00, 0x00,  // Clear status and TOP.
            0xff, 0xff}; // Mark all x87 stack registers empty.
        if (!write_guest("register", kX86X87EnvironmentRegisterOffset,
                         x87_environment.size(), x87_environment.data())) {
            error = "cannot initialize PE32 x87 state";
            return false;
        }
        return true;
    }

    int call_pe32_entry_point() {
        error.clear();
        if (call_depth != 0) {
            error = "cannot start a PE32 entry point during P-code dispatch";
            return -1;
        }
        if (pe_image_entry_point == 0) {
            error = "loaded PE32 image has no entry point";
            return -1;
        }
        if (pe32_entry_point_started) {
            error = "PE32 entry point has already been invoked";
            return -1;
        }
        pe32_entry_point_started = true;
        execution_started = true;
        if (!initialize_pe32_guest_thread_state() ||
            !write_guest_u32("register", kX86EspRegisterOffset,
                             kGuestInitialStackPointer) ||
            !write_guest_u32("register", kX86EbpRegisterOffset, 0) ||
            !write_guest_u32("ram", kGuestInitialStackPointer, 0)) {
            error = "cannot initialize PE32 entry-point stack";
            return -1;
        }
        main_guest_thread = GuestThread{};
        main_guest_thread.id = current_guest_thread_id;
        main_guest_thread.last_error = guest_last_error;
        save_execution_state(main_guest_thread);
        if (!initialize_guest_coroutine(0)) return -1;
        enqueue_guest_thread(0);
        return run_guest_scheduler(4096, true) ? 0 : -1;
    }

    int run_guest_threads() {
        if (!pe32_entry_point_started) return 0;
        error.clear();
        return run_guest_scheduler(64, false) ? 0 : -1;
    }

    bool entry_point_complete() const { return pe32_entry_point_complete; }

    bool read_guest(const char* space, uint64_t offset, size_t size,
                    uint8_t* output) {
        if (!space || !output || size == 0 || size > kMaximumPcodeValueSize) {
            error = "invalid P-code memory read request";
            return false;
        }
        if (std::strcmp(space, "register") == 0) {
            if (offset > kRegisterBankSize ||
                size > kRegisterBankSize - static_cast<size_t>(offset)) {
                error = "P-code register read is out of range";
                return false;
            }
            std::memcpy(output, registers.data() + offset, size);
            return true;
        }
        if (std::strcmp(space, "ram") == 0) {
            if (offset > kGuestRamSize || size > kGuestRamSize - offset) {
                error = "P-code RAM read is out of range";
                return false;
            }
            std::memcpy(output, static_cast<const uint8_t*>(ram) + offset,
                        size);
            return true;
        }
        error = "unsupported P-code address space: " + std::string(space);
        return false;
    }

    bool write_guest(const char* space, uint64_t offset, size_t size,
                     const uint8_t* input) {
        if (!space || !input || size == 0 || size > kMaximumPcodeValueSize) {
            error = "invalid P-code memory write request";
            return false;
        }
        if (std::strcmp(space, "register") == 0) {
            if (offset > kRegisterBankSize ||
                size > kRegisterBankSize - static_cast<size_t>(offset)) {
                error = "P-code register write is out of range at offset " +
                        std::to_string(offset) + " size " +
                        std::to_string(size);
                if (!active_guest_functions.empty()) {
                    error += " from guest function " +
                             std::to_string(active_guest_functions.back());
                }
                return false;
            }
            std::memcpy(registers.data() + offset, input, size);
            return true;
        }
        if (std::strcmp(space, "ram") == 0) {
            if (offset > kGuestRamSize || size > kGuestRamSize - offset) {
                error = "P-code RAM write is out of range";
                return false;
            }
            std::memcpy(static_cast<uint8_t*>(ram) + offset, input, size);
            return true;
        }
        error = "unsupported P-code address space: " + std::string(space);
        return false;
    }

    void* module = nullptr;
    void* ram = nullptr;
    std::array<uint8_t, kRegisterBankSize> registers{};
    RviPcodeContext context{};
    std::unordered_map<uint32_t, PcodeFunction> functions;
    std::vector<void*> supplemental_modules;
    std::vector<void*> override_modules;
    std::unordered_map<uint32_t, std::string> import_traps;
    std::unordered_map<uint32_t, uint32_t> import_id_traps;
    std::unordered_map<std::string, uint32_t> guest_module_handles;
    std::unordered_map<uint32_t, std::string> guest_module_names;
    std::unordered_map<uint32_t, GuestHeapBlock> heap_allocations;
    std::vector<GuestHeapBlock> free_heap_blocks;
    std::unordered_set<uint32_t> guest_heap_handles{kGuestProcessHeapHandle};
    std::unordered_set<uint32_t> allocated_tls_indices;
    std::unordered_map<uint32_t, uint32_t> tls_values;
    std::vector<uint32_t> free_tls_indices;
    std::unordered_map<uint32_t, GuestCriticalSection> critical_sections;
    std::unordered_map<uint32_t, GuestMutex> guest_mutexes;
    std::unordered_map<uint32_t, GuestFile> guest_files;
    std::unordered_map<uint32_t, GuestEvent> guest_events;
    std::unordered_map<uint32_t, GuestFiber> guest_fibers;
    std::unordered_map<uint32_t, GuestThread> guest_threads;
    GuestThread main_guest_thread;
    ucontext_t scheduler_context{};
    std::deque<uint32_t> ready_guest_threads;
    std::unordered_map<uint32_t, uint32_t> guest_timer_period_requests;
    std::unordered_map<uint32_t, uint64_t> guest_virtual_allocations;
    std::unordered_map<std::string, uint32_t> guest_named_mutexes;
    std::unordered_map<std::string,
                       std::pair<std::string, std::string>>
        guest_environment_variables;
    std::unordered_set<uint32_t> guest_environment_blocks;
    std::vector<uint32_t> active_guest_functions;
    bool command_line_initialized = false;
    bool environment_initialized = false;
    uint32_t guest_last_error = 0;
    uint32_t guest_process_priority_class = 0x00000020;
    int32_t guest_thread_priority = 0;
    uint32_t guest_thread_ideal_processor = 0;
    uint32_t current_guest_thread_id = 0;
    uint32_t current_guest_thread_handle = 0;
    uint32_t current_guest_thread_exit_code = 259;
    bool current_guest_thread_exit_requested = false;
    uint32_t guest_symbol_options = 0;
    uint32_t guest_symbol_process_handle = 0;
    bool guest_symbol_handler_initialized = false;
    uint32_t guest_unhandled_exception_filter = 0;
    uint64_t function_count = 0;
    std::unordered_set<uint32_t> unique_function_addresses;
    uint64_t guest_heap_next_address = kGuestHeapStartAddress;
    uint64_t guest_virtual_next_address = UINT64_C(0x20000000);
    uint64_t next_guest_heap_handle = kGuestProcessHeapHandle + 4;
    uint64_t next_guest_mutex_handle = 0x00030000;
    uint64_t next_guest_file_handle = kGuestFileHandleBase;
    uint64_t next_guest_event_handle = kGuestEventHandleBase;
    uint32_t next_guest_fiber_handle = kGuestFiberHandleBase;
    uint32_t next_guest_thread_id = 0x00010000;
    uint32_t next_guest_thread_handle = kGuestThreadHandleBase;
    uint32_t current_guest_fiber = 0;
    uint64_t next_dynamic_import_stub_address =
        kGuestDynamicImportStubBase;
    uint32_t next_tls_index = 0;
    uint32_t pe_image_base = 0;
    uint32_t pe_image_size = 0;
    uint32_t pe_image_entry_point = 0;
    std::string pe_image_file_name;
    uint32_t call_depth = 0;
    uint32_t indirect_jump_depth = 0;
    bool pe_image_load_attempted = false;
    bool pe32_entry_point_started = false;
    bool pe32_entry_point_complete = false;
    bool scheduler_context_active = false;
    bool guest_coroutine_active = false;
    bool pause_scheduler_after_yield = false;
    bool execution_started = false;
    std::string error;
};

RecompiledPcodeModule::RecompiledPcodeModule(const std::string& shared_object_path)
    : impl_(std::make_unique<Impl>(shared_object_path)) {}

RecompiledPcodeModule::~RecompiledPcodeModule() = default;

int RecompiledPcodeModule::call(uint32_t guest_address) {
    impl_->error.clear();
    if (impl_->call_depth != 0) {
        impl_->error = "cannot begin a P-code entry call during dispatch";
        return -1;
    }
    impl_->execution_started = true;
    return impl_->dispatch(guest_address);
}

Pe32ImageInfo RecompiledPcodeModule::load_pe32_image(const std::string& path) {
    return impl_->load_pe32_image(path);
}

int RecompiledPcodeModule::call_pe32_entry_point() {
    return impl_->call_pe32_entry_point();
}

int RecompiledPcodeModule::run_guest_threads() {
    return impl_->run_guest_threads();
}

bool RecompiledPcodeModule::pe32_entry_point_complete() const {
    return impl_->entry_point_complete();
}

bool RecompiledPcodeModule::load_supplemental_module(
    const std::string& shared_object_path) {
    return impl_->load_supplemental_module(shared_object_path);
}

bool RecompiledPcodeModule::load_override_module(
    const std::string& shared_object_path) {
    return impl_->load_override_module(shared_object_path);
}

uint64_t RecompiledPcodeModule::dispatched_function_count() const {
    return impl_->function_count;
}

uint64_t RecompiledPcodeModule::unique_dispatched_function_count() const {
    return impl_->unique_function_addresses.size();
}

const std::string& RecompiledPcodeModule::last_error() const {
    return impl_->error;
}

bool RecompiledPcodeModule::read_guest(const char* space, uint64_t offset,
                                       size_t size, uint8_t* output) {
    return impl_->read_guest(space, offset, size, output);
}

bool RecompiledPcodeModule::write_guest(const char* space, uint64_t offset,
                                        size_t size, const uint8_t* input) {
    return impl_->write_guest(space, offset, size, input);
}

}  // namespace shift::runtime
