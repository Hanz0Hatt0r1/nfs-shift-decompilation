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
#include <iterator>
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
constexpr size_t kGuestWriteProvenanceWordLimit = 65536;
constexpr uint32_t kGuestMinimumUserAddress = 0x00010000;
constexpr size_t kGuestFunctionHistoryLimit = 64;
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
constexpr uint32_t kRetailUiStateGateAddress = 0x0050ceb0;
constexpr uint32_t kRetailUiStateGateHelperAddress = 0x0050c880;
constexpr size_t kRetailUiStateGateTraceLimit = 8192;
constexpr size_t kGuestCallTraceLimit = 8192;
constexpr size_t kGuestCallTraceSelectionLimit = 32;
constexpr size_t kGuestCallTraceStringByteLimit = 256;
constexpr uint32_t kGuestProcessHeapHandle = 0x00010000;
constexpr uint32_t kGuestCurrentProcessPseudoHandle = UINT32_MAX;
constexpr uint32_t kGuestCurrentThreadPseudoHandle = UINT32_MAX - 1;

std::vector<uint32_t> parse_guest_trace_u32_values(const char* input,
                                                    bool allow_zero) {
    std::vector<uint32_t> values;
    if (!input || !*input) return values;
    const std::string text(input);
    size_t offset = 0;
    while (offset < text.size() &&
           values.size() < kGuestCallTraceSelectionLimit) {
        const size_t separator = text.find_first_of(",;", offset);
        const size_t end = separator == std::string::npos
                               ? text.size()
                               : separator;
        const std::string token = text.substr(offset, end - offset);
        char* parse_end = nullptr;
        errno = 0;
        const unsigned long long value =
            std::strtoull(token.c_str(), &parse_end, 0);
        if (!token.empty() && errno == 0 && parse_end &&
            *parse_end == '\0' && value <= UINT32_MAX &&
            (allow_zero || value != 0)) {
            const uint32_t parsed = static_cast<uint32_t>(value);
            if (std::find(values.begin(), values.end(), parsed) ==
                values.end()) {
                values.push_back(parsed);
            }
        }
        if (separator == std::string::npos) break;
        offset = separator + 1;
    }
    return values;
}

std::vector<std::string> parse_guest_trace_names(const char* input) {
    std::vector<std::string> values;
    if (!input || !*input) return values;
    const std::string text(input);
    size_t offset = 0;
    while (offset < text.size() &&
           values.size() < kGuestCallTraceSelectionLimit) {
        const size_t separator = text.find_first_of(",;", offset);
        const size_t end = separator == std::string::npos
                               ? text.size()
                               : separator;
        const std::string value = text.substr(offset, end - offset);
        if (!value.empty() &&
            std::find(values.begin(), values.end(), value) == values.end()) {
            values.push_back(value);
        }
        if (separator == std::string::npos) break;
        offset = separator + 1;
    }
    return values;
}

// ponytail: use an opaque guest HWND until D3D9 consumes the native window.
constexpr uint32_t kGuestDesktopWindowHandle = 0x00030000;
constexpr uint32_t kGuestSyntheticIconHandle = 0x00030004;
constexpr uint32_t kGuestSyntheticWindowHandle = 0x00030008;
constexpr uint32_t kGuestSyntheticGdiObjectBase = 0x00030010;
constexpr uint32_t kGuestSyntheticDisplayDcBase = 0x00030040;
constexpr uint32_t kGuestFileHandleBase = 0x00050000;
constexpr uint32_t kGuestEventHandleBase = 0x00060000;
constexpr uint32_t kGuestSemaphoreHandleBase = 0x00070000;
constexpr uint32_t kGuestTimerPeriodMs = 1;
constexpr uint32_t kGuestTimerNoError = 0;
constexpr uint32_t kGuestTimerErrNoCanDo = 97;
constexpr uint32_t kD3dErrInvalidCall = 0x8876086c;
constexpr uint32_t kD3dErrNotFound = 0x88760866;
constexpr uint32_t kD3dErrNotAvailable = 0x8876086a;
constexpr uint32_t kD3dErrInvalidDevice = 0x88760870;
constexpr uint32_t kD3dFormatA8R8G8B8 = 21;
constexpr uint32_t kD3dUsageRenderTarget = 1;
constexpr uint32_t kD3dPoolDefault = 0;
constexpr uint32_t kD3dFormatX8R8G8B8 = 22;
constexpr size_t kD3dCaps9Size = 304;
constexpr size_t kD3dAdapterIdentifier9Size = 1100;
static_assert(kD3dCaps9Size == 76 * sizeof(uint32_t));
constexpr uint32_t kCsidlPersonal = 5;
constexpr uint32_t kCsidlFlagCreate = 0x8000;
constexpr uint32_t kCsidlFlagDontVerify = 0x4000;
constexpr uint32_t kHresultInvalidArg = 0x80070057;
constexpr uint32_t kHresultFail = 0x80004005;
constexpr size_t kWindowsMaxPath = 260;
constexpr uint32_t kGuestAlreadyFiberError = 1280;
constexpr size_t kMaximumGuestFileReadBytes = 64 * 1024 * 1024;
constexpr uint32_t kGuestAllocationTraceThreshold = 16 * 1024 * 1024;
constexpr size_t kGuestAllocationObjectTraceSize = 0x130;
constexpr size_t kGuestAllocationObjectLinkLimit = 12;
constexpr size_t kGuestAllocationObjectChainLinkLimit = 64;
constexpr size_t kGuestAllocationLinkNextPointerWordIndex = 0x10 / 4;
constexpr uint32_t kRetailPoolAllocateFunctionAddress = 0x00638020;
constexpr uint32_t kRetailPoolTryAllocateFunctionAddress = 0x00637f50;
constexpr uint32_t kRetailPoolInitializerAddress = 0x00d8a600;
constexpr uint32_t kRetailPoolListInitHelperAddress = 0x00506ab0;
constexpr uint32_t kRetailPoolInitReturnAddress = 0x00d8a681;
constexpr size_t kGuestAllocationPoolAttemptLimit = 32;
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
constexpr uint64_t kX86EcxRegisterOffset = 4;
constexpr uint64_t kX86EdxRegisterOffset = 8;
constexpr uint64_t kX86EbxRegisterOffset = 0x0c;
constexpr uint64_t kX86EspRegisterOffset = 0x10;
constexpr uint64_t kX86EbpRegisterOffset = 0x14;
constexpr uint64_t kX86EsiRegisterOffset = 0x18;
constexpr uint64_t kX86EdiRegisterOffset = 0x1c;
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
    struct GuestObjectLinkSnapshot {
        uint32_t address = 0;
        uint32_t parent_address = 0;
        std::array<uint32_t, 6> memory{};
    };
    struct GuestRegisterSnapshot {
        uint32_t eax = 0;
        uint32_t ecx = 0;
        uint32_t edx = 0;
        uint32_t ebx = 0;
        uint32_t esp = 0;
        uint32_t ebp = 0;
        uint32_t esi = 0;
        uint32_t edi = 0;
        uint32_t stack_return_slot = 0;
        bool has_stack_arguments = false;
        std::array<uint32_t, 3> stack_arguments{};
        std::array<std::array<uint32_t, 4>, 3> stack_argument_memory{};
        std::array<bool, 3> has_stack_argument_memory{};
        bool has_ecx_object_memory = false;
        std::array<uint32_t, kGuestAllocationObjectTraceSize / 4>
            ecx_object_memory{};
        size_t ecx_object_link_count = 0;
        std::array<GuestObjectLinkSnapshot,
                   kGuestAllocationObjectLinkLimit>
            ecx_object_links{};
        size_t ecx_object_chain_link_count = 0;
        std::array<GuestObjectLinkSnapshot,
                   kGuestAllocationObjectChainLinkLimit>
            ecx_object_chain_links{};
    };
    struct GuestWriteProvenance {
        uint64_t sequence = 0;
        uint64_t dispatch_count = 0;
        uint32_t writer_function = 0;
        uint32_t writer_ecx = 0;
        bool has_writer_ecx = false;
        uint32_t writer_caller_function = 0;
        bool has_writer_caller_function = false;
        uint32_t writer_call_return_address = 0;
        bool has_writer_call_return_address = false;
        uint32_t writer_caller_return_address = 0;
        bool has_writer_caller_return_address = false;
        uint32_t writer_ancestor_function = 0;
        bool has_writer_ancestor_function = false;
        uint32_t writer_ancestor_caller_function = 0;
        bool has_writer_ancestor_caller_function = false;
        uint32_t writer_ancestor_return_address = 0;
        bool has_writer_ancestor_return_address = false;
        uint32_t thread_id = 0;
        uint32_t write_address = 0;
        uint32_t write_size = 0;
        uint32_t word_value = 0;
    };
    struct GuestPoolAllocationAttempt {
        uint64_t sequence = 0;
        uint32_t function_address = 0;
        uint32_t return_address = 0;
        uint32_t pool_address = 0;
        uint32_t request_size = 0;
        uint32_t request_flags = 0;
        uint32_t pool_flags = 0;
        uint32_t pool_threshold = 0;
        uint32_t list_head_100 = 0;
        uint32_t list_head_104 = 0;
        uint32_t result_eax = 0;
        bool has_result_eax = false;
        std::array<char, 32> pool_name{};
        uint32_t selected_list_head = 0;
        uint32_t selected_list_next_offset = 0;
        size_t selected_list_node_count = 0;
        bool selected_list_terminated = false;
        bool selected_list_truncated = false;
        bool selected_list_cycle = false;
        std::array<GuestObjectLinkSnapshot,
                   kGuestAllocationObjectChainLinkLimit>
            selected_list_nodes{};
    };
    struct GuestSemaphore {
        uint32_t count = 0;
        uint32_t maximum_count = 0;
    };
    struct GuestD3D9Interface {
        uint32_t vtable_address = 0;
        uint32_t references = 1;
    };
    struct GuestD3D9Device {
        uint32_t vtable_address = 0;
        uint32_t direct3d_interface = 0;
        uint32_t references = 1;
        uint32_t focus_window = 0;
        uint32_t behavior_flags = 0;
        uint32_t vertex_shader_address = 0;
        uint32_t pixel_shader_address = 0;
        std::unordered_map<uint32_t, uint32_t> textures;
        std::unordered_map<uint32_t, uint32_t> render_targets;
        std::unordered_map<uint32_t, uint32_t> render_states;
        uint32_t depth_surface_address = 0;
        std::unordered_map<uint64_t, uint32_t> sampler_states;
        RecompiledGuestD3d9PresentationParameters presentation;
        bool scene_active = false;
        std::array<uint32_t, 6> viewport{};
        uint32_t present_request_count = 0;
        uint32_t clear_call_count = 0;
        uint32_t last_clear_flags = 0;
        uint32_t last_clear_color = 0;
        uint32_t last_clear_depth_bits = 0;
        uint32_t last_clear_stencil = 0;
        uint32_t last_clear_rect_count = 0;
    };
    struct GuestD3D9Surface {
        uint32_t vtable_address = 0;
        uint32_t device_address = 0;
        uint32_t references = 1;
        uint32_t render_target_index = 0;
        bool depth_stencil = false;
    };
    struct GuestD3D9Texture {
        uint32_t vtable_address = 0;
        uint32_t device_address = 0;
        uint32_t references = 1;
        uint32_t width = 0;
        uint32_t height = 0;
        uint32_t levels = 0;
        uint32_t usage = 0;
        uint32_t format = 0;
        uint32_t pool = 0;
    };
    struct GuestD3D9VertexBuffer {
        uint32_t vtable_address = 0;
        uint32_t device_address = 0;
        uint32_t data_address = 0;
        uint32_t references = 1;
        uint32_t size = 0;
        uint32_t usage = 0;
        uint32_t fvf = 0;
        uint32_t pool = 0;
        uint32_t lock_offset = 0;
        uint32_t lock_size = 0;
        bool locked = false;
    };
    struct GuestFiber {
        uint32_t data = 0;
    };
    struct GuestIoCompletion {
        uint32_t routine = 0;
        uint32_t overlapped = 0;
        uint32_t error_code = 0;
        uint32_t bytes_transferred = 0;
    };
    struct GuestExecutionState {
        std::array<uint8_t, kRegisterBankSize> registers{};
        std::unordered_map<uint32_t, uint32_t> tls_values;
        std::vector<uint32_t> active_functions;
        std::vector<GuestRegisterSnapshot> active_function_registers;
        std::deque<uint32_t> recent_functions;
        std::deque<GuestIoCompletion> io_completions;
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
        uint64_t wait_sequence = 0;
        std::chrono::steady_clock::time_point wait_deadline{};
        bool started = false;
        bool completed = false;
        bool close_pending = false;
        bool coroutine_initialized = false;
        bool runnable = false;
        bool waiting = false;
        bool wait_alertable = false;
    };

    explicit Impl(const std::string& path) {
        if (const char* enabled = std::getenv("SHIFT_TRACE_UI_STATE_GATE");
            enabled && *enabled && std::strcmp(enabled, "0") != 0) {
            ui_state_gate_trace_enabled = true;
        }
        if (const char* caller = std::getenv("SHIFT_TRACE_GUEST_CALLER");
            caller && *caller) {
            char* parse_end = nullptr;
            errno = 0;
            const unsigned long long value =
                std::strtoull(caller, &parse_end, 0);
            if (errno == 0 && parse_end && *parse_end == '\0' &&
                value > 0 && value <= UINT32_MAX) {
                guest_call_trace_caller = static_cast<uint32_t>(value);
                guest_call_trace_enabled = true;
            }
        }
        guest_call_trace_targets = parse_guest_trace_u32_values(
            std::getenv("SHIFT_TRACE_GUEST_CALL_TARGETS"), false);
        guest_call_trace_imports = parse_guest_trace_names(
            std::getenv("SHIFT_TRACE_GUEST_CALL_IMPORTS"));
        guest_call_trace_enabled =
            guest_call_trace_enabled || !guest_call_trace_targets.empty() ||
            !guest_call_trace_imports.empty();
        if (guest_call_trace_enabled) {
            guest_call_trace_slot_offsets = parse_guest_trace_u32_values(
                std::getenv("SHIFT_TRACE_GUEST_CALLER_SLOTS"), true);
            guest_call_trace_target_slot_offsets =
                parse_guest_trace_u32_values(
                    std::getenv("SHIFT_TRACE_GUEST_CALL_TARGET_SLOTS"), true);
            guest_call_trace_stack_slot_offsets = parse_guest_trace_u32_values(
                std::getenv("SHIFT_TRACE_GUEST_CALL_STACK_SLOTS"), true);
            guest_call_trace_string_slot_offsets = parse_guest_trace_u32_values(
                std::getenv("SHIFT_TRACE_GUEST_CALL_STRING_SLOTS"), true);
        }
        static_assert(sizeof(size_t) >= sizeof(uint64_t),
                      "the guest RAM reservation requires a 64-bit host");
        if (const char* provenance =
                std::getenv("SHIFT_TRACE_GUEST_PROVENANCE");
            provenance && *provenance && std::strcmp(provenance, "0") != 0) {
            guest_write_provenance_enabled_flag = true;
            guest_write_provenance_all_flag =
                std::strcmp(provenance, "1") == 0 ||
                std::strcmp(provenance, "all") == 0;
            if (!guest_write_provenance_all_flag) {
                std::string text(provenance);
                size_t offset = 0;
                while (offset < text.size()) {
                    const size_t separator =
                        text.find_first_of(",;", offset);
                    const size_t end =
                        separator == std::string::npos
                            ? text.size()
                            : separator;
                    const std::string token =
                        text.substr(offset, end - offset);
                    if (!token.empty()) {
                        char* parse_end = nullptr;
                        errno = 0;
                        const unsigned long long value =
                            std::strtoull(token.c_str(), &parse_end, 0);
                        if (errno == 0 && parse_end &&
                            *parse_end == '\0' && value <= UINT32_MAX) {
                            guest_write_provenance_targets_cache.push_back(
                                static_cast<uint32_t>(value));
                        }
                    }
                    if (separator == std::string::npos) break;
                    offset = separator + 1;
                }
            }
        }
        std::error_code cwd_error;
        const std::filesystem::path host_current_directory =
            std::filesystem::current_path(cwd_error);
        if (cwd_error) {
            throw std::runtime_error(
                "cannot read host working directory: " + cwd_error.message());
        }
        guest_filesystem_root =
            std::filesystem::canonical(host_current_directory, cwd_error);
        if (cwd_error) {
            throw std::runtime_error(
                "cannot establish guest filesystem root: " +
                cwd_error.message());
        }
        guest_current_host_directory = guest_filesystem_root;
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

    bool set_guest_display_mode(uint32_t width, uint32_t height,
                                uint32_t refresh_rate, uint32_t format) {
        if (width == 0 || height == 0) {
            error = "guest display mode width and height must be nonzero";
            return false;
        }
        guest_display_width = width;
        guest_display_height = height;
        guest_display_refresh_rate = refresh_rate;
        guest_display_format = format;
        error.clear();
        return true;
    }

    bool set_guest_d3d9_adapter_info(
        const RecompiledGuestD3d9AdapterInfo& adapter_info) {
        if (execution_started || call_depth != 0) {
            error = "cannot configure the guest D3D9 adapter after execution starts";
            return false;
        }
        guest_d3d9_adapter_info = adapter_info;
        guest_d3d9_adapter_info_available = true;
        error.clear();
        return true;
    }

    size_t record_guest_call_trace(uint32_t target,
                                   const std::string& import_name = {}) {
        if (!guest_call_trace_enabled || active_guest_functions.empty()) {
            return std::numeric_limits<size_t>::max();
        }
        const uint32_t caller = active_guest_functions.back();
        const bool selected_caller = guest_call_trace_caller != 0 &&
                                     caller == guest_call_trace_caller;
        const bool selected_target = std::find(
                                         guest_call_trace_targets.begin(),
                                         guest_call_trace_targets.end(), target) !=
                                     guest_call_trace_targets.end();
        const bool selected_import = !import_name.empty() && std::find(
            guest_call_trace_imports.begin(), guest_call_trace_imports.end(),
            import_name) != guest_call_trace_imports.end();
        if (!selected_caller && !selected_target && !selected_import) {
            return std::numeric_limits<size_t>::max();
        }
        if (guest_call_trace_events.size() >= kGuestCallTraceLimit) {
            guest_call_trace_truncated = true;
            return std::numeric_limits<size_t>::max();
        }

        RecompiledGuestCallTraceEvent event{};
        event.dispatch_count = function_count;
        event.thread_id = current_guest_thread_id;
        event.function = target;
        event.caller = caller;
        event.is_import = !import_name.empty();
        event.import_name = import_name;
        (void)read_guest_u32("register", kX86EcxRegisterOffset,
                             event.ecx_entry);
        event.caller_ecx = active_guest_function_registers.empty()
                               ? event.ecx_entry
                               : active_guest_function_registers.back().ecx;
        (void)read_guest_u32("register", kX86EaxRegisterOffset,
                             event.eax_entry);
        (void)read_guest_u32("register", kX86EdxRegisterOffset,
                             event.edx_entry);
        (void)read_guest_u32("register", kX86EdiRegisterOffset,
                             event.edi_entry);
        uint32_t stack_pointer = 0;
        const bool has_stack_pointer = read_guest_u32(
            "register", kX86EspRegisterOffset, stack_pointer);
        if (has_stack_pointer) {
            event.has_return_address = read_guest_u32(
                "ram", stack_pointer, event.return_address);
        }
        const auto sample_slots = [&](uint32_t base,
                                      const std::vector<uint32_t>& offsets) {
            std::vector<RecompiledGuestCallTraceMemorySlot> slots;
            slots.reserve(offsets.size());
            for (const uint32_t slot_offset : offsets) {
                RecompiledGuestCallTraceMemorySlot slot{};
                slot.offset = slot_offset;
                const uint64_t address =
                    static_cast<uint64_t>(base) + slot_offset;
                if (address <= UINT32_MAX) {
                    slot.has_value =
                        read_guest_u32("ram", address, slot.value);
                    if (guest_write_provenance_enabled_flag) {
                        const auto writer = guest_target_last_writers.find(
                            static_cast<uint32_t>(address));
                        if (writer != guest_target_last_writers.end()) {
                            const auto& provenance = writer->second;
                            slot.has_last_writer = true;
                            slot.last_writer.sequence = provenance.sequence;
                            slot.last_writer.dispatch_count =
                                provenance.dispatch_count;
                            slot.last_writer.function =
                                provenance.writer_function;
                            slot.last_writer.ecx_entry =
                                provenance.writer_ecx;
                            slot.last_writer.has_ecx_entry =
                                provenance.has_writer_ecx;
                            slot.last_writer.caller_function =
                                provenance.writer_caller_function;
                            slot.last_writer.has_caller_function =
                                provenance.has_writer_caller_function;
                            slot.last_writer.call_return_address =
                                provenance.writer_call_return_address;
                            slot.last_writer.has_call_return_address =
                                provenance.has_writer_call_return_address;
                            slot.last_writer.caller_return_address =
                                provenance.writer_caller_return_address;
                            slot.last_writer.has_caller_return_address =
                                provenance.has_writer_caller_return_address;
                            slot.last_writer.thread_id = provenance.thread_id;
                            slot.last_writer.write_address =
                                provenance.write_address;
                            slot.last_writer.write_size = provenance.write_size;
                            slot.last_writer.word_value =
                                provenance.word_value;
                        }
                    }
                }
                slots.push_back(slot);
            }
            return slots;
        };
        const auto sample_string_slots = [&](
            uint32_t base, const std::vector<uint32_t>& offsets) {
            std::vector<RecompiledGuestCallTraceStringSlot> slots;
            slots.reserve(offsets.size());
            for (const uint32_t slot_offset : offsets) {
                RecompiledGuestCallTraceStringSlot slot{};
                slot.offset = slot_offset;
                const uint64_t slot_address =
                    static_cast<uint64_t>(base) + slot_offset;
                if (slot_address <= UINT32_MAX &&
                    read_guest_diagnostic_u32(slot_address, slot.address)) {
                    slot.has_address = true;
                    if (slot.address >= kGuestMinimumUserAddress &&
                        slot.address < kGuestRamSize) {
                        slot.has_value = true;
                        for (size_t index = 0;
                             index < kGuestCallTraceStringByteLimit; ++index) {
                            const uint64_t address =
                                static_cast<uint64_t>(slot.address) + index;
                            uint8_t byte = 0;
                            if (address >= kGuestRamSize ||
                                !read_guest_diagnostic_u8(address, byte)) {
                                slot.has_value = false;
                                slot.value.clear();
                                break;
                            }
                            if (byte == 0) {
                                slot.terminated = true;
                                break;
                            }
                            if (byte < 0x20 || byte > 0x7e) {
                                slot.has_value = false;
                                slot.value.clear();
                                break;
                            }
                            slot.value.push_back(static_cast<char>(byte));
                        }
                        if (slot.has_value && !slot.terminated &&
                            slot.value.size() ==
                                kGuestCallTraceStringByteLimit) {
                            slot.truncated = true;
                        }
                    }
                }
                slots.push_back(std::move(slot));
            }
            return slots;
        };
        event.caller_slots =
            sample_slots(event.caller_ecx, guest_call_trace_slot_offsets);
        if (!event.is_import) {
            event.target_slots = sample_slots(
                event.ecx_entry, guest_call_trace_target_slot_offsets);
        }
        if (has_stack_pointer) {
            event.stack_slots = sample_slots(
                stack_pointer, guest_call_trace_stack_slot_offsets);
            event.string_slots = sample_string_slots(
                stack_pointer, guest_call_trace_string_slot_offsets);
        }
        guest_call_trace_events.push_back(std::move(event));
        return guest_call_trace_events.size() - 1;
    }

    void complete_guest_call_trace(size_t index) {
        if (index >= guest_call_trace_events.size()) return;
        auto& event = guest_call_trace_events[index];
        event.completion_dispatch_count = function_count;
        event.has_eax_return = read_guest_u32(
            "register", kX86EaxRegisterOffset, event.eax_return);
        event.has_edi_return = read_guest_u32(
            "register", kX86EdiRegisterOffset, event.edi_return);
        event.completed = true;
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
            struct ImportCallTraceCompletion {
                Impl* module;
                size_t index;
                ~ImportCallTraceCompletion() {
                    module->complete_guest_call_trace(index);
                }
            } trace_completion{
                this, record_guest_call_trace(static_cast<uint32_t>(target),
                                              name)};
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
            if (name == "KERNEL32.dll!Sleep") return sleep();
            if (name == "KERNEL32.dll!SleepEx") return sleep_ex();
            if (name == "KERNEL32.dll!ExitProcess") return exit_process();
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
            if (name == "KERNEL32.dll!CreateSemaphoreA")
                return create_semaphore_a();
            if (name == "KERNEL32.dll!ReleaseSemaphore")
                return release_semaphore();
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
            if (name == "KERNEL32.dll!DeleteFileA")
                return delete_file_a();
            if (name == "KERNEL32.dll!GetFileSize")
                return get_file_size();
            if (name == "KERNEL32.dll!ReadFile")
                return read_file();
            if (name == "KERNEL32.dll!ReadFileEx")
                return read_file_ex();
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
            if (name == "KERNEL32.dll!LoadLibraryA")
                return load_library_a();
            if (name == "KERNEL32.dll!GetModuleHandleA")
                return get_module_handle_a();
            if (name == "KERNEL32.dll!GetCurrentDirectoryA")
                return get_current_directory_a();
            if (name == "KERNEL32.dll!SetCurrentDirectoryA")
                return set_current_directory_a();
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
            if (name == "KERNEL32.dll!OutputDebugStringA")
                return output_debug_string_a();
            if (name == "USER32.dll!GetDesktopWindow")
                return return_kernel32_dword(
                    kGuestDesktopWindowHandle,
                    "USER32.dll!GetDesktopWindow");
            if (name == "USER32.dll!LoadIconW") return load_icon_w();
            if (name == "USER32.dll!RegisterClassExW")
                return register_class_ex_w();
            if (name == "USER32.dll!CreateWindowExW")
                return create_window_ex_w();
            if (name == "USER32.dll!ClipCursor") return clip_cursor();
            if (name == "USER32.dll!ShowWindow") return show_window();
            if (name == "USER32.dll!PeekMessageW") return peek_message_w();
            if (name == "USER32.dll!SystemParametersInfoA")
                return system_parameters_info_a();
            if (name == "GDI32.dll!CreateDCA") return create_dca();
            if (name == "GDI32.dll!DeleteDC") return delete_dc();
            if (name == "GDI32.dll!ExtEscape") return ext_escape();
            if (name == "GDI32.dll!GetStockObject")
                return get_stock_object();
            if (name == "SHELL32.dll!SHGetFolderPathA" ||
                name == "shell32.dll!SHGetFolderPathA")
                return sh_get_folder_path_a();
            if (name == "SHELL32.dll!SHCreateDirectoryExA" ||
                name == "shell32.dll!SHCreateDirectoryExA")
                return sh_create_directory_ex_a();
            if (name == "d3d9.dll!Direct3DCreate9")
                return direct3d_create9();
            if (name == "d3d9.dll!D3DPERF_BeginEvent")
                return d3dperf_begin_event();
            if (name == "d3d9.dll!D3DPERF_EndEvent")
                return d3dperf_end_event();
            if (name == "d3d9.dll!IDirect3D9::AddRef")
                return d3d9_add_ref();
            if (name == "d3d9.dll!IDirect3D9::Release")
                return d3d9_release();
            if (name == "d3d9.dll!IDirect3D9::GetAdapterCount")
                return d3d9_get_adapter_count();
            if (name == "d3d9.dll!IDirect3D9::CheckDeviceType")
                return d3d9_check_device_type();
            if (name == "d3d9.dll!IDirect3D9::GetAdapterModeCount")
                return d3d9_get_adapter_mode_count();
            if (name == "d3d9.dll!IDirect3D9::CheckDeviceFormat")
                return d3d9_check_device_format();
            if (name == "d3d9.dll!IDirect3D9::CheckDepthStencilMatch")
                return d3d9_check_depth_stencil_match();
            if (name == "d3d9.dll!IDirect3D9::EnumAdapterModes")
                return d3d9_enum_adapter_modes();
            if (name == "d3d9.dll!IDirect3D9::CheckDeviceMultiSampleType")
                return d3d9_check_device_multisample_type();
            if (name == "d3d9.dll!IDirect3D9::GetAdapterDisplayMode")
                return d3d9_get_adapter_display_mode();
            if (name == "d3d9.dll!IDirect3D9::GetAdapterIdentifier")
                return d3d9_get_adapter_identifier();
            if (name == "d3d9.dll!IDirect3D9::GetDeviceCaps")
                return d3d9_get_device_caps();
            if (name == "d3d9.dll!IDirect3D9::CreateDevice")
                return d3d9_create_device();
            if (name == "d3d9.dll!IDirect3DDevice9::AddRef")
                return d3d9_device_add_ref();
            if (name == "d3d9.dll!IDirect3DDevice9::Release")
                return d3d9_device_release();
            if (name == "d3d9.dll!IDirect3DDevice9::GetDeviceCaps")
                return d3d9_device_get_caps();
            if (name == "d3d9.dll!IDirect3DDevice9::GetNumberOfSwapChains")
                return d3d9_device_get_number_of_swap_chains();
            if (name == "d3d9.dll!IDirect3DDevice9::SetPixelShader")
                return d3d9_device_set_shader(true);
            if (name == "d3d9.dll!IDirect3DDevice9::SetVertexShader")
                return d3d9_device_set_shader(false);
            if (name == "d3d9.dll!IDirect3DDevice9::GetTexture")
                return d3d9_device_get_texture();
            if (name == "d3d9.dll!IDirect3DDevice9::GetRenderTarget")
                return d3d9_device_get_render_target();
            if (name == "d3d9.dll!IDirect3DDevice9::SetRenderTarget")
                return d3d9_device_set_render_target();
            if (name == "d3d9.dll!IDirect3DDevice9::SetDepthStencilSurface")
                return d3d9_device_set_depth_stencil_surface();
            if (name == "d3d9.dll!IDirect3DDevice9::BeginScene")
                return d3d9_device_begin_scene();
            if (name == "d3d9.dll!IDirect3DDevice9::EndScene")
                return d3d9_device_end_scene();
            if (name == "d3d9.dll!IDirect3DDevice9::GetBackBuffer")
                return d3d9_device_get_back_buffer();
            if (name == "d3d9.dll!IDirect3DDevice9::GetDepthStencilSurface")
                return d3d9_device_get_depth_stencil_surface();
            if (name == "d3d9.dll!IDirect3DDevice9::SetViewport")
                return d3d9_device_set_viewport();
            if (name == "d3d9.dll!IDirect3DDevice9::GetViewport")
                return d3d9_device_get_viewport();
            if (name == "d3d9.dll!IDirect3DDevice9::GetGammaRamp")
                return d3d9_device_get_gamma_ramp();
            if (name == "d3d9.dll!IDirect3DDevice9::Present")
                return d3d9_device_present();
            if (name == "d3d9.dll!IDirect3DDevice9::SetSamplerState")
                return d3d9_device_set_sampler_state();
            if (name == "d3d9.dll!IDirect3DDevice9::SetRenderState")
                return d3d9_device_set_render_state();
            if (name == "d3d9.dll!IDirect3DDevice9::GetRenderState")
                return d3d9_device_get_render_state();
            if (name == "d3d9.dll!IDirect3DSurface9::AddRef")
                return d3d9_surface_add_ref();
            if (name == "d3d9.dll!IDirect3DSurface9::Release")
                return d3d9_surface_release();
            if (name == "d3d9.dll!IDirect3DSurface9::GetDesc")
                return d3d9_surface_get_desc();
            if (name == "d3d9.dll!IDirect3DDevice9::Clear")
                return d3d9_device_clear();
            if (name == "d3d9.dll!IDirect3DDevice9::CreateVertexBuffer")
                return d3d9_device_create_vertex_buffer();
            if (name == "d3d9.dll!IDirect3DVertexBuffer9::AddRef")
                return d3d9_vertex_buffer_add_ref();
            if (name == "d3d9.dll!IDirect3DVertexBuffer9::Release")
                return d3d9_vertex_buffer_release();
            if (name == "d3d9.dll!IDirect3DVertexBuffer9::GetDevice")
                return d3d9_vertex_buffer_get_device();
            if (name == "d3d9.dll!IDirect3DVertexBuffer9::Lock")
                return d3d9_vertex_buffer_lock();
            if (name == "d3d9.dll!IDirect3DVertexBuffer9::Unlock")
                return d3d9_vertex_buffer_unlock();
            if (name == "d3d9.dll!IDirect3DVertexBuffer9::GetDesc")
                return d3d9_vertex_buffer_get_desc();
            if (name == "d3d9.dll!IDirect3DTexture9::AddRef")
                return d3d9_texture_add_ref();
            if (name == "d3d9.dll!IDirect3DTexture9::Release")
                return d3d9_texture_release();
            if (name == "d3d9.dll!IDirect3DTexture9::GetDevice")
                return d3d9_texture_get_device();
            if (name == "d3d9.dll!IDirect3DTexture9::GetLevelCount")
                return d3d9_texture_get_level_count();
            if (name == "d3d9.dll!IDirect3DTexture9::GetLevelDesc")
                return d3d9_texture_get_level_desc();
            if (name == "d3dx9_41.dll!D3DXCreateTexture")
                return d3dx_create_texture();
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
            if (!guest_last_load_library_name.empty()) {
                char module_result[80]{};
                std::snprintf(
                    module_result, sizeof(module_result),
                    "; last LoadLibraryA(\"%s\") returned 0x%08x (error %u)",
                    guest_last_load_library_name.c_str(),
                    guest_last_load_library_handle,
                    guest_last_load_library_error);
                error += module_result;
            }
            if (!active_guest_functions.empty()) {
                char address[48]{};
                std::snprintf(address, sizeof(address),
                              " called from 0x%08x",
                              active_guest_functions.back());
                error += address;
            }
            uint32_t esp = 0;
            if (read_guest_u32("register", kX86EspRegisterOffset, esp)) {
                uint32_t return_address = 0;
                if (read_guest_u32("ram", esp, return_address)) {
                    char call_site[48]{};
                    std::snprintf(call_site, sizeof(call_site),
                                  " return_address=0x%08x", return_address);
                    error += call_site;
                }
                if (imported->second ==
                    "d3dx9_41.dll!D3DXCreateTexture") {
                    uint32_t device_address = 0;
                    if (read_guest_u32("ram",
                                       static_cast<uint64_t>(esp) + 4,
                                       device_address)) {
                        const auto runtime_device =
                            guest_d3d9_devices.find(device_address);
                        char device_info[112]{};
                        std::snprintf(
                            device_info, sizeof(device_info),
                            " d3dx_device=0x%08x runtime_device=%s",
                            device_address,
                            runtime_device == guest_d3d9_devices.end()
                                ? "no"
                                : "yes");
                        error += device_info;
                        if (runtime_device != guest_d3d9_devices.end()) {
                            char vtable[32]{};
                            std::snprintf(vtable, sizeof(vtable),
                                          " runtime_vtable=0x%08x",
                                          runtime_device->second.vtable_address);
                            error += vtable;
                        }
                        error += " guest_words=[";
                        if (valid_guest_pointer(
                                device_address, 4 * sizeof(uint32_t))) {
                            for (uint32_t index = 0; index < 4; ++index) {
                                uint32_t word = 0;
                                if (!read_guest_u32(
                                        "ram",
                                        static_cast<uint64_t>(device_address) +
                                            index * sizeof(uint32_t),
                                        word)) {
                                    break;
                                }
                                char value[16]{};
                                std::snprintf(
                                    value, sizeof(value), "%s0x%08x",
                                    index == 0 ? "" : ",", word);
                                error += value;
                            }
                        }
                        error += "] runtime_devices=[";
                        size_t listed_devices = 0;
                        for (const auto& [address, device] :
                             guest_d3d9_devices) {
                            if (listed_devices == 8) break;
                            char value[40]{};
                            std::snprintf(value, sizeof(value),
                                          "%s0x%08x/0x%08x",
                                          listed_devices == 0 ? "" : ",",
                                          address, device.vtable_address);
                            error += value;
                            ++listed_devices;
                        }
                        error += "]";
                    }
                }
                error += " args=[";
                for (uint32_t index = 0; index < 8; ++index) {
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
            const size_t unresolved_trace_index =
                record_guest_call_trace(static_cast<uint32_t>(target));
            int thunk_result = -1;
            if (dispatch_tls_alloc_wrapper(static_cast<uint32_t>(target),
                                           thunk_result)) {
                complete_guest_call_trace(unresolved_trace_index);
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
        GuestRegisterSnapshot entry_registers{};
        (void)read_guest_u32("register", kX86EaxRegisterOffset,
                             entry_registers.eax);
        (void)read_guest_u32("register", kX86EcxRegisterOffset,
                             entry_registers.ecx);
        (void)read_guest_u32("register", kX86EdxRegisterOffset,
                             entry_registers.edx);
        (void)read_guest_u32("register", kX86EbxRegisterOffset,
                             entry_registers.ebx);
        (void)read_guest_u32("register", kX86EspRegisterOffset,
                             entry_registers.esp);
        (void)read_guest_u32("register", kX86EbpRegisterOffset,
                             entry_registers.ebp);
        (void)read_guest_u32("register", kX86EsiRegisterOffset,
                             entry_registers.esi);
        (void)read_guest_u32("register", kX86EdiRegisterOffset,
                             entry_registers.edi);
        const bool inside_ui_state_gate =
            ui_state_gate_trace_enabled &&
            std::find(active_guest_functions.begin(),
                      active_guest_functions.end(),
                      kRetailUiStateGateAddress) !=
                active_guest_functions.end();
        const bool trace_ui_state_gate_call =
            ui_state_gate_trace_enabled &&
            (target == kRetailUiStateGateAddress || inside_ui_state_gate);
        size_t ui_state_gate_trace_index =
            std::numeric_limits<size_t>::max();
        if (trace_ui_state_gate_call) {
            if (ui_state_gate_trace_events.size() <
                kRetailUiStateGateTraceLimit) {
                RecompiledUiStateGateTraceEvent event{};
                event.dispatch_count = function_count;
                event.thread_id = current_guest_thread_id;
                event.function = static_cast<uint32_t>(target);
                event.caller = active_guest_functions.empty()
                                   ? 0
                                   : active_guest_functions.back();
                event.ecx_entry = entry_registers.ecx;
                event.eax_entry = entry_registers.eax;
                event.esp_entry = entry_registers.esp;
                if (target == kRetailUiStateGateAddress) {
                    const uint64_t gate_state_address =
                        static_cast<uint64_t>(entry_registers.ecx) + 0x34;
                    event.has_gate_state_word = read_guest_diagnostic_u32(
                        gate_state_address, event.gate_state_word);
                    if (gate_state_address <= UINT32_MAX) {
                        const auto last_writer = guest_last_writers.find(
                            static_cast<uint32_t>(gate_state_address) &
                            ~UINT32_C(3));
                        if (last_writer != guest_last_writers.end()) {
                            const auto& provenance = last_writer->second;
                            event.has_gate_state_last_writer = true;
                            event.gate_state_last_writer_sequence =
                                provenance.sequence;
                            event.gate_state_last_writer_dispatch_count =
                                provenance.dispatch_count;
                            event.gate_state_last_writer_function =
                                provenance.writer_function;
                            event.gate_state_last_writer_ecx =
                                provenance.writer_ecx;
                            event.has_gate_state_last_writer_ecx =
                                provenance.has_writer_ecx;
                            event.gate_state_last_writer_caller_function =
                                provenance.writer_caller_function;
                            event.has_gate_state_last_writer_caller_function =
                                provenance.has_writer_caller_function;
                            event.gate_state_last_writer_call_return_address =
                                provenance.writer_call_return_address;
                            event.has_gate_state_last_writer_call_return_address =
                                provenance.has_writer_call_return_address;
                            event.gate_state_last_writer_caller_return_address =
                                provenance.writer_caller_return_address;
                            event.has_gate_state_last_writer_caller_return_address =
                                provenance.has_writer_caller_return_address;
                            event.gate_state_last_writer_ancestor_function =
                                provenance.writer_ancestor_function;
                            event.has_gate_state_last_writer_ancestor_function =
                                provenance.has_writer_ancestor_function;
                            event.gate_state_last_writer_ancestor_caller_function =
                                provenance.writer_ancestor_caller_function;
                            event.has_gate_state_last_writer_ancestor_caller_function =
                                provenance.has_writer_ancestor_caller_function;
                            event.gate_state_last_writer_ancestor_return_address =
                                provenance.writer_ancestor_return_address;
                            event.has_gate_state_last_writer_ancestor_return_address =
                                provenance.has_writer_ancestor_return_address;
                            event.gate_state_last_writer_thread_id =
                                provenance.thread_id;
                            event.gate_state_last_writer_address =
                                provenance.write_address;
                            event.gate_state_last_writer_size =
                                provenance.write_size;
                            event.gate_state_last_writer_word_value =
                                provenance.word_value;
                        }
                    }
                    uint32_t callback_vtable = 0;
                    event.has_gate_callback_object =
                        read_guest_diagnostic_u32(
                            static_cast<uint64_t>(entry_registers.ecx) + 0x48,
                            event.gate_callback_object);
                    event.has_callback_target =
                        event.has_gate_callback_object &&
                        event.gate_callback_object != 0 &&
                        read_guest_diagnostic_u32(event.gate_callback_object,
                                                  callback_vtable) &&
                        callback_vtable != 0 &&
                        read_guest_diagnostic_u32(
                            static_cast<uint64_t>(callback_vtable) + 0x24c,
                            event.callback_target);
                } else if (target == kRetailUiStateGateHelperAddress) {
                    const uint64_t helper_flag_address =
                        static_cast<uint64_t>(entry_registers.ecx) + 0x0c;
                    event.has_helper_flag_byte = read_guest_diagnostic_u8(
                        helper_flag_address,
                        event.helper_flag_byte);
                    if (helper_flag_address <= UINT32_MAX) {
                        const GuestWriteProvenance* last_writer = nullptr;
                        const auto target_last_writer =
                            guest_target_last_writers.find(
                                static_cast<uint32_t>(helper_flag_address));
                        if (target_last_writer !=
                            guest_target_last_writers.end()) {
                            last_writer = &target_last_writer->second;
                        } else if (guest_write_provenance_all()) {
                            const auto word_writer = guest_last_writers.find(
                                static_cast<uint32_t>(helper_flag_address) &
                                ~UINT32_C(3));
                            if (word_writer != guest_last_writers.end() &&
                                word_writer->second.write_address <=
                                    helper_flag_address &&
                                helper_flag_address <
                                    static_cast<uint64_t>(
                                        word_writer->second.write_address) +
                                        word_writer->second.write_size) {
                                last_writer = &word_writer->second;
                            }
                        }
                        if (last_writer != nullptr) {
                            const auto& provenance = *last_writer;
                            auto& trace = event.helper_flag_last_writer;
                            event.has_helper_flag_last_writer = true;
                            trace.sequence = provenance.sequence;
                            trace.dispatch_count = provenance.dispatch_count;
                            trace.function = provenance.writer_function;
                            trace.ecx_entry = provenance.writer_ecx;
                            trace.has_ecx_entry = provenance.has_writer_ecx;
                            trace.caller_function =
                                provenance.writer_caller_function;
                            trace.has_caller_function =
                                provenance.has_writer_caller_function;
                            trace.call_return_address =
                                provenance.writer_call_return_address;
                            trace.has_call_return_address =
                                provenance.has_writer_call_return_address;
                            trace.caller_return_address =
                                provenance.writer_caller_return_address;
                            trace.has_caller_return_address =
                                provenance.has_writer_caller_return_address;
                            trace.thread_id = provenance.thread_id;
                            trace.write_address = provenance.write_address;
                            trace.write_size = provenance.write_size;
                            trace.word_value = provenance.word_value;
                        }
                    }
                    uint32_t helper_vtable = 0;
                    event.has_callback_target =
                        read_guest_diagnostic_u32(entry_registers.ecx,
                                                  helper_vtable) &&
                        helper_vtable != 0 &&
                        read_guest_diagnostic_u32(
                            static_cast<uint64_t>(helper_vtable) + 4,
                            event.callback_target);
                }
                ui_state_gate_trace_index =
                    ui_state_gate_trace_events.size();
                ui_state_gate_trace_events.push_back(event);
            } else {
                ui_state_gate_trace_truncated = true;
            }
        }
        const size_t guest_call_trace_index =
            record_guest_call_trace(static_cast<uint32_t>(target));
        const char* trace_allocations =
            std::getenv("SHIFT_TRACE_GUEST_ALLOCATIONS");
        if (trace_allocations && *trace_allocations &&
            entry_registers.esp <= UINT32_MAX - 16) {
            (void)read_guest_diagnostic_u32(
                entry_registers.esp, entry_registers.stack_return_slot);
            entry_registers.has_stack_arguments = true;
            for (size_t argument_index = 0;
                 argument_index < entry_registers.stack_arguments.size();
                 ++argument_index) {
                const uint64_t argument_address =
                    static_cast<uint64_t>(entry_registers.esp) + 4 +
                    argument_index * sizeof(uint32_t);
                if (!read_guest_diagnostic_u32(
                        argument_address,
                        entry_registers.stack_arguments[argument_index])) {
                    entry_registers.has_stack_arguments = false;
                    break;
                }
                const uint32_t pointer =
                    entry_registers.stack_arguments[argument_index];
                if (!diagnostic_guest_pointer_mapped(pointer, 16)) continue;
                bool complete_snapshot = true;
                for (size_t word_index = 0;
                     word_index <
                     entry_registers.stack_argument_memory[argument_index]
                         .size();
                     ++word_index) {
                    const uint64_t word_address =
                        static_cast<uint64_t>(pointer) +
                        word_index * sizeof(uint32_t);
                    if (!read_guest_diagnostic_u32(
                            word_address,
                            entry_registers
                                .stack_argument_memory[argument_index]
                                     [word_index])) {
                        complete_snapshot = false;
                        break;
                    }
                }
                entry_registers.has_stack_argument_memory[argument_index] =
                    complete_snapshot;
            }
            if (diagnostic_guest_pointer_mapped(
                    entry_registers.ecx, kGuestAllocationObjectTraceSize)) {
                entry_registers.has_ecx_object_memory = true;
                for (size_t word_index = 0;
                     word_index < entry_registers.ecx_object_memory.size();
                     ++word_index) {
                    const uint64_t word_address =
                        static_cast<uint64_t>(entry_registers.ecx) +
                        word_index * sizeof(uint32_t);
                    if (!read_guest_diagnostic_u32(
                            word_address,
                            entry_registers.ecx_object_memory[word_index])) {
                        entry_registers.has_ecx_object_memory = false;
                        break;
                    }
                }
                if (entry_registers.has_ecx_object_memory) {
                    for (const uint32_t pointer :
                         entry_registers.ecx_object_memory) {
                        if (entry_registers.ecx_object_link_count >=
                            entry_registers.ecx_object_links.size()) {
                            break;
                        }
                        if (!diagnostic_guest_pointer_mapped(pointer, 16))
                            continue;
                        bool duplicate = false;
                        for (size_t link_index = 0;
                             link_index <
                             entry_registers.ecx_object_link_count;
                             ++link_index) {
                            if (entry_registers.ecx_object_links[link_index]
                                    .address == pointer) {
                                duplicate = true;
                                break;
                            }
                        }
                        if (duplicate) continue;
                        auto& link = entry_registers.ecx_object_links[
                            entry_registers.ecx_object_link_count];
                        link.address = pointer;
                        bool complete_snapshot = true;
                        for (size_t word_index = 0;
                             word_index < link.memory.size(); ++word_index) {
                            const uint64_t word_address =
                                static_cast<uint64_t>(pointer) +
                                word_index * sizeof(uint32_t);
                            if (!read_guest_diagnostic_u32(
                                    word_address, link.memory[word_index])) {
                                complete_snapshot = false;
                                break;
                            }
                        }
                        if (complete_snapshot)
                            ++entry_registers.ecx_object_link_count;
                    }
                    // The allocator follows linked pool records through the
                    // dword at +0x10. Snapshot that bounded chain without
                    // interpreting the other record fields.
                    const auto add_chain_link = [&](uint32_t parent_address,
                                                    uint32_t pointer) {
                        if (entry_registers.ecx_object_chain_link_count >=
                                entry_registers.ecx_object_chain_links.size() ||
                            !diagnostic_guest_pointer_mapped(pointer, 24)) {
                            return;
                        }
                        for (size_t direct_index = 0;
                             direct_index <
                             entry_registers.ecx_object_link_count;
                             ++direct_index) {
                            if (entry_registers.ecx_object_links[direct_index]
                                    .address == pointer) {
                                return;
                            }
                        }
                        for (size_t chain_index = 0;
                             chain_index <
                             entry_registers.ecx_object_chain_link_count;
                             ++chain_index) {
                            if (entry_registers.ecx_object_chain_links
                                    [chain_index]
                                    .address == pointer) {
                                return;
                            }
                        }
                        auto& link = entry_registers.ecx_object_chain_links[
                            entry_registers.ecx_object_chain_link_count];
                        link.address = pointer;
                        link.parent_address = parent_address;
                        for (size_t word_index = 0;
                             word_index < link.memory.size(); ++word_index) {
                            const uint64_t word_address =
                                static_cast<uint64_t>(pointer) +
                                word_index * sizeof(uint32_t);
                            if (!read_guest_diagnostic_u32(
                                    word_address, link.memory[word_index])) {
                                return;
                            }
                        }
                        ++entry_registers.ecx_object_chain_link_count;
                    };
                    for (size_t link_index = 0;
                         link_index < entry_registers.ecx_object_link_count;
                         ++link_index) {
                        const auto& parent =
                            entry_registers.ecx_object_links[link_index];
                        add_chain_link(
                            parent.address,
                            parent.memory[
                                kGuestAllocationLinkNextPointerWordIndex]);
                    }
                    for (size_t link_index = 0;
                         link_index <
                         entry_registers.ecx_object_chain_link_count;
                         ++link_index) {
                        const auto& parent =
                            entry_registers.ecx_object_chain_links[link_index];
                        add_chain_link(
                            parent.address,
                            parent.memory[
                                kGuestAllocationLinkNextPointerWordIndex]);
                    }
                }
            }
        }
        size_t pool_attempt_index = kGuestAllocationPoolAttemptLimit;
        const bool pool_allocation_target =
            target == kRetailPoolAllocateFunctionAddress ||
            target == kRetailPoolTryAllocateFunctionAddress;
        if (trace_allocations && *trace_allocations &&
            entry_registers.has_ecx_object_memory &&
            pool_allocation_target) {
            pool_attempt_index = guest_pool_allocation_attempt_cursor;
            guest_pool_allocation_attempt_cursor =
                (guest_pool_allocation_attempt_cursor + 1) %
                guest_pool_allocation_attempts.size();
            guest_pool_allocation_attempt_count = std::min(
                guest_pool_allocation_attempt_count + 1,
                guest_pool_allocation_attempts.size());
            auto& attempt =
                guest_pool_allocation_attempts[pool_attempt_index];
            attempt = {};
            attempt.sequence = ++guest_pool_allocation_attempts_seen;
            attempt.function_address = static_cast<uint32_t>(target);
            attempt.return_address = entry_registers.stack_return_slot;
            attempt.pool_address = entry_registers.ecx;
            attempt.pool_flags =
                entry_registers.ecx_object_memory[0x110 / 4];
            attempt.pool_threshold =
                entry_registers.ecx_object_memory[0x12c / 4];
            attempt.list_head_100 =
                entry_registers.ecx_object_memory[0x100 / 4];
            attempt.list_head_104 =
                entry_registers.ecx_object_memory[0x104 / 4];
            if (target == kRetailPoolAllocateFunctionAddress) {
                attempt.request_size = entry_registers.edx;
                if (entry_registers.has_stack_arguments)
                    attempt.request_flags =
                        entry_registers.stack_arguments[0];
            } else if (entry_registers.has_stack_arguments) {
                attempt.request_size =
                    entry_registers.stack_arguments[0];
                attempt.request_flags =
                    entry_registers.stack_arguments[1];
            }
            const std::string pool_name = read_diagnostic_guest_ascii(
                entry_registers.ecx + 0x30);
            std::snprintf(attempt.pool_name.data(),
                          attempt.pool_name.size(), "%s", pool_name.c_str());
            if (attempt.request_size >= kGuestAllocationTraceThreshold) {
                const bool use_list_104 =
                    (attempt.request_flags & 0x80) != 0;
                attempt.selected_list_head =
                    use_list_104 ? attempt.list_head_104
                                 : attempt.list_head_100;
                attempt.selected_list_next_offset =
                    use_list_104 ? 0x10 : 0x14;
                const size_t next_word_index =
                    attempt.selected_list_next_offset / sizeof(uint32_t);
                uint32_t parent_address = 0;
                uint32_t node_address = attempt.selected_list_head;
                while (attempt.selected_list_node_count <
                       attempt.selected_list_nodes.size()) {
                    if (node_address == 0) {
                        attempt.selected_list_terminated = true;
                        break;
                    }
                    if (!diagnostic_guest_pointer_mapped(node_address, 24)) {
                        attempt.selected_list_truncated = true;
                        break;
                    }
                    bool duplicate = false;
                    for (size_t node_index = 0;
                         node_index <
                         attempt.selected_list_node_count;
                         ++node_index) {
                        if (attempt.selected_list_nodes[node_index].address ==
                            node_address) {
                            duplicate = true;
                            break;
                        }
                    }
                    if (duplicate) {
                        attempt.selected_list_cycle = true;
                        break;
                    }
                    auto& node = attempt.selected_list_nodes[
                        attempt.selected_list_node_count];
                    node.address = node_address;
                    node.parent_address = parent_address;
                    bool complete_snapshot = true;
                    for (size_t word_index = 0;
                         word_index < node.memory.size(); ++word_index) {
                        const uint64_t word_address =
                            static_cast<uint64_t>(node_address) +
                            word_index * sizeof(uint32_t);
                        if (!read_guest_diagnostic_u32(
                                word_address, node.memory[word_index])) {
                            complete_snapshot = false;
                            break;
                        }
                    }
                    if (!complete_snapshot) {
                        attempt.selected_list_truncated = true;
                        break;
                    }
                    ++attempt.selected_list_node_count;
                    const uint32_t next_address = node.memory[next_word_index];
                    if (next_address == 0) {
                        attempt.selected_list_terminated = true;
                        break;
                    }
                    parent_address = node_address;
                    node_address = next_address;
                }
                if (!attempt.selected_list_terminated &&
                    !attempt.selected_list_truncated &&
                    !attempt.selected_list_cycle &&
                    attempt.selected_list_node_count ==
                        attempt.selected_list_nodes.size()) {
                    attempt.selected_list_truncated = true;
                }
            }
        }
        if (scheduler_context_active) {
            GuestThread* thread =
                guest_execution_state(current_guest_thread_handle);
            if (thread) {
                if (thread->recent_functions.size() ==
                    kGuestFunctionHistoryLimit) {
                    thread->recent_functions.pop_front();
                }
                thread->recent_functions.push_back(
                    static_cast<uint32_t>(target));
            }
        }
        active_guest_functions.push_back(static_cast<uint32_t>(target));
        active_guest_function_registers.push_back(entry_registers);
        int result = 0;
        uint32_t pool_list_head = 0;
        uint32_t pool_element_size = 0;
        uint32_t pool_element_count = 0;
        uint32_t pool_element_type = 0;
        const bool repair_empty_retail_pool =
            target == kRetailPoolInitializerAddress &&
            diagnostic_guest_pointer_mapped(entry_registers.ecx, 0x20) &&
            read_guest_diagnostic_u32(entry_registers.ecx,
                                      pool_list_head) &&
            read_guest_diagnostic_u32(
                static_cast<uint64_t>(entry_registers.ecx) + 4,
                pool_element_size) &&
            read_guest_diagnostic_u32(
                static_cast<uint64_t>(entry_registers.ecx) + 8,
                pool_element_count) &&
            read_guest_diagnostic_u32(
                static_cast<uint64_t>(entry_registers.ecx) + 0x1c,
                pool_element_type) &&
            pool_list_head == 0 && pool_element_size == 0x10 &&
            pool_element_count == 0x10;
        if (repair_empty_retail_pool) {
            const auto saved_registers = registers;
            const uint32_t nested_esp = entry_registers.esp - 16;
            const std::array<uint32_t, 4> helper_stack = {
                kRetailPoolInitReturnAddress,
                pool_element_count,
                0x1f,
                pool_element_type};
            bool frame_ready = entry_registers.esp >=
                                   kGuestMinimumUserAddress + 16;
            for (size_t index = 0; frame_ready && index < helper_stack.size();
                 ++index) {
                frame_ready = write_guest_u32(
                    "ram", static_cast<uint64_t>(nested_esp) + index * 4,
                    helper_stack[index]);
            }
            if (frame_ready) {
                frame_ready = write_guest_u32(
                                  "register", kX86EcxRegisterOffset,
                                  entry_registers.ecx) &&
                              write_guest_u32(
                                  "register", kX86EdxRegisterOffset,
                                  pool_element_size) &&
                              write_guest_u32("register", kX86EspRegisterOffset,
                                              nested_esp);
            }
            if (!frame_ready) {
                const std::string cause = error;
                error = "could not prepare retail pool list initializer: " +
                        cause;
                result = -1;
            } else {
                error.clear();
                const int helper_result =
                    dispatch(kRetailPoolListInitHelperAddress);
                const std::string helper_error = error;
                registers = saved_registers;
                if (helper_result != 0 || !helper_error.empty()) {
                    error = "retail pool list initializer 0x00506ab0 failed: " +
                            helper_error;
                    result = -1;
                } else if (!read_guest_diagnostic_u32(
                               entry_registers.ecx, pool_list_head) ||
                           pool_list_head == 0) {
                    error = "retail pool list initializer 0x00506ab0 left "
                            "the list head empty";
                    result = -1;
                } else {
                    result = function(&context);
                }
            }
        } else {
            result = function(&context);
        }
        if (pool_attempt_index < guest_pool_allocation_attempts.size()) {
            auto& attempt =
                guest_pool_allocation_attempts[pool_attempt_index];
            attempt.has_result_eax = read_guest_u32(
                "register", kX86EaxRegisterOffset, attempt.result_eax);
        }
        if (ui_state_gate_trace_index !=
            std::numeric_limits<size_t>::max()) {
            auto& event = ui_state_gate_trace_events[
                ui_state_gate_trace_index];
            event.completed = read_guest_u32(
                "register", kX86EaxRegisterOffset, event.eax_return);
        }
        if (current_guest_thread_handle != 0 &&
            current_guest_thread_exit_requested) {
            complete_guest_call_trace(guest_call_trace_index);
            active_guest_function_registers.pop_back();
            active_guest_functions.pop_back();
            --call_depth;
            return kGuestThreadExitResult;
        }
        if (result != 0) {
            if (error.empty()) {
                char message[96]{};
                std::snprintf(message, sizeof(message),
                              "P-code function 0x%08x returned %d",
                              static_cast<uint32_t>(target), result);
                error = message;
            }
            append_failure_guest_write_provenance(entry_registers);
            append_guest_stack();
        }
        complete_guest_call_trace(guest_call_trace_index);
        active_guest_function_registers.pop_back();
        active_guest_functions.pop_back();
        --call_depth;
        return result;
    }

    bool guest_write_provenance_enabled() const {
        return guest_write_provenance_enabled_flag;
    }

    bool guest_write_provenance_all() const {
        return guest_write_provenance_all_flag;
    }

    const std::vector<uint32_t>& guest_write_provenance_targets() const {
        return guest_write_provenance_targets_cache;
    }

    void record_guest_write_provenance(uint64_t offset, size_t size) {
        if (!guest_write_provenance_enabled() || !ram || size == 0 ||
            offset > UINT32_MAX) {
            return;
        }
        const auto& targets = guest_write_provenance_targets();
        if (!guest_write_provenance_all() && targets.empty()) return;
        const uint64_t end = offset + size;
        if (end > kGuestRamSize) return;

        const uint64_t first_word = offset & ~UINT64_C(3);
        const uint64_t last_word = (end - 1) & ~UINT64_C(3);
        const uint64_t sequence = ++guest_write_provenance_sequence;
        const uint32_t writer_function =
            active_guest_functions.empty() ? 0 : active_guest_functions.back();

        for (uint64_t word_address = first_word;
             word_address <= last_word; word_address += sizeof(uint32_t)) {
            if (!guest_write_provenance_all() &&
                std::none_of(targets.begin(), targets.end(),
                             [word_address](uint32_t address) {
                                 return (address & ~UINT32_C(3)) ==
                                        word_address;
                             })) {
                continue;
            }
            if (guest_write_provenance_all() &&
                guest_last_writers.size() >=
                    kGuestWriteProvenanceWordLimit &&
                guest_last_writers.find(
                    static_cast<uint32_t>(word_address)) ==
                    guest_last_writers.end()) {
                guest_last_writers.clear();
            }
            uint32_t word_value = 0;
            if (!read_guest_diagnostic_u32(word_address, word_value)) continue;
            GuestWriteProvenance record{};
            record.sequence = sequence;
            record.dispatch_count = function_count;
            record.writer_function = writer_function;
            if (!active_guest_function_registers.empty()) {
                const auto& writer_frame =
                    active_guest_function_registers.back();
                record.writer_ecx = writer_frame.ecx;
                record.has_writer_ecx = true;
                record.has_writer_call_return_address =
                    read_guest_diagnostic_u32(
                        writer_frame.esp, record.writer_call_return_address);
            }
            if (active_guest_functions.size() > 1) {
                const size_t caller_index = active_guest_functions.size() - 2;
                record.writer_caller_function =
                    active_guest_functions[caller_index];
                record.has_writer_caller_function = true;
                if (caller_index < active_guest_function_registers.size()) {
                    record.has_writer_caller_return_address =
                        read_guest_diagnostic_u32(
                            active_guest_function_registers[caller_index].esp,
                            record.writer_caller_return_address);
                }
            }
            if (active_guest_functions.size() > 2) {
                const size_t ancestor_index = active_guest_functions.size() - 3;
                record.writer_ancestor_function =
                    active_guest_functions[ancestor_index];
                record.has_writer_ancestor_function = true;
                if (ancestor_index < active_guest_function_registers.size()) {
                    record.has_writer_ancestor_return_address =
                        read_guest_diagnostic_u32(
                            active_guest_function_registers[ancestor_index].esp,
                            record.writer_ancestor_return_address);
                }
            }
            if (active_guest_functions.size() > 3) {
                record.writer_ancestor_caller_function =
                    active_guest_functions[active_guest_functions.size() - 4];
                record.has_writer_ancestor_caller_function = true;
            }
            record.thread_id = current_guest_thread_id;
            record.write_address = static_cast<uint32_t>(offset);
            record.write_size = static_cast<uint32_t>(size);
            record.word_value = word_value;
            guest_last_writers[static_cast<uint32_t>(word_address)] = record;
            if (!guest_write_provenance_all()) {
                for (const uint32_t target : targets) {
                    if (target < offset || target >= end) continue;
                    if (guest_target_last_writers.size() >=
                            kGuestWriteProvenanceWordLimit &&
                        guest_target_last_writers.find(target) ==
                            guest_target_last_writers.end()) {
                        guest_target_last_writers.clear();
                    }
                    guest_target_last_writers[target] = record;
                }
            }
        }
    }

    void append_guest_write_provenance_address(
        uint32_t address, bool& first_record) {
        const uint32_t word_address = address & ~UINT32_C(3);
        uint32_t current_value = 0;
        const bool current_available =
            read_guest_diagnostic_u32(word_address, current_value);
        const auto found = guest_last_writers.find(word_address);

        char record[320]{};
        if (found == guest_last_writers.end()) {
            std::snprintf(
                record, sizeof(record),
                "%s0x%08x(word=0x%08x,current=%s0x%08x,last_writer=none)",
                first_record ? "" : ",", address, word_address,
                current_available ? "" : "unavailable:",
                current_available ? current_value : 0u);
        } else {
            const auto& provenance = found->second;
            std::snprintf(
                record, sizeof(record),
                "%s0x%08x(word=0x%08x,current=%s0x%08x,"
                "last_writer=0x%08x,thread=0x%08x,dispatch=%llu,"
                "write_seq=%llu,write=0x%08x+%u,word_value=0x%08x)",
                first_record ? "" : ",", address, word_address,
                current_available ? "" : "unavailable:",
                current_available ? current_value : 0u,
                provenance.writer_function, provenance.thread_id,
                static_cast<unsigned long long>(provenance.dispatch_count),
                static_cast<unsigned long long>(provenance.sequence),
                provenance.write_address, provenance.write_size,
                provenance.word_value);
        }
        error += record;
        first_record = false;
    }

    void append_failure_guest_write_provenance(
        const GuestRegisterSnapshot& registers_at_entry) {
        if (!guest_write_provenance_enabled() ||
            error.find("; guest write provenance=[") != std::string::npos) {
            return;
        }

        std::vector<uint32_t> addresses = guest_write_provenance_targets();
        if (addresses.empty() && guest_write_provenance_all()) {
            constexpr size_t kAutomaticAddressLimit = 18;
            const std::array<uint32_t, 3> bases = {
                registers_at_entry.ecx,
                registers_at_entry.esi,
                registers_at_entry.edi,
            };
            for (const uint32_t base : bases) {
                if (base < kGuestMinimumUserAddress ||
                    !diagnostic_guest_pointer_mapped(base, 0x40)) {
                    continue;
                }
                for (uint32_t field_offset = 0;
                     field_offset < 0x40 &&
                     addresses.size() < kAutomaticAddressLimit;
                     field_offset += sizeof(uint32_t)) {
                    const uint32_t address = base + field_offset;
                    if (std::find(addresses.begin(), addresses.end(), address) !=
                        addresses.end()) {
                        continue;
                    }
                    uint32_t current_value = 0;
                    if (!read_guest_diagnostic_u32(address, current_value))
                        continue;
                    if (current_value == 0 ||
                        guest_last_writers.find(address) !=
                            guest_last_writers.end()) {
                        addresses.push_back(address);
                    }
                }
                if (addresses.size() >= kAutomaticAddressLimit) break;
            }
        }

        if (addresses.empty()) return;
        error += "; guest write provenance=[";
        bool first_record = true;
        for (const uint32_t address : addresses)
            append_guest_write_provenance_address(address, first_record);
        error += "]";
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

    bool read_guest_diagnostic_u32(uint64_t offset, uint32_t& value) const {
        if (!ram || offset + sizeof(uint32_t) > kGuestRamSize) return false;
        const auto* bytes = static_cast<const uint8_t*>(ram) + offset;
        value = static_cast<uint32_t>(bytes[0]) |
                (static_cast<uint32_t>(bytes[1]) << 8) |
                (static_cast<uint32_t>(bytes[2]) << 16) |
                (static_cast<uint32_t>(bytes[3]) << 24);
        return true;
    }

    bool read_guest_diagnostic_u8(uint64_t offset, uint8_t& value) const {
        if (!ram || offset >= kGuestRamSize) return false;
        value = static_cast<const uint8_t*>(ram)[offset];
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
        return address >= kGuestMinimumUserAddress &&
               size <= kGuestRamSize - address;
    }

    void trace_guest_allocation(const char* api, uint32_t size,
                                uint32_t address) const {
        const char* enabled = std::getenv("SHIFT_TRACE_GUEST_ALLOCATIONS");
        if (!enabled || !*enabled || size < kGuestAllocationTraceThreshold)
            return;
        const uint32_t guest_pc = active_guest_functions.empty()
                                      ? 0
                                      : active_guest_functions.back();
        std::fprintf(stderr,
                     "shift_runtime: %s size=0x%08x (%u) result=0x%08x "
                     "guest_pc=0x%08x guest_stack=[",
                     api, size, size, address, guest_pc);
        const size_t first = active_guest_functions.size() > 8
                                 ? active_guest_functions.size() - 8
                                 : 0;
        for (size_t index = first;
             index < active_guest_functions.size(); ++index) {
            std::fprintf(stderr, "%s0x%08x", index == first ? "" : " -> ",
                         active_guest_functions[index]);
        }
        std::fputs("]\n", stderr);
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
            "Sleep", "SleepEx", "ExitProcess",
            "GetLocalTime",
            "ConvertThreadToFiber", "IsThreadAFiber",
            "GlobalMemoryStatus",
            "GetSystemTimeAsFileTime", "QueryPerformanceCounter",
            "QueryPerformanceFrequency", "GetStartupInfoA", "GetProcessHeap",
            "CreateMutexA", "CreateSemaphoreA", "ReleaseSemaphore",
            "WaitForSingleObject", "ReleaseMutex",
            "WaitForSingleObjectEx", "CreateEventW", "CreateEventA",
            "SetEvent", "ResetEvent",
            "InterlockedCompareExchange",
            "InterlockedExchange",
            "VirtualAlloc", "VirtualFree",
            "CloseHandle",
            "CreateFileA", "DeleteFileA", "GetFileSize", "ReadFile",
            "ReadFileEx",
            "HeapCreate", "HeapAlloc", "HeapReAlloc", "HeapSize", "HeapFree", "GetVersionExA",
            "SetUnhandledExceptionFilter", "LoadLibraryA", "GetModuleHandleA",
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
            "GetCurrentDirectoryA", "SetCurrentDirectoryA",
            "FreeEnvironmentStrings", "FreeEnvironmentStringsA",
            "FreeEnvironmentStringsW", "WideCharToMultiByte", "GetLastError",
            "SetLastError", "RaiseException", "GetACP", "IsValidCodePage", "GetCPInfo",
            "GetStringTypeW", "MultiByteToWideChar", "LCMapStringW",
            "OutputDebugStringA"};
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

    int sleep() {
        constexpr const char* api = "KERNEL32.dll!Sleep";
        uint32_t milliseconds = 0;
        if (!read_stack_argument(0, milliseconds, api)) return -1;
        return sleep_guest_thread(milliseconds, false, api, sizeof(uint32_t));
    }

    int sleep_ex() {
        constexpr const char* api = "KERNEL32.dll!SleepEx";
        uint32_t milliseconds = 0;
        uint32_t alertable = 0;
        if (!read_stack_argument(0, milliseconds, api) ||
            !read_stack_argument(1, alertable, api)) {
            return -1;
        }
        return sleep_guest_thread(milliseconds, alertable != 0, api,
                                  2 * sizeof(uint32_t));
    }

    int sleep_guest_thread(uint32_t milliseconds, bool alertable,
                           const char* api, uint32_t stack_cleanup) {
        if (alertable) {
            bool dispatched = false;
            if (!dispatch_pending_io_completions(dispatched)) return -1;
            if (dispatched)
                return return_kernel32_dword(0x000000c0, api,
                                             stack_cleanup);
        }
        if (scheduler_context_active && guest_coroutine_active) {
            GuestThread* thread =
                guest_execution_state(current_guest_thread_handle);
            if (!thread) {
                error = std::string(api) + " has no current guest thread state";
                return -1;
            }
            if (milliseconds == 0) {
                if (!yield_current_guest_thread(true)) return -1;
            } else {
                thread->waiting = true;
                thread->runnable = false;
                thread->wait_handle = 0;
                thread->wait_result = 0;
                thread->wait_sequence = next_guest_wait_sequence++;
                thread->wait_alertable = alertable;
                thread->wait_deadline = milliseconds == UINT32_MAX
                    ? std::chrono::steady_clock::time_point::max()
                    : std::chrono::steady_clock::now() +
                          std::chrono::milliseconds(milliseconds);
                if (!yield_current_guest_thread(false)) return -1;
            }
        } else if (milliseconds == UINT32_MAX) {
            error = std::string(api) +
                    " with INFINITE requires the cooperative guest scheduler";
            return -1;
        } else if (milliseconds == 0) {
            std::this_thread::yield();
        } else {
            std::this_thread::sleep_for(
                std::chrono::milliseconds(milliseconds));
        }
        return return_kernel32_dword(0, api, stack_cleanup);
    }

    int exit_process() {
        constexpr const char* api = "KERNEL32.dll!ExitProcess";
        uint32_t exit_code = 0;
        if (!read_stack_argument(0, exit_code, api)) return -1;
        error = std::string(api) + " terminated the guest process with code " +
                std::to_string(exit_code);
        const char* trace_allocations =
            std::getenv("SHIFT_TRACE_GUEST_ALLOCATIONS");
        const bool trace_allocation_context =
            trace_allocations && *trace_allocations;
        uint32_t guest_edi = 0;
        if (read_guest_u32("register", kX86EdiRegisterOffset, guest_edi)) {
            char register_value[64]{};
            std::snprintf(register_value, sizeof(register_value),
                          "; guest EDI=0x%08x (%u)", guest_edi, guest_edi);
            error += register_value;
        }
        if (!active_guest_functions.empty()) {
            error += "; guest call stack=";
            const size_t first = active_guest_functions.size() > 32
                                     ? active_guest_functions.size() - 32
                                     : 0;
            for (size_t index = first;
                 index < active_guest_functions.size(); ++index) {
                char address[256]{};
                const GuestRegisterSnapshot registers =
                    index < active_guest_function_registers.size()
                        ? active_guest_function_registers[index]
                        : GuestRegisterSnapshot{};
                std::snprintf(address, sizeof(address),
                              "%s0x%08x(EAX=0x%08x,ECX=0x%08x,"
                              "EDX=0x%08x,EBX=0x%08x,ESP=0x%08x,"
                              "EBP=0x%08x,ESI=0x%08x,EDI=0x%08x)",
                              index == first ? "[" : " -> ",
                              active_guest_functions[index], registers.eax,
                              registers.ecx, registers.edx, registers.ebx,
                              registers.esp, registers.ebp, registers.esi,
                              registers.edi);
                error += address;
                if (trace_allocation_context &&
                    registers.has_stack_arguments) {
                    char arguments[112]{};
                    std::snprintf(arguments, sizeof(arguments),
                                  "{stack=0x%08x,args=0x%08x,0x%08x,"
                                  "0x%08x}",
                                  registers.stack_return_slot,
                                  registers.stack_arguments[0],
                                  registers.stack_arguments[1],
                                  registers.stack_arguments[2]);
                    error += arguments;
                    for (size_t argument_index = 0;
                         argument_index < registers.stack_arguments.size();
                         ++argument_index) {
                        if (!registers
                                 .has_stack_argument_memory[argument_index])
                            continue;
                        const uint32_t pointer =
                            registers.stack_arguments[argument_index];
                        char memory[128]{};
                        std::snprintf(memory, sizeof(memory),
                                      "{guest-memory@0x%08x=", pointer);
                        error += memory;
                        for (size_t word_index = 0; word_index < 4;
                             ++word_index) {
                            char word[16]{};
                            std::snprintf(
                                word, sizeof(word), "%s%08x",
                                word_index == 0 ? "" : ",",
                                registers.stack_argument_memory[argument_index]
                                                               [word_index]);
                            error += word;
                        }
                        error += "}";
                    }
                }
                if (trace_allocation_context &&
                    registers.has_ecx_object_memory) {
                    char object[64]{};
                    std::snprintf(object, sizeof(object),
                                  "{guest-ecx-memory@0x%08x=",
                                  registers.ecx);
                    error += object;
                    for (size_t word_index = 0;
                         word_index < registers.ecx_object_memory.size();
                         ++word_index) {
                        char word[16]{};
                        std::snprintf(
                            word, sizeof(word), "%s%08x",
                            word_index == 0 ? "" : ",",
                            registers.ecx_object_memory[word_index]);
                        error += word;
                    }
                    error += "}";
                    for (size_t link_index = 0;
                         link_index < registers.ecx_object_link_count;
                         ++link_index) {
                        const auto& link =
                            registers.ecx_object_links[link_index];
                        char linked_memory[64]{};
                        std::snprintf(
                            linked_memory, sizeof(linked_memory),
                            "{guest-ecx-link@0x%08x=", link.address);
                        error += linked_memory;
                        for (size_t word_index = 0;
                             word_index < link.memory.size(); ++word_index) {
                            char word[16]{};
                            std::snprintf(
                                word, sizeof(word), "%s%08x",
                                word_index == 0 ? "" : ",",
                                link.memory[word_index]);
                            error += word;
                        }
                        error += "}";
                    }
                    for (size_t link_index = 0;
                         link_index < registers.ecx_object_chain_link_count;
                         ++link_index) {
                        const auto& link =
                            registers.ecx_object_chain_links[link_index];
                        char linked_memory[64]{};
                        std::snprintf(
                            linked_memory, sizeof(linked_memory),
                            "{guest-ecx-next@0x%08x+0x10->0x%08x=",
                            link.parent_address, link.address);
                        error += linked_memory;
                        for (size_t word_index = 0;
                             word_index < link.memory.size(); ++word_index) {
                            char word[16]{};
                            std::snprintf(
                                word, sizeof(word), "%s%08x",
                                word_index == 0 ? "" : ",",
                                link.memory[word_index]);
                            error += word;
                        }
                        error += "}";
                    }
                }
                const std::string ebx_text =
                    read_diagnostic_guest_ascii(registers.ebx);
                if (!ebx_text.empty()) {
                    error += "{EBX-text='" + ebx_text + "'}";
                }
            }
            error += "]";
        }
        if (trace_allocation_context &&
            guest_pool_allocation_attempt_count != 0) {
            char header[96]{};
            std::snprintf(
                header, sizeof(header),
                "; pool allocation attempts(total=%llu,stored=%zu)=[",
                static_cast<unsigned long long>(
                    guest_pool_allocation_attempts_seen),
                guest_pool_allocation_attempt_count);
            error += header;
            const size_t first_attempt =
                (guest_pool_allocation_attempt_cursor +
                 guest_pool_allocation_attempts.size() -
                 guest_pool_allocation_attempt_count) %
                guest_pool_allocation_attempts.size();
            for (size_t index = 0;
                 index < guest_pool_allocation_attempt_count; ++index) {
                const size_t attempt_index =
                    (first_attempt + index) %
                    guest_pool_allocation_attempts.size();
                const auto& attempt =
                    guest_pool_allocation_attempts[attempt_index];
                char record[512]{};
                char result_eax[24]{};
                if (attempt.has_result_eax) {
                    std::snprintf(result_eax, sizeof(result_eax),
                                  "0x%08x", attempt.result_eax);
                } else {
                    std::snprintf(result_eax, sizeof(result_eax),
                                  "unavailable");
                }
                std::snprintf(
                    record, sizeof(record),
                    "%s#%llu@0x%08x(return=0x%08x,pool=0x%08x,size=0x%08x,"
                    "flags=0x%08x,pool_flags=0x%08x,threshold=0x%08x,"
                    "list100=0x%08x,list104=0x%08x,selected_head=0x%08x,"
                    "next=+0x%x,nodes=%zu,terminated=%u,truncated=%u,"
                    "cycle=%u,eax=%s,name='%s')",
                    index == 0 ? "" : ",",
                    static_cast<unsigned long long>(attempt.sequence),
                    attempt.function_address, attempt.return_address,
                    attempt.pool_address, attempt.request_size,
                    attempt.request_flags, attempt.pool_flags,
                    attempt.pool_threshold, attempt.list_head_100,
                    attempt.list_head_104, attempt.selected_list_head,
                    attempt.selected_list_next_offset,
                    attempt.selected_list_node_count,
                    attempt.selected_list_terminated ? 1u : 0u,
                    attempt.selected_list_truncated ? 1u : 0u,
                    attempt.selected_list_cycle ? 1u : 0u, result_eax,
                    attempt.pool_name.data());
                error += record;
                for (size_t node_index = 0;
                     node_index < attempt.selected_list_node_count;
                     ++node_index) {
                    const auto& node =
                        attempt.selected_list_nodes[node_index];
                    char node_header[96]{};
                    std::snprintf(
                        node_header, sizeof(node_header),
                        "{guest-pool-node@0x%08x(prev=0x%08x,words=",
                        node.address, node.parent_address);
                    error += node_header;
                    for (size_t word_index = 0;
                         word_index < node.memory.size(); ++word_index) {
                        char word[16]{};
                        std::snprintf(word, sizeof(word), "%s%08x",
                                      word_index == 0 ? "" : ",",
                                      node.memory[word_index]);
                        error += word;
                    }
                    error += ")}";
                }
            }
            error += "]";
        }
        return -1;
    }

    std::string read_diagnostic_guest_ascii(uint32_t address) const {
        if (!ram || address >= kGuestRamSize) return {};
        const auto* bytes = static_cast<const uint8_t*>(ram);
        std::string text;
        for (uint64_t index = 0; index < 64; ++index) {
            const uint64_t byte_address =
                static_cast<uint64_t>(address) + index;
            if (byte_address >= kGuestRamSize) return {};
            const uint8_t byte = bytes[byte_address];
            if (byte == 0) return text;
            if (byte < 0x20 || byte > 0x7e) return {};
            text.push_back(static_cast<char>(byte));
        }
        return {};
    }

    bool diagnostic_guest_pointer_mapped(uint32_t address,
                                         size_t size) const {
        if (address == 0) return false;
        const uint64_t end = static_cast<uint64_t>(address) + size;
        if (end > kGuestRamSize) return false;
        if (pe_image_size != 0 && address >= pe_image_base &&
            end <= static_cast<uint64_t>(pe_image_base) + pe_image_size) {
            return true;
        }
        for (const auto& region : guest_virtual_allocations) {
            if (address >= region.first &&
                end <= static_cast<uint64_t>(region.first) + region.second) {
                return true;
            }
        }
        for (const auto& allocation : heap_allocations) {
            if (address >= allocation.first &&
                end <= static_cast<uint64_t>(allocation.first) +
                           allocation.second.size) {
                return true;
            }
        }
        return false;
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
        state.active_function_registers = active_guest_function_registers;
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
        active_guest_function_registers = state.active_function_registers;
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
            thread.wait_sequence = 0;
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
            thread.wait_sequence = 0;
            thread.wait_result = 0x00000102;
            enqueue_guest_thread(handle);
        };
        wake(0, main_guest_thread);
        for (auto& [handle, thread] : guest_threads) wake(handle, thread);
    }

    void wake_guest_event_waiters(uint32_t handle, GuestEvent& event) {
        auto wake = [&](uint32_t candidate, GuestThread& thread) {
            if (!thread.waiting || thread.wait_handle != handle) return false;
            thread.waiting = false;
            thread.wait_sequence = 0;
            thread.wait_result = 0;
            enqueue_guest_thread(candidate);
            return true;
        };

        if (event.manual_reset) {
            wake(0, main_guest_thread);
            for (auto& [candidate, thread] : guest_threads)
                wake(candidate, thread);
            return;
        }

        uint32_t selected_handle = 0;
        GuestThread* selected = nullptr;
        auto consider = [&](uint32_t candidate, GuestThread& thread) {
            if (!thread.waiting || thread.wait_handle != handle) return;
            if (!selected || thread.wait_sequence < selected->wait_sequence) {
                selected_handle = candidate;
                selected = &thread;
            }
        };
        consider(0, main_guest_thread);
        for (auto& [candidate, thread] : guest_threads)
            consider(candidate, thread);
        if (!selected) return;

        selected->waiting = false;
        selected->wait_sequence = 0;
        selected->wait_result = 0;
        event.signaled = false;
        enqueue_guest_thread(selected_handle);
    }

    uint32_t wake_guest_semaphore_waiters(uint32_t handle,
                                          uint32_t released_count) {
        std::vector<std::pair<uint64_t, uint32_t>> waiters;
        auto collect = [&](uint32_t candidate, const GuestThread& thread) {
            if (thread.waiting && thread.wait_handle == handle) {
                waiters.emplace_back(thread.wait_sequence, candidate);
            }
        };
        collect(0, main_guest_thread);
        for (const auto& [candidate, thread] : guest_threads)
            collect(candidate, thread);
        std::sort(waiters.begin(), waiters.end());

        const uint32_t wake_count = static_cast<uint32_t>(
            std::min<size_t>(released_count, waiters.size()));
        for (uint32_t index = 0; index < wake_count; ++index) {
            const uint32_t waiter_handle = waiters[index].second;
            GuestThread* waiter = guest_execution_state(waiter_handle);
            if (!waiter || !waiter->waiting || waiter->wait_handle != handle)
                continue;
            waiter->waiting = false;
            waiter->wait_sequence = 0;
            waiter->wait_result = 0;
            enqueue_guest_thread(waiter_handle);
        }
        return wake_count;
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
            if (ready_guest_threads.empty()) {
                auto next_deadline =
                    std::chrono::steady_clock::time_point::max();
                auto consider_deadline = [&](const GuestThread& thread) {
                    if (thread.waiting &&
                        thread.wait_deadline !=
                            std::chrono::steady_clock::time_point::max()) {
                        next_deadline =
                            std::min(next_deadline, thread.wait_deadline);
                    }
                };
                consider_deadline(main_guest_thread);
                for (const auto& [waiting_handle, thread] : guest_threads) {
                    (void)waiting_handle;
                    consider_deadline(thread);
                }
                if (next_deadline ==
                    std::chrono::steady_clock::time_point::max()) {
                    break;
                }
                std::this_thread::sleep_until(next_deadline);
                continue;
            }

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
        active_guest_function_registers.clear();
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

    int create_semaphore_a() {
        constexpr const char* api = "KERNEL32.dll!CreateSemaphoreA";
        uint32_t security_attributes = 0;
        uint32_t initial_count = 0;
        uint32_t maximum_count = 0;
        uint32_t name_address = 0;
        if (!read_stack_argument(0, security_attributes, api) ||
            !read_stack_argument(1, initial_count, api) ||
            !read_stack_argument(2, maximum_count, api) ||
            !read_stack_argument(3, name_address, api)) {
            return -1;
        }
        (void)security_attributes;
        if (maximum_count == 0 || initial_count > maximum_count) {
            guest_last_error = 87;
            return return_kernel32_dword(0, api, 16);
        }

        std::string name;
        if (name_address != 0 && !read_guest_ascii(name_address, name, api))
            return -1;
        if (!name.empty()) {
            const auto existing = guest_named_semaphores.find(name);
            if (existing != guest_named_semaphores.end()) {
                guest_last_error = 183;
                return return_kernel32_dword(existing->second, api, 16);
            }
        }
        if (next_guest_semaphore_handle >
            std::numeric_limits<uint32_t>::max() - sizeof(uint32_t)) {
            guest_last_error = 8;
            return return_kernel32_dword(0, api, 16);
        }
        const uint32_t handle =
            static_cast<uint32_t>(next_guest_semaphore_handle);
        next_guest_semaphore_handle += sizeof(uint32_t);
        guest_semaphores.emplace(
            handle, GuestSemaphore{initial_count, maximum_count});
        if (!name.empty())
            guest_named_semaphores.emplace(std::move(name), handle);
        return return_kernel32_dword(handle, api, 16);
    }

    int release_semaphore() {
        constexpr const char* api = "KERNEL32.dll!ReleaseSemaphore";
        uint32_t handle = 0;
        uint32_t release_count = 0;
        uint32_t previous_count_address = 0;
        if (!read_stack_argument(0, handle, api) ||
            !read_stack_argument(1, release_count, api) ||
            !read_stack_argument(2, previous_count_address, api)) {
            return -1;
        }
        const auto semaphore = guest_semaphores.find(handle);
        if (semaphore == guest_semaphores.end()) {
            guest_last_error = 6;
            return return_kernel32_dword(0, api, 12);
        }
        if (release_count == 0 ||
            release_count > semaphore->second.maximum_count -
                                semaphore->second.count) {
            guest_last_error = 298;
            return return_kernel32_dword(0, api, 12);
        }
        const uint32_t previous_count = semaphore->second.count;
        if (previous_count_address != 0) {
            if (!valid_guest_pointer(previous_count_address,
                                    sizeof(previous_count)) ||
                !write_guest_u32("ram", previous_count_address,
                                 previous_count)) {
                error = std::string(api) +
                        " has an invalid previous-count pointer";
                return -1;
            }
        }
        const uint32_t woken =
            wake_guest_semaphore_waiters(handle, release_count);
        semaphore->second.count += release_count - woken;
        return return_kernel32_dword(1, api, 12);
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
        return return_kernel32_dword(
            wait_guest_object(handle, timeout_ms, api, alertable != 0), api,
            12);
    }

    uint32_t wait_guest_object(uint32_t handle, uint32_t timeout_ms,
                               const char* api, bool alertable = false) {
        if (alertable) {
            bool dispatched = false;
            if (!dispatch_pending_io_completions(dispatched))
                return UINT32_MAX;
            if (dispatched) return 0x000000c0;
        }
        const auto thread = guest_threads.find(handle);
        if (thread != guest_threads.end()) {
            if (thread->second.completed) return 0;
            return wait_for_guest_object(handle, timeout_ms, api, alertable);
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
            return wait_for_guest_object(handle, timeout_ms, api, alertable);
        }
        const auto semaphore = guest_semaphores.find(handle);
        if (semaphore != guest_semaphores.end()) {
            if (semaphore->second.count != 0) {
                --semaphore->second.count;
                return 0;
            }
            return wait_for_guest_object(handle, timeout_ms, api, alertable);
        }
        guest_last_error = 6;
        (void)api;
        return UINT32_MAX;
    }

    uint32_t wait_for_guest_object(uint32_t handle, uint32_t timeout_ms,
                                   const char* api, bool alertable) {
        if (timeout_ms == 0) return 0x00000102;
        if (!guest_coroutine_active || !scheduler_context_active) {
            if (timeout_ms == UINT32_MAX) {
                guest_last_error = 50;
                return UINT32_MAX;
            }
            return 0x00000102;
        }

        const uint32_t waiter_handle = current_guest_thread_handle;
        GuestThread* waiter = guest_execution_state(waiter_handle);
        if (!waiter) {
            error = std::string(api) + " has no current guest thread state";
            return UINT32_MAX;
        }
        waiter->waiting = true;
        waiter->runnable = false;
        waiter->wait_handle = handle;
        waiter->wait_result = 0x00000102;
        waiter->wait_sequence = next_guest_wait_sequence++;
        waiter->wait_alertable = alertable;
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

    int sh_get_folder_path_a() {
        constexpr const char* api = "SHELL32.dll!SHGetFolderPathA";
        uint32_t window = 0;
        uint32_t csidl = 0;
        uint32_t token = 0;
        uint32_t flags = 0;
        uint32_t output_address = 0;
        if (!read_stack_argument(0, window, api) ||
            !read_stack_argument(1, csidl, api) ||
            !read_stack_argument(2, token, api) ||
            !read_stack_argument(3, flags, api) ||
            !read_stack_argument(4, output_address, api)) {
            return -1;
        }
        (void)window;
        if (!valid_guest_pointer(output_address, kWindowsMaxPath)) {
            return return_kernel32_dword(kHresultInvalidArg, api, 20);
        }

        std::array<uint8_t, kWindowsMaxPath> output{};
        if (!write_guest_bytes(output_address, output.data(), output.size(), api))
            return -1;

        const uint32_t folder = csidl & 0x3fff;
        const uint32_t csidl_flags = csidl & ~0x3fff;
        if (folder != kCsidlPersonal || token != 0 || flags > 1 ||
            (csidl_flags & ~(kCsidlFlagCreate | kCsidlFlagDontVerify)) != 0) {
            return return_kernel32_dword(kHresultInvalidArg, api, 20);
        }

        constexpr char guest_path[] =
            "C:\\Documents and Settings\\SHIFT\\My Documents";
        std::filesystem::path folder_path;
        if (!make_guest_path_candidate(guest_path, folder_path, api))
            return return_kernel32_dword(kHresultFail, api, 20);
        std::error_code error_code;
        if ((csidl_flags & kCsidlFlagCreate) != 0) {
            std::filesystem::create_directories(folder_path, error_code);
            if (error_code)
                return return_kernel32_dword(kHresultFail, api, 20);
        }
        folder_path = std::filesystem::canonical(folder_path, error_code);
        if (error_code) {
            if ((csidl_flags & kCsidlFlagCreate) == 0 &&
                error_code == std::errc::no_such_file_or_directory) {
                return return_kernel32_dword(1, api, 20);
            }
            return return_kernel32_dword(kHresultFail, api, 20);
        }
        if (!path_is_within_guest_root(folder_path))
            return return_kernel32_dword(kHresultFail, api, 20);
        const bool is_directory =
            std::filesystem::is_directory(folder_path, error_code);
        if (error_code)
            return return_kernel32_dword(kHresultFail, api, 20);
        if (!is_directory) {
            return return_kernel32_dword(
                (csidl_flags & kCsidlFlagCreate) == 0 ? 1 : kHresultFail,
                api, 20);
        }

        constexpr size_t path_size = sizeof(guest_path) - 1;
        std::copy_n(reinterpret_cast<const uint8_t*>(guest_path), path_size,
                    output.begin());
        if (!write_guest_bytes(output_address, output.data(), path_size + 1,
                               api)) {
            return -1;
        }
        return return_kernel32_dword(0, api, 20);
    }

    int sh_create_directory_ex_a() {
        constexpr const char* api = "SHELL32.dll!SHCreateDirectoryExA";
        uint32_t window = 0;
        uint32_t path_address = 0;
        uint32_t security_attributes = 0;
        if (!read_stack_argument(0, window, api) ||
            !read_stack_argument(1, path_address, api) ||
            !read_stack_argument(2, security_attributes, api)) {
            return -1;
        }
        (void)window;
        if (security_attributes != 0)
            return return_kernel32_dword(87, api, 12);

        std::string path;
        if (!read_guest_ascii(path_address, path, api)) return -1;
        if (path.size() >= 248) return return_kernel32_dword(206, api, 12);
        if (path.size() < 3 ||
            std::tolower(static_cast<unsigned char>(path[0])) != 'c' ||
            path[1] != ':' || (path[2] != '\\' && path[2] != '/')) {
            return return_kernel32_dword(161, api, 12);
        }

        std::filesystem::path folder_path;
        if (!make_guest_path_candidate(path, folder_path, api))
            return return_kernel32_dword(guest_last_error, api, 12);
        std::error_code error_code;
        const auto current_status =
            std::filesystem::status(folder_path, error_code);
        if (!error_code && std::filesystem::exists(current_status)) {
            return return_kernel32_dword(
                std::filesystem::is_directory(current_status) ? 183 : 80,
                api, 12);
        }
        if (error_code && error_code != std::errc::no_such_file_or_directory &&
            error_code != std::errc::not_a_directory) {
            const uint32_t failure =
                error_code == std::errc::permission_denied ? 5 : 3;
            return return_kernel32_dword(failure, api, 12);
        }

        error_code.clear();
        std::filesystem::create_directories(folder_path, error_code);
        if (error_code) {
            const uint32_t failure =
                error_code == std::errc::permission_denied ? 5 :
                error_code == std::errc::filename_too_long ? 206 : 3;
            return return_kernel32_dword(failure, api, 12);
        }
        folder_path = std::filesystem::canonical(folder_path, error_code);
        if (error_code || !path_is_within_guest_root(folder_path))
            return return_kernel32_dword(5, api, 12);
        return return_kernel32_dword(0, api, 12);
    }

    int direct3d_create9() {
        constexpr const char* api = "d3d9.dll!Direct3DCreate9";
        constexpr uint32_t kD3dSdkVersion = 32;
        static constexpr std::array<const char*, 17> methods = {
            "QueryInterface", "AddRef", "Release",
            "RegisterSoftwareDevice", "GetAdapterCount",
            "GetAdapterIdentifier", "GetAdapterModeCount",
            "EnumAdapterModes", "GetAdapterDisplayMode",
            "CheckDeviceType", "CheckDeviceFormat",
            "CheckDeviceMultiSampleType", "CheckDepthStencilMatch",
            "CheckDeviceFormatConversion", "GetDeviceCaps",
            "GetAdapterMonitor", "CreateDevice"};
        uint32_t sdk_version = 0;
        if (!read_stack_argument(0, sdk_version, api)) return -1;
        uint32_t interface_address = 0;
        if (sdk_version == kD3dSdkVersion) {
            uint32_t vtable_address = 0;
            if (!allocate_guest_heap(kGuestProcessHeapHandle,
                                     methods.size() * sizeof(uint32_t),
                                     vtable_address) ||
                !allocate_guest_heap(kGuestProcessHeapHandle,
                                     sizeof(uint32_t), interface_address)) {
                interface_address = 0;
            } else {
                for (size_t index = 0; index < methods.size(); ++index) {
                    uint32_t method_stub = 0;
                    const std::string method_name =
                        std::string("d3d9.dll!IDirect3D9::") + methods[index];
                    if (!allocate_dynamic_import_stub(method_name,
                                                      method_stub) ||
                        !write_guest_u32("ram", vtable_address + index * 4,
                                         method_stub)) {
                        error = std::string(api) +
                                " could not create its IDirect3D9 vtable";
                        return -1;
                    }
                }
                if (!write_guest_u32("ram", interface_address,
                                     vtable_address)) {
                    error = std::string(api) +
                            " could not initialize its IDirect3D9 object";
                    return -1;
                }
                guest_d3d9_interfaces.emplace(
                    interface_address,
                    GuestD3D9Interface{vtable_address, 1});
            }
        }
        if (!write_guest_u32("register", kX86EaxRegisterOffset,
                             interface_address)) {
            error = std::string(api) + " cannot write EAX";
            return -1;
        }
        return finish_stdcall(sizeof(uint32_t), api) ? 0 : -1;
    }

    int d3dperf_begin_event() {
        constexpr const char* api = "d3d9.dll!D3DPERF_BeginEvent";
        uint32_t color = 0;
        uint32_t name_address = 0;
        if (!read_stack_argument(0, color, api) ||
            !read_stack_argument(1, name_address, api)) {
            return -1;
        }
        (void)color;
        (void)name_address;
        return return_kernel32_dword(0, api, 2 * sizeof(uint32_t));
    }

    int d3dperf_end_event() {
        constexpr const char* api = "d3d9.dll!D3DPERF_EndEvent";
        return return_kernel32_dword(0, api, 0);
    }

    int d3d9_add_ref() {
        constexpr const char* api = "d3d9.dll!IDirect3D9::AddRef";
        uint32_t interface_address = 0;
        if (!read_stack_argument(0, interface_address, api)) return -1;
        const auto interface = guest_d3d9_interfaces.find(interface_address);
        if (interface == guest_d3d9_interfaces.end()) {
            error = std::string(api) + " received an invalid interface pointer";
            return -1;
        }
        if (interface->second.references != UINT32_MAX)
            ++interface->second.references;
        return return_kernel32_dword(interface->second.references, api, 4);
    }

    int d3d9_release() {
        constexpr const char* api = "d3d9.dll!IDirect3D9::Release";
        uint32_t interface_address = 0;
        if (!read_stack_argument(0, interface_address, api)) return -1;
        const auto interface = guest_d3d9_interfaces.find(interface_address);
        if (interface == guest_d3d9_interfaces.end() ||
            interface->second.references == 0) {
            error = std::string(api) + " received an invalid interface pointer";
            return -1;
        }
        const uint32_t remaining = --interface->second.references;
        if (remaining == 0) {
            for (uint32_t address : {interface_address,
                                     interface->second.vtable_address}) {
                const auto allocation = heap_allocations.find(address);
                if (allocation == heap_allocations.end()) continue;
                free_heap_blocks.push_back(allocation->second);
                heap_allocations.erase(allocation);
            }
            guest_d3d9_interfaces.erase(interface);
        }
        return return_kernel32_dword(remaining, api, 4);
    }

    int d3d9_get_adapter_count() {
        constexpr const char* api =
            "d3d9.dll!IDirect3D9::GetAdapterCount";
        uint32_t interface_address = 0;
        if (!read_stack_argument(0, interface_address, api)) return -1;
        if (guest_d3d9_interfaces.find(interface_address) ==
            guest_d3d9_interfaces.end()) {
            error = std::string(api) + " received an invalid interface pointer";
            return -1;
        }

        // Expose the one guest display slot that GetAdapterDisplayMode
        // models. This does not claim that the D3D9 device is usable; device
        // capability requests still fail until the Vulkan backend exists.
        return return_kernel32_dword(1, api, 4);
    }

    int d3d9_get_adapter_mode_count() {
        constexpr const char* api =
            "d3d9.dll!IDirect3D9::GetAdapterModeCount";
        uint32_t interface_address = 0;
        uint32_t adapter = 0;
        uint32_t format = 0;
        if (!read_stack_argument(0, interface_address, api) ||
            !read_stack_argument(1, adapter, api) ||
            !read_stack_argument(2, format, api)) {
            return -1;
        }
        if (guest_d3d9_interfaces.find(interface_address) ==
            guest_d3d9_interfaces.end()) {
            error = std::string(api) + " received an invalid interface pointer";
            return -1;
        }

        const uint32_t count =
            adapter == 0 && format == guest_display_format ? 1 : 0;
        return return_kernel32_dword(count, api, 12);
    }

    int d3d9_check_device_type() {
        constexpr const char* api =
            "d3d9.dll!IDirect3D9::CheckDeviceType";
        uint32_t interface_address = 0;
        uint32_t adapter = 0;
        uint32_t device_type = 0;
        uint32_t adapter_format = 0;
        uint32_t back_buffer_format = 0;
        uint32_t windowed = 0;
        if (!read_stack_argument(0, interface_address, api) ||
            !read_stack_argument(1, adapter, api) ||
            !read_stack_argument(2, device_type, api) ||
            !read_stack_argument(3, adapter_format, api) ||
            !read_stack_argument(4, back_buffer_format, api) ||
            !read_stack_argument(5, windowed, api)) {
            return -1;
        }
        if (guest_d3d9_interfaces.find(interface_address) ==
            guest_d3d9_interfaces.end()) {
            error = std::string(api) + " received an invalid interface pointer";
            return -1;
        }
        if (adapter != 0 || device_type != 1 ||
            (windowed != 0 && windowed != 1)) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 24);
        }
        if (!guest_d3d9_adapter_info_available ||
            !guest_d3d9_adapter_info.supports_bgra8_surface ||
            adapter_format != kD3dFormatX8R8G8B8 ||
            (back_buffer_format != 21 &&
             back_buffer_format != kD3dFormatX8R8G8B8)) {
            return return_kernel32_dword(kD3dErrNotAvailable, api, 24);
        }
        return return_kernel32_dword(0, api, 24);
    }

    int d3d9_check_device_format() {
        constexpr const char* api =
            "d3d9.dll!IDirect3D9::CheckDeviceFormat";
        uint32_t interface_address = 0;
        uint32_t adapter = 0;
        uint32_t device_type = 0;
        uint32_t adapter_format = 0;
        uint32_t usage = 0;
        uint32_t resource_type = 0;
        uint32_t check_format = 0;
        if (!read_stack_argument(0, interface_address, api) ||
            !read_stack_argument(1, adapter, api) ||
            !read_stack_argument(2, device_type, api) ||
            !read_stack_argument(3, adapter_format, api) ||
            !read_stack_argument(4, usage, api) ||
            !read_stack_argument(5, resource_type, api) ||
            !read_stack_argument(6, check_format, api)) {
            return -1;
        }
        if (guest_d3d9_interfaces.find(interface_address) ==
            guest_d3d9_interfaces.end()) {
            error = std::string(api) + " received an invalid interface pointer";
            return -1;
        }
        if (adapter != 0 || device_type != 1 || resource_type < 1 ||
            resource_type > 7) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 28);
        }

        if (!guest_d3d9_adapter_info_available ||
            !guest_d3d9_adapter_info.supports_bgra8_surface ||
            (adapter_format != 21 && adapter_format != kD3dFormatX8R8G8B8)) {
            return return_kernel32_dword(kD3dErrNotAvailable, api, 28);
        }

        // The Vulkan host exposes BGRA8 as a sampled color format and, when
        // presentable, as a render target. SHIFT's depth-format probe asks
        // for D24S8 as a depth/stencil surface or texture. Keep this table
        // narrow so D3D9 does not advertise formats the host cannot back.
        const bool surface_or_texture =
            resource_type == 1 || resource_type == 3;
        const bool bgra8_format = check_format == 21 ||
                                  check_format == kD3dFormatX8R8G8B8;
        if (surface_or_texture && bgra8_format &&
            (usage == 0 || usage == 1 || usage == 5) &&
            ((usage & 1) != 0
                 ? guest_d3d9_adapter_info.supports_bgra8_surface
                 : guest_d3d9_adapter_info.supports_bgra8_texture)) {
            return return_kernel32_dword(0, api, 28);
        }
        if (surface_or_texture && check_format == 75 && usage == 2 &&
            guest_d3d9_adapter_info.supports_d24s8_depth_stencil &&
            (guest_d3d9_adapter_info.d24s8_sample_count_mask & 1) != 0) {
            return return_kernel32_dword(0, api, 28);
        }
        return return_kernel32_dword(kD3dErrNotAvailable, api, 28);
    }

    int d3d9_check_depth_stencil_match() {
        constexpr const char* api =
            "d3d9.dll!IDirect3D9::CheckDepthStencilMatch";
        uint32_t interface_address = 0;
        uint32_t adapter = 0;
        uint32_t device_type = 0;
        uint32_t adapter_format = 0;
        uint32_t render_target_format = 0;
        uint32_t depth_stencil_format = 0;
        if (!read_stack_argument(0, interface_address, api) ||
            !read_stack_argument(1, adapter, api) ||
            !read_stack_argument(2, device_type, api) ||
            !read_stack_argument(3, adapter_format, api) ||
            !read_stack_argument(4, render_target_format, api) ||
            !read_stack_argument(5, depth_stencil_format, api)) {
            return -1;
        }
        if (guest_d3d9_interfaces.find(interface_address) ==
            guest_d3d9_interfaces.end()) {
            error = std::string(api) + " received an invalid interface pointer";
            return -1;
        }
        if (adapter != 0 || (device_type != 1) ||
            (adapter_format != 21 &&
             adapter_format != kD3dFormatX8R8G8B8) ||
            (render_target_format != 21 &&
             render_target_format != kD3dFormatX8R8G8B8)) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 24);
        }
        if (!guest_d3d9_adapter_info_available ||
            !guest_d3d9_adapter_info.supports_bgra8_surface ||
            !guest_d3d9_adapter_info.supports_d24s8_depth_stencil ||
            (guest_d3d9_adapter_info.d24s8_sample_count_mask & 1) == 0 ||
            depth_stencil_format != 75) {
            return return_kernel32_dword(kD3dErrNotAvailable, api, 24);
        }
        return return_kernel32_dword(0, api, 24);
    }

    int d3d9_enum_adapter_modes() {
        constexpr const char* api =
            "d3d9.dll!IDirect3D9::EnumAdapterModes";
        uint32_t interface_address = 0;
        uint32_t adapter = 0;
        uint32_t format = 0;
        uint32_t mode_index = 0;
        uint32_t mode_address = 0;
        if (!read_stack_argument(0, interface_address, api) ||
            !read_stack_argument(1, adapter, api) ||
            !read_stack_argument(2, format, api) ||
            !read_stack_argument(3, mode_index, api) ||
            !read_stack_argument(4, mode_address, api)) {
            return -1;
        }
        if (guest_d3d9_interfaces.find(interface_address) ==
            guest_d3d9_interfaces.end()) {
            error = std::string(api) + " received an invalid interface pointer";
            return -1;
        }
        if (adapter != 0 || mode_address == 0 ||
            mode_address > UINT32_MAX - 15) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 20);
        }
        if (format != guest_display_format || mode_index != 0) {
            return return_kernel32_dword(kD3dErrNotAvailable, api, 20);
        }

        const std::array<uint32_t, 4> mode = {
            guest_display_width, guest_display_height,
            guest_display_refresh_rate, guest_display_format};
        for (size_t index = 0; index < mode.size(); ++index) {
            if (!write_guest_u32("ram", mode_address + index * 4,
                                 mode[index])) {
                return return_kernel32_dword(kD3dErrInvalidCall, api, 20);
            }
        }
        return return_kernel32_dword(0, api, 20);
    }

    int d3d9_check_device_multisample_type() {
        constexpr const char* api =
            "d3d9.dll!IDirect3D9::CheckDeviceMultiSampleType";
        uint32_t interface_address = 0;
        uint32_t adapter = 0;
        uint32_t device_type = 0;
        uint32_t surface_format = 0;
        uint32_t windowed = 0;
        uint32_t multisample_type = 0;
        uint32_t quality_levels_address = 0;
        if (!read_stack_argument(0, interface_address, api) ||
            !read_stack_argument(1, adapter, api) ||
            !read_stack_argument(2, device_type, api) ||
            !read_stack_argument(3, surface_format, api) ||
            !read_stack_argument(4, windowed, api) ||
            !read_stack_argument(5, multisample_type, api) ||
            !read_stack_argument(6, quality_levels_address, api)) {
            return -1;
        }
        if (guest_d3d9_interfaces.find(interface_address) ==
            guest_d3d9_interfaces.end()) {
            error = std::string(api) + " received an invalid interface pointer";
            return -1;
        }
        if (adapter != 0 || multisample_type > 16 || windowed > 1) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 28);
        }
        if (device_type != 1) {
            return return_kernel32_dword(kD3dErrInvalidDevice, api, 28);
        }
        if (quality_levels_address != 0 &&
            (quality_levels_address > UINT32_MAX - 3 ||
             !valid_guest_pointer(quality_levels_address, sizeof(uint32_t)))) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 28);
        }

        if (!guest_d3d9_adapter_info_available ||
            !guest_d3d9_adapter_info.supports_bgra8_surface) {
            return return_kernel32_dword(kD3dErrNotAvailable, api, 28);
        }
        uint32_t sample_count_mask = 0;
        if (surface_format == 21 || surface_format == kD3dFormatX8R8G8B8) {
            sample_count_mask =
                guest_d3d9_adapter_info.bgra8_sample_count_mask;
        } else if (surface_format == 75) {
            sample_count_mask =
                guest_d3d9_adapter_info.d24s8_sample_count_mask;
        }
        const uint32_t sample_bit = multisample_type == 0
                                        ? 1
                                        : multisample_type;
        if (multisample_type == 1 || sample_bit > 64 ||
            (sample_bit & (sample_bit - 1)) != 0 ||
            (sample_count_mask & sample_bit) == 0) {
            return return_kernel32_dword(kD3dErrNotAvailable, api, 28);
        }
        if (quality_levels_address != 0 &&
            !write_guest_u32("ram", quality_levels_address, 1)) {
            return -1;
        }
        (void)windowed;
        return return_kernel32_dword(0, api, 28);
    }

    int d3d9_get_adapter_display_mode() {
        constexpr const char* api =
            "d3d9.dll!IDirect3D9::GetAdapterDisplayMode";
        uint32_t interface_address = 0;
        uint32_t adapter = 0;
        uint32_t mode_address = 0;
        if (!read_stack_argument(0, interface_address, api) ||
            !read_stack_argument(1, adapter, api) ||
            !read_stack_argument(2, mode_address, api)) {
            return -1;
        }
        const auto interface = guest_d3d9_interfaces.find(interface_address);
        if (interface == guest_d3d9_interfaces.end()) {
            error = std::string(api) + " received an invalid interface pointer";
            return -1;
        }
        if (adapter != 0 || mode_address == 0 ||
            mode_address > UINT32_MAX - 15) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 12);
        }

        const std::array<uint32_t, 4> mode = {
            guest_display_width, guest_display_height,
            guest_display_refresh_rate, guest_display_format};
        for (size_t index = 0; index < mode.size(); ++index) {
            if (!write_guest_u32("ram", mode_address + index * 4,
                                 mode[index])) {
                return return_kernel32_dword(kD3dErrInvalidCall, api, 12);
            }
        }
        return return_kernel32_dword(0, api, 12);
    }

    bool write_d3d9_caps(uint32_t caps_address, const char* api) {
        std::array<uint8_t, kD3dCaps9Size> caps_bytes{};
        for (size_t index = 0;
             index < guest_d3d9_adapter_info.caps.size(); ++index) {
            const uint32_t word = guest_d3d9_adapter_info.caps[index];
            for (size_t byte = 0; byte < sizeof(word); ++byte) {
                caps_bytes[index * sizeof(word) + byte] =
                    static_cast<uint8_t>(word >> (byte * 8));
            }
        }
        return write_guest_bytes(caps_address, caps_bytes.data(),
                                 caps_bytes.size(), api);
    }

    int d3d9_get_device_caps() {
        constexpr const char* api = "d3d9.dll!IDirect3D9::GetDeviceCaps";
        uint32_t interface_address = 0;
        uint32_t adapter = 0;
        uint32_t device_type = 0;
        uint32_t caps_address = 0;
        if (!read_stack_argument(0, interface_address, api) ||
            !read_stack_argument(1, adapter, api) ||
            !read_stack_argument(2, device_type, api) ||
            !read_stack_argument(3, caps_address, api)) {
            return -1;
        }
        const auto interface = guest_d3d9_interfaces.find(interface_address);
        if (interface == guest_d3d9_interfaces.end()) {
            error = std::string(api) + " received an invalid interface pointer";
            return -1;
        }
        if (adapter != 0 || caps_address == 0 ||
            caps_address > UINT32_MAX - (kD3dCaps9Size - 1) ||
            !valid_guest_pointer(caps_address, kD3dCaps9Size)) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 16);
        }
        if (device_type != 1) {
            return return_kernel32_dword(kD3dErrInvalidDevice, api, 16);
        }
        if (!guest_d3d9_adapter_info_available) {
            return return_kernel32_dword(kD3dErrNotAvailable, api, 16);
        }

        if (!write_d3d9_caps(caps_address, api)) return -1;
        return return_kernel32_dword(0, api, 16);
    }

    int d3d9_device_get_caps() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DDevice9::GetDeviceCaps";
        uint32_t device_address = 0;
        uint32_t caps_address = 0;
        if (!read_stack_argument(0, device_address, api) ||
            !read_stack_argument(1, caps_address, api)) {
            return -1;
        }
        if (guest_d3d9_devices.find(device_address) ==
            guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        if (caps_address == 0 ||
            caps_address > UINT32_MAX - (kD3dCaps9Size - 1) ||
            !valid_guest_pointer(caps_address, kD3dCaps9Size)) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 8);
        }
        if (!guest_d3d9_adapter_info_available) {
            return return_kernel32_dword(kD3dErrNotAvailable, api, 8);
        }
        if (!write_d3d9_caps(caps_address, api)) return -1;
        return return_kernel32_dword(0, api, 8);
    }

    int d3d9_create_device() {
        constexpr const char* api = "d3d9.dll!IDirect3D9::CreateDevice";
        constexpr size_t parameter_size = 14 * sizeof(uint32_t);
        d3d9_create_device_attempted = true;
        d3d9_create_device_callback_called = false;
        d3d9_create_device_hresult = UINT32_MAX;
        d3d9_create_device_rejection.clear();
        const auto reject = [this, api](uint32_t result,
                                        const std::string& reason) {
            d3d9_create_device_hresult = result;
            d3d9_create_device_rejection = reason;
            return return_kernel32_dword(result, api, 28);
        };
        uint32_t interface_address = 0;
        uint32_t adapter = 0;
        uint32_t device_type = 0;
        uint32_t focus_window = 0;
        uint32_t behavior_flags = 0;
        uint32_t parameters_address = 0;
        uint32_t output_device_address = 0;
        if (!read_stack_argument(0, interface_address, api) ||
            !read_stack_argument(1, adapter, api) ||
            !read_stack_argument(2, device_type, api) ||
            !read_stack_argument(3, focus_window, api) ||
            !read_stack_argument(4, behavior_flags, api) ||
            !read_stack_argument(5, parameters_address, api) ||
            !read_stack_argument(6, output_device_address, api)) {
            d3d9_create_device_rejection = "invalid CreateDevice stack arguments";
            return -1;
        }
        if (guest_d3d9_interfaces.find(interface_address) ==
                guest_d3d9_interfaces.end()) {
            error = std::string(api) + " received an invalid interface pointer";
            d3d9_create_device_rejection = "invalid IDirect3D9 interface pointer";
            return -1;
        }
        if (output_device_address == 0 ||
            !valid_guest_pointer(output_device_address, sizeof(uint32_t)) ||
            parameters_address == 0 ||
            !valid_guest_pointer(parameters_address, parameter_size)) {
            return reject(kD3dErrInvalidCall,
                          "invalid presentation or output-device pointer");
        }
        if (!write_guest_u32("ram", output_device_address, 0)) return -1;
        if (adapter != 0) {
            return reject(kD3dErrInvalidCall, "adapter index is not zero");
        }
        if (device_type != 1) {
            return reject(kD3dErrInvalidDevice, "device type is not HAL");
        }

        std::array<uint32_t, 14> fields{};
        for (size_t index = 0; index < fields.size(); ++index) {
            if (!read_guest_u32("ram", parameters_address + index * 4,
                                fields[index])) {
                return return_kernel32_dword(kD3dErrInvalidCall, api, 28);
            }
        }
        RecompiledGuestD3d9PresentationParameters parameters{};
        parameters.back_buffer_width = fields[0];
        parameters.back_buffer_height = fields[1];
        parameters.back_buffer_format = fields[2];
        parameters.back_buffer_count = fields[3];
        parameters.multisample_type = fields[4];
        parameters.multisample_quality = fields[5];
        parameters.swap_effect = fields[6];
        parameters.device_window = fields[7];
        parameters.windowed = fields[8];
        parameters.enable_auto_depth_stencil = fields[9];
        parameters.auto_depth_stencil_format = fields[10];
        parameters.flags = fields[11];
        parameters.fullscreen_refresh_rate = fields[12];
        parameters.presentation_interval = fields[13];
        if ((parameters.windowed != 0 && parameters.windowed != 1) ||
            (parameters.enable_auto_depth_stencil != 0 &&
             parameters.enable_auto_depth_stencil != 1) ||
            focus_window == 0 || parameters.device_window == 0) {
            return reject(kD3dErrInvalidCall,
                          "invalid window or boolean presentation parameter");
        }
        if (!guest_d3d9_adapter_info_available ||
            !guest_d3d9_adapter_info.supports_bgra8_surface ||
            guest_d3d9_adapter_info.create_device == nullptr) {
            return reject(kD3dErrNotAvailable,
                          "Vulkan adapter lacks BGRA8 surface support or callback");
        }
        std::string backend_error;
        d3d9_create_device_callback_called = true;
        if (!guest_d3d9_adapter_info.create_device(
                guest_d3d9_adapter_info.backend_context, focus_window,
                behavior_flags, parameters, backend_error)) {
            return reject(kD3dErrNotAvailable,
                          backend_error.empty()
                              ? "Vulkan CreateDevice callback rejected request"
                              : backend_error);
        }
        if (!write_guest_u32("ram", parameters_address,
                             parameters.back_buffer_width) ||
            !write_guest_u32("ram", parameters_address + 4,
                             parameters.back_buffer_height) ||
            !write_guest_u32("ram", parameters_address + 8,
                             parameters.back_buffer_format) ||
            !write_guest_u32("ram", parameters_address + 12,
                             parameters.back_buffer_count) ||
            !write_guest_u32("ram", parameters_address + 16,
                             parameters.multisample_type) ||
            !write_guest_u32("ram", parameters_address + 20,
                             parameters.multisample_quality) ||
            !write_guest_u32("ram", parameters_address + 24,
                             parameters.swap_effect) ||
            !write_guest_u32("ram", parameters_address + 28,
                             parameters.device_window) ||
            !write_guest_u32("ram", parameters_address + 32,
                             parameters.windowed) ||
            !write_guest_u32("ram", parameters_address + 36,
                             parameters.enable_auto_depth_stencil) ||
            !write_guest_u32("ram", parameters_address + 40,
                             parameters.auto_depth_stencil_format) ||
            !write_guest_u32("ram", parameters_address + 44,
                             parameters.flags) ||
            !write_guest_u32("ram", parameters_address + 48,
                             parameters.fullscreen_refresh_rate) ||
            !write_guest_u32("ram", parameters_address + 52,
                             parameters.presentation_interval)) {
            d3d9_create_device_rejection =
                "failed to write normalized presentation parameters";
            return -1;
        }

        static constexpr std::array<const char*, 119> methods = {
            "QueryInterface", "AddRef", "Release", "TestCooperativeLevel",
            "GetAvailableTextureMem", "EvictManagedResources", "GetDirect3D",
            "GetDeviceCaps", "GetDisplayMode", "GetCreationParameters",
            "SetCursorProperties", "SetCursorPosition", "ShowCursor",
            "CreateAdditionalSwapChain", "GetSwapChain", "GetNumberOfSwapChains",
            "Reset", "Present", "GetBackBuffer", "GetRasterStatus",
            "SetDialogBoxMode", "SetGammaRamp", "GetGammaRamp", "CreateTexture",
            "CreateVolumeTexture", "CreateCubeTexture", "CreateVertexBuffer",
            "CreateIndexBuffer", "CreateRenderTarget", "CreateDepthStencilSurface",
            "UpdateSurface", "UpdateTexture", "GetRenderTargetData",
            "GetFrontBufferData", "StretchRect", "ColorFill",
            "CreateOffscreenPlainSurface", "SetRenderTarget", "GetRenderTarget",
            "SetDepthStencilSurface", "GetDepthStencilSurface", "BeginScene",
            "EndScene", "Clear", "SetTransform", "GetTransform",
            "MultiplyTransform", "SetViewport", "GetViewport", "SetMaterial",
            "GetMaterial", "SetLight", "GetLight", "LightEnable", "GetLightEnable",
            "SetClipPlane", "GetClipPlane", "SetRenderState", "GetRenderState",
            "CreateStateBlock", "BeginStateBlock", "EndStateBlock", "SetClipStatus",
            "GetClipStatus", "GetTexture", "SetTexture", "GetTextureStageState",
            "SetTextureStageState", "GetSamplerState", "SetSamplerState",
            "ValidateDevice", "SetPaletteEntries", "GetPaletteEntries",
            "SetCurrentTexturePalette", "GetCurrentTexturePalette", "SetScissorRect",
            "GetScissorRect", "SetSoftwareVertexProcessing",
            "GetSoftwareVertexProcessing", "SetNPatchMode", "GetNPatchMode",
            "DrawPrimitive", "DrawIndexedPrimitive", "DrawPrimitiveUP",
            "DrawIndexedPrimitiveUP", "ProcessVertices", "CreateVertexDeclaration",
            "SetVertexDeclaration", "GetVertexDeclaration", "SetFVF", "GetFVF",
            "CreateVertexShader", "SetVertexShader", "GetVertexShader",
            "SetVertexShaderConstantF", "GetVertexShaderConstantF",
            "SetVertexShaderConstantI", "GetVertexShaderConstantI",
            "SetVertexShaderConstantB", "GetVertexShaderConstantB", "SetStreamSource",
            "GetStreamSource", "SetStreamSourceFreq", "GetStreamSourceFreq",
            "SetIndices", "GetIndices", "CreatePixelShader", "SetPixelShader",
            "GetPixelShader", "SetPixelShaderConstantF", "GetPixelShaderConstantF",
            "SetPixelShaderConstantI", "GetPixelShaderConstantI",
            "SetPixelShaderConstantB", "GetPixelShaderConstantB", "DrawRectPatch",
            "DrawTriPatch", "DeletePatch", "CreateQuery"};
        uint32_t vtable_address = 0;
        uint32_t device_address = 0;
        if (!allocate_guest_heap(kGuestProcessHeapHandle,
                                 methods.size() * sizeof(uint32_t),
                                 vtable_address) ||
            !allocate_guest_heap(kGuestProcessHeapHandle, sizeof(uint32_t),
                                 device_address)) {
            error = std::string(api) + " could not allocate an IDirect3DDevice9";
            d3d9_create_device_rejection = "failed to allocate IDirect3DDevice9";
            return -1;
        }
        for (size_t index = 0; index < methods.size(); ++index) {
            uint32_t method_stub = 0;
            const std::string method_name =
                std::string("d3d9.dll!IDirect3DDevice9::") + methods[index];
            if (!allocate_dynamic_import_stub(method_name, method_stub) ||
                !write_guest_u32("ram", vtable_address + index * 4,
                                 method_stub)) {
                error = std::string(api) + " could not create its device vtable";
                d3d9_create_device_rejection = "failed to create IDirect3DDevice9 vtable";
                return -1;
            }
        }
        if (!write_guest_u32("ram", device_address, vtable_address) ||
            !write_guest_u32("ram", output_device_address, device_address)) {
            error = std::string(api) + " could not initialize its device object";
            d3d9_create_device_rejection = "failed to initialize IDirect3DDevice9 object";
            return -1;
        }
        auto parent = guest_d3d9_interfaces.find(interface_address);
        if (parent->second.references != UINT32_MAX) ++parent->second.references;
        guest_d3d9_devices.emplace(
            device_address,
            GuestD3D9Device{vtable_address, interface_address, 1,
                            focus_window, behavior_flags, 0, 0, {}, {}, {}, 0, {},
                            parameters});
        d3d9_create_device_hresult = 0;
        return return_kernel32_dword(0, api, 28);
    }

    int d3d9_device_add_ref() {
        constexpr const char* api = "d3d9.dll!IDirect3DDevice9::AddRef";
        uint32_t device_address = 0;
        if (!read_stack_argument(0, device_address, api)) return -1;
        auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        if (device->second.references != UINT32_MAX)
            ++device->second.references;
        return return_kernel32_dword(device->second.references, api, 4);
    }

    int d3d9_device_release() {
        constexpr const char* api = "d3d9.dll!IDirect3DDevice9::Release";
        uint32_t device_address = 0;
        if (!read_stack_argument(0, device_address, api)) return -1;
        auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end() ||
            device->second.references == 0) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        const uint32_t remaining = --device->second.references;
        if (remaining == 0) {
            const uint32_t vtable_address = device->second.vtable_address;
            const uint32_t parent_address =
                device->second.direct3d_interface;
            for (uint32_t address : {device_address, vtable_address}) {
                const auto allocation = heap_allocations.find(address);
                if (allocation == heap_allocations.end()) continue;
                free_heap_blocks.push_back(allocation->second);
                heap_allocations.erase(allocation);
            }
            guest_d3d9_devices.erase(device);
            auto parent = guest_d3d9_interfaces.find(parent_address);
            if (parent != guest_d3d9_interfaces.end() &&
                parent->second.references > 0) {
                --parent->second.references;
            }
        }
        return return_kernel32_dword(remaining, api, 4);
    }

    int d3d9_device_get_number_of_swap_chains() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DDevice9::GetNumberOfSwapChains";
        uint32_t device_address = 0;
        if (!read_stack_argument(0, device_address, api)) return -1;
        if (guest_d3d9_devices.find(device_address) ==
            guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        return return_kernel32_dword(1, api, 4);
    }

    int d3d9_device_set_shader(bool pixel_shader) {
        const char* api = pixel_shader
            ? "d3d9.dll!IDirect3DDevice9::SetPixelShader"
            : "d3d9.dll!IDirect3DDevice9::SetVertexShader";
        uint32_t device_address = 0;
        uint32_t shader_address = 0;
        if (!read_stack_argument(0, device_address, api) ||
            !read_stack_argument(1, shader_address, api)) {
            return -1;
        }
        const auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        if (shader_address != 0) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 8);
        }
        if (pixel_shader) {
            device->second.pixel_shader_address = 0;
        } else {
            device->second.vertex_shader_address = 0;
        }
        return return_kernel32_dword(0, api, 8);
    }

    bool create_guest_d3d9_surface(uint32_t device_address,
                                   uint32_t render_target_index,
                                   bool depth_stencil,
                                   uint32_t& surface_address) {
        static constexpr std::array<const char*, 17> methods = {
            "QueryInterface", "AddRef", "Release", "GetDevice",
            "SetPrivateData", "GetPrivateData", "FreePrivateData",
            "SetPriority", "GetPriority", "PreLoad", "GetType",
            "GetContainer", "GetDesc", "LockRect", "UnlockRect",
            "GetDC", "ReleaseDC"};
        uint32_t vtable_address = 0;
        uint32_t object_address = 0;
        if (!allocate_guest_heap(kGuestProcessHeapHandle,
                                 methods.size() * sizeof(uint32_t),
                                 vtable_address) ||
            !allocate_guest_heap(kGuestProcessHeapHandle, sizeof(uint32_t),
                                 object_address)) {
            error = "could not allocate an IDirect3DSurface9";
            return false;
        }
        for (size_t index = 0; index < methods.size(); ++index) {
            uint32_t method_stub = 0;
            const std::string method_name =
                std::string("d3d9.dll!IDirect3DSurface9::") + methods[index];
            if (!allocate_dynamic_import_stub(method_name, method_stub) ||
                !write_guest_u32("ram", vtable_address + index * 4,
                                 method_stub)) {
                error = "could not create an IDirect3DSurface9 vtable";
                return false;
            }
        }
        if (!write_guest_u32("ram", object_address, vtable_address)) {
            error = "could not initialize an IDirect3DSurface9 object";
            return false;
        }
        guest_d3d9_surfaces.emplace(
            object_address,
            GuestD3D9Surface{vtable_address, device_address, 1,
                             render_target_index, depth_stencil});
        surface_address = object_address;
        return true;
    }

    int d3d9_device_get_render_target() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DDevice9::GetRenderTarget";
        uint32_t device_address = 0;
        uint32_t render_target_index = 0;
        uint32_t output_surface_address = 0;
        if (!read_stack_argument(0, device_address, api) ||
            !read_stack_argument(1, render_target_index, api) ||
            !read_stack_argument(2, output_surface_address, api)) {
            return -1;
        }
        auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        if (render_target_index > 3 || output_surface_address == 0 ||
            !valid_guest_pointer(output_surface_address, sizeof(uint32_t))) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 12);
        }
        uint32_t surface_address = 0;
        auto target = device->second.render_targets.find(render_target_index);
        if (target == device->second.render_targets.end()) {
            if (render_target_index != 0) {
                if (!write_guest_u32("ram", output_surface_address, 0))
                    return -1;
                return return_kernel32_dword(kD3dErrNotFound, api, 12);
            }
            if (!create_guest_d3d9_surface(device_address,
                                           render_target_index, false,
                                           surface_address)) {
                return -1;
            }
            device->second.render_targets.emplace(render_target_index,
                                                  surface_address);
        } else {
            surface_address = target->second;
        }
        auto surface = guest_d3d9_surfaces.find(surface_address);
        if (surface == guest_d3d9_surfaces.end()) {
            error = std::string(api) + " found an invalid render-target surface";
            return -1;
        }
        if (surface->second.references != UINT32_MAX)
            ++surface->second.references;
        if (!write_guest_u32("ram", output_surface_address, surface_address))
            return -1;
        return return_kernel32_dword(0, api, 12);
    }

    bool release_guest_d3d9_surface_reference(uint32_t surface_address,
                                               uint32_t& remaining) {
        auto surface = guest_d3d9_surfaces.find(surface_address);
        if (surface == guest_d3d9_surfaces.end() ||
            surface->second.references == 0) {
            return false;
        }
        remaining = --surface->second.references;
        if (remaining == 0) {
            free_guest_heap_address(surface->second.vtable_address);
            free_guest_heap_address(surface_address);
            guest_d3d9_surfaces.erase(surface);
        }
        return true;
    }

    int d3d9_device_set_render_target() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DDevice9::SetRenderTarget";
        uint32_t device_address = 0;
        uint32_t render_target_index = 0;
        uint32_t surface_address = 0;
        if (!read_stack_argument(0, device_address, api) ||
            !read_stack_argument(1, render_target_index, api) ||
            !read_stack_argument(2, surface_address, api)) {
            return -1;
        }
        auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        const auto surface = guest_d3d9_surfaces.find(surface_address);
        if (render_target_index > 3 || surface_address == 0 ||
            surface == guest_d3d9_surfaces.end() ||
            surface->second.device_address != device_address ||
            surface->second.depth_stencil ||
            surface->second.render_target_index != render_target_index) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 12);
        }
        const auto current =
            device->second.render_targets.find(render_target_index);
        if (current != device->second.render_targets.end() &&
            current->second != surface_address) {
            if (surface->second.references != UINT32_MAX)
                ++surface->second.references;
            const uint32_t old_surface_address = current->second;
            current->second = surface_address;
            uint32_t remaining = 0;
            (void)release_guest_d3d9_surface_reference(
                old_surface_address, remaining);
        } else if (current == device->second.render_targets.end()) {
            if (surface->second.references != UINT32_MAX)
                ++surface->second.references;
            device->second.render_targets.emplace(render_target_index,
                                                  surface_address);
        }
        return return_kernel32_dword(0, api, 12);
    }

    int d3d9_device_set_depth_stencil_surface() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DDevice9::SetDepthStencilSurface";
        uint32_t device_address = 0;
        uint32_t surface_address = 0;
        if (!read_stack_argument(0, device_address, api) ||
            !read_stack_argument(1, surface_address, api)) {
            return -1;
        }
        auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        if (surface_address != 0) {
            const auto surface = guest_d3d9_surfaces.find(surface_address);
            if (surface == guest_d3d9_surfaces.end() ||
                surface->second.device_address != device_address ||
                !surface->second.depth_stencil) {
                return return_kernel32_dword(kD3dErrInvalidCall, api, 8);
            }
        }
        const uint32_t previous_surface = device->second.depth_surface_address;
        if (previous_surface != surface_address) {
            if (surface_address != 0) {
                auto surface = guest_d3d9_surfaces.find(surface_address);
                if (surface->second.references != UINT32_MAX)
                    ++surface->second.references;
            }
            device->second.depth_surface_address = surface_address;
            uint32_t remaining = 0;
            if (previous_surface != 0) {
                (void)release_guest_d3d9_surface_reference(previous_surface,
                                                           remaining);
            }
        }
        return return_kernel32_dword(0, api, 8);
    }

    int d3d9_device_get_back_buffer() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DDevice9::GetBackBuffer";
        uint32_t device_address = 0;
        uint32_t swap_chain = 0;
        uint32_t back_buffer = 0;
        uint32_t type = 0;
        uint32_t output_surface_address = 0;
        if (!read_stack_argument(0, device_address, api) ||
            !read_stack_argument(1, swap_chain, api) ||
            !read_stack_argument(2, back_buffer, api) ||
            !read_stack_argument(3, type, api) ||
            !read_stack_argument(4, output_surface_address, api)) {
            return -1;
        }
        auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        if (swap_chain != 0 || back_buffer != 0 || type != 0 ||
            output_surface_address == 0 ||
            !valid_guest_pointer(output_surface_address, sizeof(uint32_t))) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 20);
        }
        uint32_t surface_address = 0;
        auto target = device->second.render_targets.find(0);
        if (target == device->second.render_targets.end()) {
            if (!create_guest_d3d9_surface(device_address, 0, false,
                                           surface_address)) {
                return -1;
            }
            device->second.render_targets.emplace(0, surface_address);
        } else {
            surface_address = target->second;
        }
        auto surface = guest_d3d9_surfaces.find(surface_address);
        if (surface == guest_d3d9_surfaces.end()) {
            error = std::string(api) + " found an invalid backbuffer surface";
            return -1;
        }
        if (surface->second.references != UINT32_MAX)
            ++surface->second.references;
        if (!write_guest_u32("ram", output_surface_address, surface_address))
            return -1;
        return return_kernel32_dword(0, api, 20);
    }

    int d3d9_device_get_depth_stencil_surface() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DDevice9::GetDepthStencilSurface";
        uint32_t device_address = 0;
        uint32_t output_surface_address = 0;
        if (!read_stack_argument(0, device_address, api) ||
            !read_stack_argument(1, output_surface_address, api)) {
            return -1;
        }
        auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        if (output_surface_address == 0 ||
            !valid_guest_pointer(output_surface_address, sizeof(uint32_t))) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 8);
        }
        if (device->second.presentation.enable_auto_depth_stencil == 0) {
            if (!write_guest_u32("ram", output_surface_address, 0))
                return -1;
            return return_kernel32_dword(kD3dErrNotFound, api, 8);
        }
        uint32_t surface_address = device->second.depth_surface_address;
        if (surface_address == 0) {
            if (!create_guest_d3d9_surface(device_address, 0, true,
                                           surface_address)) {
                return -1;
            }
            device->second.depth_surface_address = surface_address;
        }
        auto surface = guest_d3d9_surfaces.find(surface_address);
        if (surface == guest_d3d9_surfaces.end()) {
            error = std::string(api) + " found an invalid depth surface";
            return -1;
        }
        if (surface->second.references != UINT32_MAX)
            ++surface->second.references;
        if (!write_guest_u32("ram", output_surface_address, surface_address))
            return -1;
        return return_kernel32_dword(0, api, 8);
    }

    int d3d9_device_get_viewport() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DDevice9::GetViewport";
        uint32_t device_address = 0;
        uint32_t output_viewport_address = 0;
        if (!read_stack_argument(0, device_address, api) ||
            !read_stack_argument(1, output_viewport_address, api)) {
            return -1;
        }
        const auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        if (output_viewport_address == 0 ||
            !valid_guest_pointer(output_viewport_address, 6 * sizeof(uint32_t))) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 8);
        }
        auto viewport = device->second.viewport;
        if (viewport[2] == 0 || viewport[3] == 0) {
            viewport = {0, 0, device->second.presentation.back_buffer_width,
                        device->second.presentation.back_buffer_height, 0,
                        0x3f800000};
        }
        for (size_t index = 0; index < viewport.size(); ++index) {
            if (!write_guest_u32("ram", output_viewport_address + index * 4,
                                 viewport[index])) {
                return -1;
            }
        }
        return return_kernel32_dword(0, api, 8);
    }

    int d3d9_device_set_viewport() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DDevice9::SetViewport";
        uint32_t device_address = 0;
        uint32_t viewport_address = 0;
        if (!read_stack_argument(0, device_address, api) ||
            !read_stack_argument(1, viewport_address, api)) {
            return -1;
        }
        auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        if (viewport_address == 0 ||
            !valid_guest_pointer(viewport_address, 6 * sizeof(uint32_t))) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 8);
        }
        std::array<uint32_t, 6> viewport{};
        for (size_t index = 0; index < viewport.size(); ++index) {
            if (!read_guest_u32("ram", viewport_address + index * 4,
                                viewport[index])) {
                return -1;
            }
        }
        float min_z = 0.0f;
        float max_z = 0.0f;
        std::memcpy(&min_z, &viewport[4], sizeof(min_z));
        std::memcpy(&max_z, &viewport[5], sizeof(max_z));
        if (viewport[2] == 0 || viewport[3] == 0 ||
            !std::isfinite(min_z) || !std::isfinite(max_z) || min_z < 0.0f ||
            max_z > 1.0f || min_z > max_z) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 8);
        }
        device->second.viewport = viewport;
        return return_kernel32_dword(0, api, 8);
    }

    int d3d9_device_get_gamma_ramp() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DDevice9::GetGammaRamp";
        uint32_t device_address = 0;
        uint32_t swap_chain = 0;
        uint32_t ramp_address = 0;
        if (!read_stack_argument(0, device_address, api) ||
            !read_stack_argument(1, swap_chain, api) ||
            !read_stack_argument(2, ramp_address, api)) {
            return -1;
        }
        if (guest_d3d9_devices.find(device_address) ==
            guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        constexpr size_t kRampByteSize = 3 * 256 * sizeof(uint16_t);
        if (swap_chain != 0 || ramp_address == 0 ||
            !valid_guest_pointer(ramp_address, kRampByteSize)) {
            error = std::string(api) +
                    " received an unsupported swap chain or invalid ramp pointer";
            return -1;
        }

        std::array<uint8_t, kRampByteSize> ramp{};
        for (size_t channel = 0; channel < 3; ++channel) {
            for (size_t sample = 0; sample < 256; ++sample) {
                const uint16_t value = static_cast<uint16_t>(sample * 257);
                const size_t offset = (channel * 256 + sample) * 2;
                ramp[offset] = static_cast<uint8_t>(value);
                ramp[offset + 1] = static_cast<uint8_t>(value >> 8);
            }
        }
        if (!write_guest_bytes(ramp_address, ramp.data(), ramp.size(), api))
            return -1;
        return finish_stdcall(3 * sizeof(uint32_t), api) ? 0 : -1;
    }

    int d3d9_device_set_sampler_state() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DDevice9::SetSamplerState";
        uint32_t device_address = 0;
        uint32_t sampler = 0;
        uint32_t state = 0;
        uint32_t value = 0;
        if (!read_stack_argument(0, device_address, api) ||
            !read_stack_argument(1, sampler, api) ||
            !read_stack_argument(2, state, api) ||
            !read_stack_argument(3, value, api)) {
            return -1;
        }
        auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        if (sampler > 259 || state > 13) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 16);
        }
        const uint64_t key = static_cast<uint64_t>(sampler) << 32 | state;
        device->second.sampler_states[key] = value;
        return return_kernel32_dword(0, api, 16);
    }

    int d3d9_device_set_render_state() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DDevice9::SetRenderState";
        uint32_t device_address = 0;
        uint32_t state = 0;
        uint32_t value = 0;
        if (!read_stack_argument(0, device_address, api) ||
            !read_stack_argument(1, state, api) ||
            !read_stack_argument(2, value, api)) {
            return -1;
        }
        auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        if (state == 0 || state > 255) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 12);
        }
        device->second.render_states[state] = value;
        return return_kernel32_dword(0, api, 12);
    }

    int d3d9_device_begin_scene() {
        constexpr const char* api = "d3d9.dll!IDirect3DDevice9::BeginScene";
        uint32_t device_address = 0;
        if (!read_stack_argument(0, device_address, api)) return -1;
        auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        if (device->second.scene_active) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 4);
        }
        device->second.scene_active = true;
        return return_kernel32_dword(0, api, 4);
    }

    int d3d9_device_end_scene() {
        constexpr const char* api = "d3d9.dll!IDirect3DDevice9::EndScene";
        uint32_t device_address = 0;
        if (!read_stack_argument(0, device_address, api)) return -1;
        auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        if (!device->second.scene_active) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 4);
        }
        device->second.scene_active = false;
        return return_kernel32_dword(0, api, 4);
    }

    int d3d9_device_present() {
        constexpr const char* api = "d3d9.dll!IDirect3DDevice9::Present";
        std::array<uint32_t, 5> arguments{};
        for (size_t index = 0; index < arguments.size(); ++index) {
            if (!read_stack_argument(index, arguments[index], api)) return -1;
        }
        auto device = guest_d3d9_devices.find(arguments[0]);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        // The current retail startup probe presents only the default full
        // backbuffer. Other presentation parameters remain unsupported.
        if (arguments[1] != 0 || arguments[2] != 0 || arguments[3] != 0 ||
            arguments[4] != 0) {
            return return_kernel32_dword(kD3dErrNotAvailable, api, 20);
        }
        if (guest_d3d9_adapter_info.present != nullptr) {
            std::string callback_error;
            if (!guest_d3d9_adapter_info.present(
                    guest_d3d9_adapter_info.backend_context,
                    callback_error)) {
                if (!callback_error.empty()) {
                    error = std::string(api) + ": " + callback_error;
                }
                return return_kernel32_dword(kD3dErrNotAvailable, api, 20);
            }
        }
        if (device->second.present_request_count != UINT32_MAX)
            ++device->second.present_request_count;
        if (const char* trace = std::getenv("SHIFT_TRACE_D3D9_RESOURCES");
            trace != nullptr && *trace != '\0') {
            std::fprintf(stderr,
                         "shift_runtime: guest D3D9 Present request count=%u "
                         "device=0x%08x (%s)\n",
                         device->second.present_request_count, arguments[0],
                         guest_d3d9_adapter_info.present != nullptr
                             ? "queued for Vulkan frame"
                             : "accepted without Vulkan callback");
        }
        return return_kernel32_dword(0, api, 20);
    }

    int d3d9_device_get_render_state() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DDevice9::GetRenderState";
        uint32_t device_address = 0;
        uint32_t state = 0;
        uint32_t output_value_address = 0;
        if (!read_stack_argument(0, device_address, api) ||
            !read_stack_argument(1, state, api) ||
            !read_stack_argument(2, output_value_address, api)) {
            return -1;
        }
        const auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        if (state == 0 || state > 255 || output_value_address == 0 ||
            !valid_guest_pointer(output_value_address, sizeof(uint32_t))) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 12);
        }
        const auto value = device->second.render_states.find(state);
        if (!write_guest_u32("ram", output_value_address,
                             value == device->second.render_states.end()
                                 ? 0
                                 : value->second)) {
            return -1;
        }
        return return_kernel32_dword(0, api, 12);
    }

    void free_guest_heap_address(uint32_t address) {
        const auto allocation = heap_allocations.find(address);
        if (allocation == heap_allocations.end()) return;
        free_heap_blocks.push_back(allocation->second);
        heap_allocations.erase(allocation);
    }

    bool create_guest_d3d9_texture(uint32_t device_address,
                                   uint32_t width, uint32_t height,
                                   uint32_t levels, uint32_t usage,
                                   uint32_t format, uint32_t pool,
                                   uint32_t& texture_address) {
        static constexpr std::array<const char*, 22> methods = {
            "QueryInterface", "AddRef", "Release", "GetDevice",
            "SetPrivateData", "GetPrivateData", "FreePrivateData",
            "SetPriority", "GetPriority", "PreLoad", "GetType", "SetLOD",
            "GetLOD", "GetLevelCount", "SetAutoGenFilterType",
            "GetAutoGenFilterType", "GenerateMipSubLevels", "GetLevelDesc",
            "GetSurfaceLevel", "LockRect", "UnlockRect", "AddDirtyRect"};
        uint32_t vtable_address = 0;
        uint32_t object_address = 0;
        if (!allocate_guest_heap(kGuestProcessHeapHandle,
                                 methods.size() * sizeof(uint32_t),
                                 vtable_address) ||
            !allocate_guest_heap(kGuestProcessHeapHandle, sizeof(uint32_t),
                                 object_address)) {
            error = "D3DXCreateTexture could not allocate its guest object";
            free_guest_heap_address(vtable_address);
            return false;
        }
        for (size_t index = 0; index < methods.size(); ++index) {
            uint32_t method_stub = 0;
            const std::string method_name =
                std::string("d3d9.dll!IDirect3DTexture9::") + methods[index];
            if (!allocate_dynamic_import_stub(method_name, method_stub) ||
                !write_guest_u32("ram", vtable_address + index * 4,
                                 method_stub)) {
                error = "D3DXCreateTexture could not build its guest vtable";
                free_guest_heap_address(object_address);
                free_guest_heap_address(vtable_address);
                return false;
            }
        }
        if (!write_guest_u32("ram", object_address, vtable_address)) {
            error = "D3DXCreateTexture could not initialize its guest object";
            free_guest_heap_address(object_address);
            free_guest_heap_address(vtable_address);
            return false;
        }
        std::string backend_error;
        if (!guest_d3d9_adapter_info.create_texture(
                guest_d3d9_adapter_info.backend_context, object_address,
                device_address, width, height, levels, usage, format, pool,
                backend_error)) {
            error = std::move(backend_error);
            free_guest_heap_address(object_address);
            free_guest_heap_address(vtable_address);
            return false;
        }
        auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end()) {
            guest_d3d9_adapter_info.release_texture(
                guest_d3d9_adapter_info.backend_context, object_address);
            free_guest_heap_address(object_address);
            free_guest_heap_address(vtable_address);
            error = "D3DXCreateTexture lost its guest device";
            return false;
        }
        if (device->second.references != UINT32_MAX)
            ++device->second.references;
        guest_d3d9_textures.emplace(
            object_address,
            GuestD3D9Texture{vtable_address, device_address, 1, width, height,
                             levels, usage, format, pool});
        texture_address = object_address;
        return true;
    }

    bool create_guest_d3d9_vertex_buffer(uint32_t device_address,
                                         uint32_t size, uint32_t usage,
                                         uint32_t fvf, uint32_t pool,
                                         uint32_t& buffer_address) {
        static constexpr std::array<const char*, 14> methods = {
            "QueryInterface", "AddRef", "Release", "GetDevice",
            "SetPrivateData", "GetPrivateData", "FreePrivateData",
            "SetPriority", "GetPriority", "PreLoad", "GetType", "Lock",
            "Unlock", "GetDesc"};
        uint32_t vtable_address = 0;
        uint32_t object_address = 0;
        uint32_t data_address = 0;
        if (!allocate_guest_heap(kGuestProcessHeapHandle,
                                 methods.size() * sizeof(uint32_t),
                                 vtable_address) ||
            !allocate_guest_heap(kGuestProcessHeapHandle, sizeof(uint32_t),
                                 object_address) ||
            !allocate_guest_heap(kGuestProcessHeapHandle, size, data_address)) {
            error = "CreateVertexBuffer could not allocate its guest object";
            free_guest_heap_address(data_address);
            free_guest_heap_address(object_address);
            free_guest_heap_address(vtable_address);
            return false;
        }
        for (size_t index = 0; index < methods.size(); ++index) {
            uint32_t method_stub = 0;
            const std::string method_name =
                std::string("d3d9.dll!IDirect3DVertexBuffer9::") + methods[index];
            if (!allocate_dynamic_import_stub(method_name, method_stub) ||
                !write_guest_u32("ram", vtable_address + index * 4,
                                 method_stub)) {
                error = "CreateVertexBuffer could not build its guest vtable";
                free_guest_heap_address(data_address);
                free_guest_heap_address(object_address);
                free_guest_heap_address(vtable_address);
                return false;
            }
        }
        if (!write_guest_u32("ram", object_address, vtable_address)) {
            error = "CreateVertexBuffer could not initialize its guest object";
            free_guest_heap_address(data_address);
            free_guest_heap_address(object_address);
            free_guest_heap_address(vtable_address);
            return false;
        }
        std::string backend_error;
        if (!guest_d3d9_adapter_info.create_vertex_buffer(
                guest_d3d9_adapter_info.backend_context, object_address,
                device_address, size, usage, fvf, pool, backend_error)) {
            error = std::move(backend_error);
            free_guest_heap_address(data_address);
            free_guest_heap_address(object_address);
            free_guest_heap_address(vtable_address);
            return false;
        }
        auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end()) {
            guest_d3d9_adapter_info.release_vertex_buffer(
                guest_d3d9_adapter_info.backend_context, object_address);
            free_guest_heap_address(data_address);
            free_guest_heap_address(object_address);
            free_guest_heap_address(vtable_address);
            error = "CreateVertexBuffer lost its guest device";
            return false;
        }
        if (device->second.references != UINT32_MAX)
            ++device->second.references;
        guest_d3d9_vertex_buffers.emplace(
            object_address,
            GuestD3D9VertexBuffer{vtable_address, device_address, data_address,
                                  1, size, usage, fvf, pool});
        buffer_address = object_address;
        return true;
    }

    int d3d9_device_create_vertex_buffer() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DDevice9::CreateVertexBuffer";
        std::array<uint32_t, 7> arguments{};
        for (uint32_t index = 0; index < arguments.size(); ++index) {
            if (!read_stack_argument(index, arguments[index], api)) return -1;
        }
        const uint32_t device_address = arguments[0];
        const uint32_t size = arguments[1];
        const uint32_t usage = arguments[2];
        const uint32_t fvf = arguments[3];
        const uint32_t pool = arguments[4];
        const uint32_t output_buffer_address = arguments[5];
        if (guest_d3d9_devices.find(device_address) == guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        if (output_buffer_address == 0 || size == 0 ||
            !valid_guest_pointer(output_buffer_address, sizeof(uint32_t))) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 28);
        }
        if (!write_guest_u32("ram", output_buffer_address, 0)) return -1;
        if (pool != kD3dPoolDefault ||
            guest_d3d9_adapter_info.create_vertex_buffer == nullptr ||
            guest_d3d9_adapter_info.update_vertex_buffer == nullptr ||
            guest_d3d9_adapter_info.release_vertex_buffer == nullptr) {
            return return_kernel32_dword(kD3dErrNotAvailable, api, 28);
        }
        uint32_t buffer_address = 0;
        if (!create_guest_d3d9_vertex_buffer(device_address, size, usage, fvf,
                                             pool, buffer_address)) {
            return return_kernel32_dword(kD3dErrNotAvailable, api, 28);
        }
        if (!write_guest_u32("ram", output_buffer_address, buffer_address))
            return -1;
        return return_kernel32_dword(0, api, 28);
    }

    int d3d9_vertex_buffer_add_ref() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DVertexBuffer9::AddRef";
        uint32_t buffer_address = 0;
        if (!read_stack_argument(0, buffer_address, api)) return -1;
        auto buffer = guest_d3d9_vertex_buffers.find(buffer_address);
        if (buffer == guest_d3d9_vertex_buffers.end()) {
            error = std::string(api) + " received an invalid buffer pointer";
            return -1;
        }
        if (buffer->second.references != UINT32_MAX)
            ++buffer->second.references;
        return return_kernel32_dword(buffer->second.references, api, 4);
    }

    int d3d9_vertex_buffer_release() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DVertexBuffer9::Release";
        uint32_t buffer_address = 0;
        if (!read_stack_argument(0, buffer_address, api)) return -1;
        auto buffer = guest_d3d9_vertex_buffers.find(buffer_address);
        if (buffer == guest_d3d9_vertex_buffers.end() ||
            buffer->second.references == 0) {
            error = std::string(api) + " received an invalid buffer pointer";
            return -1;
        }
        const uint32_t remaining = --buffer->second.references;
        if (remaining == 0) {
            const auto device_address = buffer->second.device_address;
            guest_d3d9_adapter_info.release_vertex_buffer(
                guest_d3d9_adapter_info.backend_context, buffer_address);
            const auto vtable_address = buffer->second.vtable_address;
            const auto data_address = buffer->second.data_address;
            guest_d3d9_vertex_buffers.erase(buffer);
            free_guest_heap_address(data_address);
            free_guest_heap_address(buffer_address);
            free_guest_heap_address(vtable_address);
            const auto device = guest_d3d9_devices.find(device_address);
            if (device != guest_d3d9_devices.end() &&
                device->second.references > 0) {
                --device->second.references;
            }
        }
        return return_kernel32_dword(remaining, api, 4);
    }

    int d3d9_vertex_buffer_get_device() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DVertexBuffer9::GetDevice";
        uint32_t buffer_address = 0;
        uint32_t output_device_address = 0;
        if (!read_stack_argument(0, buffer_address, api) ||
            !read_stack_argument(1, output_device_address, api)) {
            return -1;
        }
        const auto buffer = guest_d3d9_vertex_buffers.find(buffer_address);
        if (buffer == guest_d3d9_vertex_buffers.end()) {
            error = std::string(api) + " received an invalid buffer pointer";
            return -1;
        }
        if (output_device_address == 0 ||
            !valid_guest_pointer(output_device_address, sizeof(uint32_t))) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 8);
        }
        const auto device = guest_d3d9_devices.find(buffer->second.device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " found an invalid parent device";
            return -1;
        }
        if (!write_guest_u32("ram", output_device_address,
                             buffer->second.device_address)) {
            return -1;
        }
        if (device->second.references != UINT32_MAX)
            ++device->second.references;
        return return_kernel32_dword(0, api, 8);
    }

    int d3d9_vertex_buffer_lock() {
        constexpr const char* api = "d3d9.dll!IDirect3DVertexBuffer9::Lock";
        uint32_t buffer_address = 0;
        uint32_t offset = 0;
        uint32_t size = 0;
        uint32_t output_data_address = 0;
        uint32_t flags = 0;
        if (!read_stack_argument(0, buffer_address, api) ||
            !read_stack_argument(1, offset, api) ||
            !read_stack_argument(2, size, api) ||
            !read_stack_argument(3, output_data_address, api) ||
            !read_stack_argument(4, flags, api)) {
            return -1;
        }
        auto buffer = guest_d3d9_vertex_buffers.find(buffer_address);
        if (buffer == guest_d3d9_vertex_buffers.end()) {
            error = std::string(api) + " received an invalid buffer pointer";
            return -1;
        }
        if (buffer->second.locked || offset > buffer->second.size ||
            (size != 0 && size > buffer->second.size - offset) ||
            output_data_address == 0 ||
            !valid_guest_pointer(output_data_address, sizeof(uint32_t))) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 20);
        }
        (void)flags;
        const uint32_t lock_size = size == 0 ? buffer->second.size - offset : size;
        if (lock_size == 0) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 20);
        }
        const uint32_t data_address = buffer->second.data_address + offset;
        if (!write_guest_u32("ram", output_data_address, data_address)) return -1;
        buffer->second.locked = true;
        buffer->second.lock_offset = offset;
        buffer->second.lock_size = lock_size;
        return return_kernel32_dword(0, api, 20);
    }

    int d3d9_vertex_buffer_unlock() {
        constexpr const char* api = "d3d9.dll!IDirect3DVertexBuffer9::Unlock";
        uint32_t buffer_address = 0;
        if (!read_stack_argument(0, buffer_address, api)) return -1;
        auto buffer = guest_d3d9_vertex_buffers.find(buffer_address);
        if (buffer == guest_d3d9_vertex_buffers.end()) {
            error = std::string(api) + " received an invalid buffer pointer";
            return -1;
        }
        if (!buffer->second.locked) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 4);
        }
        std::vector<uint8_t> data(buffer->second.lock_size);
        for (size_t offset = 0; offset < data.size();) {
            const size_t count = std::min<size_t>(
                data.size() - offset, kMaximumPcodeValueSize);
            if (!read_guest("ram", buffer->second.data_address +
                                      buffer->second.lock_offset + offset,
                            count, data.data() + offset)) {
                return -1;
            }
            offset += count;
        }
        std::string backend_error;
        if (!guest_d3d9_adapter_info.update_vertex_buffer(
                guest_d3d9_adapter_info.backend_context, buffer_address,
                buffer->second.lock_offset, data.data(), data.size(),
                backend_error)) {
            error = std::move(backend_error);
            return return_kernel32_dword(kD3dErrNotAvailable, api, 4);
        }
        buffer->second.locked = false;
        buffer->second.lock_offset = 0;
        buffer->second.lock_size = 0;
        return return_kernel32_dword(0, api, 4);
    }

    int d3d9_vertex_buffer_get_desc() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DVertexBuffer9::GetDesc";
        uint32_t buffer_address = 0;
        uint32_t description_address = 0;
        if (!read_stack_argument(0, buffer_address, api) ||
            !read_stack_argument(1, description_address, api)) {
            return -1;
        }
        const auto buffer = guest_d3d9_vertex_buffers.find(buffer_address);
        if (buffer == guest_d3d9_vertex_buffers.end()) {
            error = std::string(api) + " received an invalid buffer pointer";
            return -1;
        }
        if (description_address == 0 ||
            !valid_guest_pointer(description_address, 6 * sizeof(uint32_t))) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 8);
        }
        const std::array<uint32_t, 6> description = {
            0, 6, buffer->second.usage, buffer->second.pool,
            buffer->second.size, buffer->second.fvf};
        for (size_t index = 0; index < description.size(); ++index) {
            if (!write_guest_u32("ram", description_address + index * 4,
                                 description[index])) {
                return -1;
            }
        }
        return return_kernel32_dword(0, api, 8);
    }

    int d3dx_create_texture() {
        constexpr const char* api = "d3dx9_41.dll!D3DXCreateTexture";
        std::array<uint32_t, 8> arguments{};
        for (uint32_t index = 0; index < arguments.size(); ++index) {
            if (!read_stack_argument(index, arguments[index], api)) return -1;
        }
        const uint32_t wrapper_address = arguments[0];
        const uint32_t width = arguments[1];
        const uint32_t height = arguments[2];
        const uint32_t levels = arguments[3];
        const uint32_t usage = arguments[4];
        const uint32_t format = arguments[5];
        const uint32_t pool = arguments[6];
        const uint32_t output_texture_address = arguments[7];
        if (output_texture_address == 0 ||
            !valid_guest_pointer(output_texture_address, sizeof(uint32_t))) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 32);
        }
        if (!write_guest_u32("ram", output_texture_address, 0)) return -1;
        if (!valid_guest_pointer(wrapper_address, 3 * sizeof(uint32_t))) {
            return return_kernel32_dword(kD3dErrInvalidDevice, api, 32);
        }
        uint32_t wrapper_vtable = 0;
        uint32_t device_address = 0;
        if (!read_guest_u32("ram", wrapper_address, wrapper_vtable) ||
            !read_guest_u32("ram", wrapper_address + 8, device_address) ||
            wrapper_vtable == 0 ||
            guest_d3d9_devices.find(device_address) ==
                guest_d3d9_devices.end()) {
            return return_kernel32_dword(kD3dErrInvalidDevice, api, 32);
        }
        if (width == 0 || height == 0 || levels != 1 ||
            usage != kD3dUsageRenderTarget ||
            format != kD3dFormatA8R8G8B8 || pool != kD3dPoolDefault) {
            return return_kernel32_dword(kD3dErrNotAvailable, api, 32);
        }
        if (guest_d3d9_adapter_info.create_texture == nullptr ||
            guest_d3d9_adapter_info.release_texture == nullptr) {
            return return_kernel32_dword(kD3dErrNotAvailable, api, 32);
        }
        uint32_t texture_address = 0;
        if (!create_guest_d3d9_texture(device_address, width, height, levels,
                                       usage, format, pool, texture_address)) {
            return return_kernel32_dword(kD3dErrNotAvailable, api, 32);
        }
        if (!write_guest_u32("ram", output_texture_address, texture_address))
            return -1;
        return return_kernel32_dword(0, api, 32);
    }

    int d3d9_texture_add_ref() {
        constexpr const char* api = "d3d9.dll!IDirect3DTexture9::AddRef";
        uint32_t texture_address = 0;
        if (!read_stack_argument(0, texture_address, api)) return -1;
        auto texture = guest_d3d9_textures.find(texture_address);
        if (texture == guest_d3d9_textures.end()) {
            error = std::string(api) + " received an invalid texture pointer";
            return -1;
        }
        if (texture->second.references != UINT32_MAX)
            ++texture->second.references;
        return return_kernel32_dword(texture->second.references, api, 4);
    }

    int d3d9_texture_release() {
        constexpr const char* api = "d3d9.dll!IDirect3DTexture9::Release";
        uint32_t texture_address = 0;
        if (!read_stack_argument(0, texture_address, api)) return -1;
        auto texture = guest_d3d9_textures.find(texture_address);
        if (texture == guest_d3d9_textures.end() ||
            texture->second.references == 0) {
            error = std::string(api) + " received an invalid texture pointer";
            return -1;
        }
        const uint32_t remaining = --texture->second.references;
        if (remaining == 0) {
            const uint32_t vtable_address = texture->second.vtable_address;
            const uint32_t device_address = texture->second.device_address;
            guest_d3d9_adapter_info.release_texture(
                guest_d3d9_adapter_info.backend_context, texture_address);
            guest_d3d9_textures.erase(texture);
            free_guest_heap_address(texture_address);
            free_guest_heap_address(vtable_address);
            const auto device = guest_d3d9_devices.find(device_address);
            if (device != guest_d3d9_devices.end() &&
                device->second.references > 0) {
                --device->second.references;
            }
        }
        return return_kernel32_dword(remaining, api, 4);
    }

    int d3d9_texture_get_device() {
        constexpr const char* api = "d3d9.dll!IDirect3DTexture9::GetDevice";
        uint32_t texture_address = 0;
        uint32_t output_device_address = 0;
        if (!read_stack_argument(0, texture_address, api) ||
            !read_stack_argument(1, output_device_address, api)) {
            return -1;
        }
        const auto texture = guest_d3d9_textures.find(texture_address);
        if (texture == guest_d3d9_textures.end()) {
            error = std::string(api) + " received an invalid texture pointer";
            return -1;
        }
        if (output_device_address == 0 ||
            !valid_guest_pointer(output_device_address, sizeof(uint32_t))) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 8);
        }
        const auto device =
            guest_d3d9_devices.find(texture->second.device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " found an invalid parent device";
            return -1;
        }
        if (!write_guest_u32("ram", output_device_address,
                             texture->second.device_address)) {
            return -1;
        }
        if (device->second.references != UINT32_MAX)
            ++device->second.references;
        return return_kernel32_dword(0, api, 8);
    }

    int d3d9_texture_get_level_count() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DTexture9::GetLevelCount";
        uint32_t texture_address = 0;
        if (!read_stack_argument(0, texture_address, api)) return -1;
        const auto texture = guest_d3d9_textures.find(texture_address);
        if (texture == guest_d3d9_textures.end()) {
            error = std::string(api) + " received an invalid texture pointer";
            return -1;
        }
        return return_kernel32_dword(texture->second.levels, api, 4);
    }

    int d3d9_texture_get_level_desc() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DTexture9::GetLevelDesc";
        uint32_t texture_address = 0;
        uint32_t level = 0;
        uint32_t description_address = 0;
        if (!read_stack_argument(0, texture_address, api) ||
            !read_stack_argument(1, level, api) ||
            !read_stack_argument(2, description_address, api)) {
            return -1;
        }
        const auto texture = guest_d3d9_textures.find(texture_address);
        if (texture == guest_d3d9_textures.end()) {
            error = std::string(api) + " received an invalid texture pointer";
            return -1;
        }
        if (level >= texture->second.levels || description_address == 0 ||
            !valid_guest_pointer(description_address, 8 * sizeof(uint32_t))) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 12);
        }
        const std::array<uint32_t, 8> description = {
            texture->second.format, 3, texture->second.usage,
            texture->second.pool, 0, 0, texture->second.width,
            texture->second.height};
        for (size_t index = 0; index < description.size(); ++index) {
            if (!write_guest_u32("ram", description_address + index * 4,
                                 description[index])) {
                return -1;
            }
        }
        return return_kernel32_dword(0, api, 12);
    }

    int d3d9_surface_add_ref() {
        constexpr const char* api = "d3d9.dll!IDirect3DSurface9::AddRef";
        uint32_t surface_address = 0;
        if (!read_stack_argument(0, surface_address, api)) return -1;
        auto surface = guest_d3d9_surfaces.find(surface_address);
        if (surface == guest_d3d9_surfaces.end()) {
            error = std::string(api) + " received an invalid surface pointer";
            return -1;
        }
        if (surface->second.references != UINT32_MAX)
            ++surface->second.references;
        return return_kernel32_dword(surface->second.references, api, 4);
    }

    int d3d9_surface_release() {
        constexpr const char* api = "d3d9.dll!IDirect3DSurface9::Release";
        uint32_t surface_address = 0;
        if (!read_stack_argument(0, surface_address, api)) return -1;
        uint32_t remaining = 0;
        if (!release_guest_d3d9_surface_reference(surface_address, remaining)) {
            error = std::string(api) + " received an invalid surface pointer";
            return -1;
        }
        return return_kernel32_dword(remaining, api, 4);
    }

    int d3d9_surface_get_desc() {
        constexpr const char* api = "d3d9.dll!IDirect3DSurface9::GetDesc";
        uint32_t surface_address = 0;
        uint32_t description_address = 0;
        if (!read_stack_argument(0, surface_address, api) ||
            !read_stack_argument(1, description_address, api)) {
            return -1;
        }
        const auto surface = guest_d3d9_surfaces.find(surface_address);
        if (surface == guest_d3d9_surfaces.end()) {
            error = std::string(api) + " received an invalid surface pointer";
            return -1;
        }
        if (description_address == 0 ||
            !valid_guest_pointer(description_address, 8 * sizeof(uint32_t))) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 8);
        }
        const auto device =
            guest_d3d9_devices.find(surface->second.device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " found an invalid parent device";
            return -1;
        }
        const auto& presentation = device->second.presentation;
        // D3DSURFACE_DESC: Format, Type, Usage, Pool, multisample type/quality,
        // Width, Height. Backbuffer and auto-depth surfaces use D3DPOOL_DEFAULT.
        const std::array<uint32_t, 8> description = {
            surface->second.depth_stencil
                ? presentation.auto_depth_stencil_format
                : presentation.back_buffer_format,
            1,
            surface->second.depth_stencil ? 2u : 1u,
            0,
            presentation.multisample_type,
            presentation.multisample_quality,
            presentation.back_buffer_width,
            presentation.back_buffer_height};
        for (size_t index = 0; index < description.size(); ++index) {
            if (!write_guest_u32("ram", description_address + index * 4,
                                 description[index])) {
                return -1;
            }
        }
        return return_kernel32_dword(0, api, 8);
    }

    int d3d9_device_clear() {
        constexpr const char* api = "d3d9.dll!IDirect3DDevice9::Clear";
        uint32_t device_address = 0;
        uint32_t rect_count = 0;
        uint32_t rects_address = 0;
        uint32_t flags = 0;
        uint32_t color = 0;
        uint32_t depth_bits = 0;
        uint32_t stencil = 0;
        if (!read_stack_argument(0, device_address, api) ||
            !read_stack_argument(1, rect_count, api) ||
            !read_stack_argument(2, rects_address, api) ||
            !read_stack_argument(3, flags, api) ||
            !read_stack_argument(4, color, api) ||
            !read_stack_argument(5, depth_bits, api) ||
            !read_stack_argument(6, stencil, api)) {
            return -1;
        }
        auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        constexpr uint32_t clear_target = 0x1;
        constexpr uint32_t clear_zbuffer = 0x2;
        constexpr uint32_t clear_stencil = 0x4;
        constexpr uint32_t supported_flags =
            clear_target | clear_zbuffer | clear_stencil;
        if (flags == 0 || (flags & ~supported_flags) != 0 ||
            (rect_count != 0 &&
             (rects_address == 0 ||
              rect_count > (UINT32_MAX - rects_address) / 16 ||
              !valid_guest_pointer(rects_address, rect_count * 16))) ||
            ((flags & (clear_zbuffer | clear_stencil)) != 0 &&
             device->second.presentation.enable_auto_depth_stencil == 0)) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 28);
        }
        if (guest_d3d9_adapter_info.clear != nullptr) {
            std::string callback_error;
            if (!guest_d3d9_adapter_info.clear(
                    guest_d3d9_adapter_info.backend_context, flags, color,
                    depth_bits, stencil, rect_count, callback_error)) {
                if (!callback_error.empty()) {
                    error = std::string(api) + ": " + callback_error;
                }
                return return_kernel32_dword(kD3dErrNotAvailable, api, 28);
            }
        }
        if (device->second.clear_call_count != UINT32_MAX)
            ++device->second.clear_call_count;
        device->second.last_clear_flags = flags;
        device->second.last_clear_color = color;
        device->second.last_clear_depth_bits = depth_bits;
        device->second.last_clear_stencil = stencil;
        device->second.last_clear_rect_count = rect_count;
        return return_kernel32_dword(0, api, 28);
    }

    int d3d9_device_get_texture() {
        constexpr const char* api =
            "d3d9.dll!IDirect3DDevice9::GetTexture";
        uint32_t device_address = 0;
        uint32_t stage = 0;
        uint32_t output_texture_address = 0;
        if (!read_stack_argument(0, device_address, api) ||
            !read_stack_argument(1, stage, api) ||
            !read_stack_argument(2, output_texture_address, api)) {
            return -1;
        }
        const auto device = guest_d3d9_devices.find(device_address);
        if (device == guest_d3d9_devices.end()) {
            error = std::string(api) + " received an invalid device pointer";
            return -1;
        }
        if (stage > 259 || output_texture_address == 0 ||
            !valid_guest_pointer(output_texture_address, sizeof(uint32_t))) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 12);
        }
        const auto texture = device->second.textures.find(stage);
        const uint32_t texture_address =
            texture == device->second.textures.end() ? 0 : texture->second;
        if (!write_guest_u32("ram", output_texture_address,
                             texture_address)) {
            return -1;
        }
        return return_kernel32_dword(0, api, 12);
    }

    int d3d9_get_adapter_identifier() {
        constexpr const char* api =
            "d3d9.dll!IDirect3D9::GetAdapterIdentifier";
        uint32_t interface_address = 0;
        uint32_t adapter = 0;
        uint32_t flags = 0;
        uint32_t identifier_address = 0;
        if (!read_stack_argument(0, interface_address, api) ||
            !read_stack_argument(1, adapter, api) ||
            !read_stack_argument(2, flags, api) ||
            !read_stack_argument(3, identifier_address, api)) {
            return -1;
        }
        const auto interface = guest_d3d9_interfaces.find(interface_address);
        if (interface == guest_d3d9_interfaces.end()) {
            error = std::string(api) + " received an invalid interface pointer";
            return -1;
        }
        if (adapter != 0 || flags != 0 || identifier_address == 0 ||
            identifier_address >
                UINT32_MAX - (kD3dAdapterIdentifier9Size - 1) ||
            !valid_guest_pointer(identifier_address,
                                 kD3dAdapterIdentifier9Size)) {
            return return_kernel32_dword(kD3dErrInvalidCall, api, 16);
        }
        if (!guest_d3d9_adapter_info_available) {
            return return_kernel32_dword(kD3dErrNotAvailable, api, 16);
        }

        std::array<uint8_t, kD3dAdapterIdentifier9Size> identifier{};
        const size_t description_size = std::min(
            guest_d3d9_adapter_info.description.size(), size_t{511});
        std::copy_n(guest_d3d9_adapter_info.description.data(),
                    description_size, identifier.data() + 512);
        const auto store_u32 = [&identifier](size_t offset, uint32_t value) {
            for (size_t byte = 0; byte < sizeof(value); ++byte) {
                identifier[offset + byte] =
                    static_cast<uint8_t>(value >> (byte * 8));
            }
        };
        store_u32(1064, guest_d3d9_adapter_info.vendor_id);
        store_u32(1068, guest_d3d9_adapter_info.device_id);
        if (!write_guest_bytes(identifier_address, identifier.data(),
                               identifier.size(), api)) {
            return -1;
        }
        return return_kernel32_dword(0, api, 16);
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
        if (signaled) wake_guest_event_waiters(handle, event->second);
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
        if (guest_semaphores.erase(handle) != 0) {
            for (auto name = guest_named_semaphores.begin();
                 name != guest_named_semaphores.end();) {
                if (name->second == handle) {
                    name = guest_named_semaphores.erase(name);
                } else {
                    ++name;
                }
            }
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
        std::filesystem::path candidate;
        if (!make_guest_path_candidate(path, candidate, api)) return false;
        std::error_code error_code;
        resolved = std::filesystem::canonical(candidate, error_code);
        if (error_code) {
            guest_last_error =
                error_code == std::errc::no_such_file_or_directory ? 2 : 5;
            return false;
        }
        if (!path_is_within_guest_root(resolved)) {
            guest_last_error = 5;
            return false;
        }
        (void)api;
        return true;
    }

    bool path_is_within_guest_root(
        const std::filesystem::path& path) const {
        const std::filesystem::path normalized = path.lexically_normal();
        const std::filesystem::path relative =
            normalized.lexically_relative(guest_filesystem_root);
        return normalized == guest_filesystem_root ||
               (!relative.empty() && !relative.is_absolute() &&
                *relative.begin() != "..");
    }

    bool make_guest_path_candidate(const std::string& path,
                                   std::filesystem::path& candidate,
                                   const char* api,
                                   bool preserve_final_component = false) {
        if (path.empty()) {
            guest_last_error = 3;
            return false;
        }
        if (path.size() >= kWindowsMaxPath) {
            guest_last_error = 206;
            return false;
        }

        std::string portable_path = path;
        std::replace(portable_path.begin(), portable_path.end(), '\\', '/');
        std::filesystem::path base = guest_current_host_directory;
        std::string relative_path = portable_path;
        if (portable_path.size() >= 2 &&
            std::isalpha(static_cast<unsigned char>(portable_path[0])) &&
            portable_path[1] == ':') {
            if (std::tolower(static_cast<unsigned char>(portable_path[0])) !=
                'c') {
                guest_last_error = 15;
                return false;
            }
            relative_path.erase(0, 2);
            if (!relative_path.empty() && relative_path.front() == '/') {
                base = guest_filesystem_root;
                relative_path.erase(0, 1);
            }
        } else if (!portable_path.empty() && portable_path.front() == '/') {
            if (portable_path.size() >= 2 && portable_path[1] == '/') {
                guest_last_error = 123;
                return false;
            }
            base = guest_filesystem_root;
            relative_path.erase(0, 1);
        }
        if (relative_path.find(':') != std::string::npos) {
            guest_last_error = 123;
            return false;
        }

        candidate = (base / std::filesystem::path(relative_path)).lexically_normal();
        if (!path_is_within_guest_root(candidate)) {
            guest_last_error = 5;
            return false;
        }

        std::filesystem::path case_resolved = guest_filesystem_root;
        const std::filesystem::path relative_candidate =
            candidate.lexically_relative(guest_filesystem_root);
        for (auto component = relative_candidate.begin();
             component != relative_candidate.end(); ++component) {
            if (*component == ".") continue;
            const bool final_component =
                std::next(component) == relative_candidate.end();
            std::filesystem::path match = case_resolved / *component;
            std::error_code component_error;
            const bool exact_match =
                std::filesystem::exists(match, component_error) &&
                !component_error;
            if (!exact_match) {
                component_error.clear();
                std::filesystem::path folded_match;
                std::filesystem::directory_iterator entry(case_resolved,
                                                           component_error);
                const auto fold_ascii = [](std::string value) {
                    for (char& character : value) {
                        if (character >= 'A' && character <= 'Z')
                            character = static_cast<char>(character + ('a' - 'A'));
                    }
                    return value;
                };
                const std::string wanted = fold_ascii(component->string());
                for (const std::filesystem::directory_iterator end;
                     !component_error && entry != end;
                     entry.increment(component_error)) {
                    if (fold_ascii(entry->path().filename().string()) != wanted)
                        continue;
                    if (!folded_match.empty()) {
                        guest_last_error = 5;
                        return false;
                    }
                    folded_match = entry->path().filename();
                }
                if (component_error) {
                    match = case_resolved / *component;
                    for (auto remaining = std::next(component);
                         remaining != relative_candidate.end(); ++remaining) {
                        match /= *remaining;
                    }
                    case_resolved = std::move(match);
                    break;
                }
                if (!folded_match.empty()) {
                    match = case_resolved / folded_match;
                } else if (!preserve_final_component || !final_component) {
                    for (auto remaining = component;
                         remaining != relative_candidate.end(); ++remaining) {
                        case_resolved /= *remaining;
                    }
                    break;
                }
            }

            if (preserve_final_component && final_component) {
                case_resolved = std::move(match);
                continue;
            }
            std::filesystem::path canonical_component =
                std::filesystem::canonical(match, component_error);
            if (component_error) {
                guest_last_error = component_error == std::errc::permission_denied
                                       ? 5
                                       : 3;
                return false;
            }
            if (!path_is_within_guest_root(canonical_component)) {
                guest_last_error = 5;
                return false;
            }
            case_resolved = std::move(canonical_component);
        }
        candidate = std::move(case_resolved);
        std::error_code error_code;
        if (preserve_final_component) {
            const std::filesystem::path parent =
                std::filesystem::canonical(candidate.parent_path(), error_code);
            if (!error_code) {
                const std::filesystem::path filename = candidate.filename();
                if (filename.empty() || filename == "." || filename == "..") {
                    guest_last_error = 5;
                    return false;
                }
                candidate = parent / filename;
            }
        } else {
            candidate = std::filesystem::weakly_canonical(candidate, error_code);
        }
        if (error_code) {
            guest_last_error = error_code == std::errc::permission_denied ? 5 : 3;
            return false;
        }
        if (!path_is_within_guest_root(candidate)) {
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

    int delete_file_a() {
        constexpr const char* api = "KERNEL32.dll!DeleteFileA";
        uint32_t path_address = 0;
        if (!read_stack_argument(0, path_address, api)) return -1;
        if (path_address == 0) {
            guest_last_error = 87;
            return return_kernel32_dword(0, api, 4);
        }

        std::string guest_path;
        if (!read_guest_ascii(path_address, guest_path, api)) return -1;
        std::filesystem::path host_path;
        if (!make_guest_path_candidate(guest_path, host_path, api, true))
            return return_kernel32_dword(0, api, 4);

        struct stat file_status {};
        if (::lstat(host_path.c_str(), &file_status) != 0) {
            guest_last_error = errno == ENOENT ? 2 :
                               errno == ENOTDIR ? 3 :
                               errno == EACCES || errno == EPERM ? 5 : 31;
            return return_kernel32_dword(0, api, 4);
        }
        if (S_ISDIR(file_status.st_mode) ||
            (file_status.st_mode & (S_IWUSR | S_IWGRP | S_IWOTH)) == 0) {
            guest_last_error = 5;
            return return_kernel32_dword(0, api, 4);
        }
        if (::unlink(host_path.c_str()) != 0) {
            guest_last_error = errno == ENOENT ? 2 :
                               errno == ENOTDIR ? 3 :
                               errno == EACCES || errno == EPERM ||
                                       errno == EISDIR || errno == EROFS
                                   ? 5
                                   : 31;
            return return_kernel32_dword(0, api, 4);
        }
        guest_last_error = 0;
        return return_kernel32_dword(1, api, 4);
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

    int read_file_ex() {
        constexpr const char* api = "KERNEL32.dll!ReadFileEx";
        uint32_t handle = 0;
        uint32_t output_address = 0;
        uint32_t bytes_to_read = 0;
        uint32_t overlapped = 0;
        uint32_t completion_routine = 0;
        if (!read_stack_argument(0, handle, api) ||
            !read_stack_argument(1, output_address, api) ||
            !read_stack_argument(2, bytes_to_read, api) ||
            !read_stack_argument(3, overlapped, api) ||
            !read_stack_argument(4, completion_routine, api)) {
            return -1;
        }
        const auto file = guest_files.find(handle);
        if (file == guest_files.end() || completion_routine == 0 ||
            overlapped == 0 || !valid_guest_pointer(overlapped, 20) ||
            bytes_to_read > kMaximumGuestFileReadBytes ||
            (bytes_to_read != 0 &&
             !valid_guest_pointer(output_address, bytes_to_read))) {
            guest_last_error = file == guest_files.end() ? 6 : 87;
            return return_kernel32_dword(0, api, 20);
        }

        GuestThread* thread =
            guest_execution_state(current_guest_thread_handle);
        if (!thread || thread->io_completions.size() >= 1024) {
            error = std::string(api) +
                    " has no available guest completion queue";
            return -1;
        }
        uint32_t offset_low = 0;
        uint32_t offset_high = 0;
        if (!read_guest_u32("ram", static_cast<uint64_t>(overlapped) + 8,
                            offset_low) ||
            !read_guest_u32("ram", static_cast<uint64_t>(overlapped) + 12,
                            offset_high)) {
            guest_last_error = 87;
            return return_kernel32_dword(0, api, 20);
        }
        const uint64_t file_offset =
            (static_cast<uint64_t>(offset_high) << 32) | offset_low;
        const uint64_t maximum_offset = static_cast<uint64_t>(
            std::numeric_limits<off_t>::max());
        if (file_offset > maximum_offset ||
            bytes_to_read > maximum_offset - file_offset) {
            guest_last_error = 87;
            return return_kernel32_dword(0, api, 20);
        }

        std::vector<uint8_t> bytes(bytes_to_read);
        size_t total_read = 0;
        uint32_t completion_error = 0;
        while (total_read < bytes.size()) {
            const ssize_t count = ::pread(
                file->second.descriptor, bytes.data() + total_read,
                bytes.size() - total_read,
                static_cast<off_t>(file_offset + total_read));
            if (count < 0 && errno == EINTR) continue;
            if (count < 0) {
                completion_error = 31;
                break;
            }
            if (count == 0) break;
            total_read += static_cast<size_t>(count);
        }
        if (total_read != 0 &&
            !write_guest_bytes(output_address, bytes.data(), total_read, api))
            return -1;
        if (!write_guest_u32("ram", overlapped, completion_error) ||
            !write_guest_u32("ram", static_cast<uint64_t>(overlapped) + 4,
                             static_cast<uint32_t>(total_read))) {
            error = std::string(api) + " cannot update OVERLAPPED status";
            return -1;
        }
        thread->io_completions.push_back(
            {completion_routine, overlapped, completion_error,
             static_cast<uint32_t>(total_read)});
        guest_last_error = 0;
        return return_kernel32_dword(1, api, 20);
    }

    bool dispatch_pending_io_completions(bool& dispatched) {
        dispatched = false;
        GuestThread* thread =
            guest_execution_state(current_guest_thread_handle);
        if (!thread) {
            error = "alertable guest wait has no thread state";
            return false;
        }
        size_t count = 0;
        while (!thread->io_completions.empty()) {
            if (++count > 1024) {
                error = "guest I/O completion queue exceeded its dispatch limit";
                return false;
            }
            const GuestIoCompletion completion =
                thread->io_completions.front();
            thread->io_completions.pop_front();
            uint32_t esp = 0;
            if (!read_guest_u32("register", kX86EspRegisterOffset, esp) ||
                esp < kGuestMinimumUserAddress + 16) {
                error = "guest I/O completion has no valid callback stack";
                return false;
            }
            const uint32_t callback_esp = esp - 16;
            if (!write_guest_u32("ram", callback_esp, 0) ||
                !write_guest_u32("ram", callback_esp + 4,
                                 completion.error_code) ||
                !write_guest_u32("ram", callback_esp + 8,
                                 completion.bytes_transferred) ||
                !write_guest_u32("ram", callback_esp + 12,
                                 completion.overlapped)) {
                error = "cannot prepare guest I/O completion callback stack";
                return false;
            }

            const auto saved_registers = registers;
            const std::string saved_error = error;
            error.clear();
            if (!write_guest_u32("register", kX86EspRegisterOffset,
                                 callback_esp)) {
                registers = saved_registers;
                error = "cannot enter guest I/O completion callback";
                return false;
            }
            const int result = dispatch(completion.routine);
            const std::string callback_error = error;
            registers = saved_registers;
            if (result != 0 || !callback_error.empty()) {
                error = callback_error.empty()
                            ? "guest I/O completion callback failed"
                            : callback_error;
                return false;
            }
            error = saved_error;
            dispatched = true;
        }
        return true;
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

    int load_library_a() {
        constexpr const char* api = "KERNEL32.dll!LoadLibraryA";
        uint32_t name_address = 0;
        if (!read_stack_argument(0, name_address, api)) return -1;
        guest_last_load_library_name.clear();
        guest_last_load_library_handle = 0;
        guest_last_load_library_error = 0;
        if (name_address == 0) {
            guest_last_error = 87;
            guest_last_load_library_error = guest_last_error;
            return return_kernel32_dword(0, api, 4);
        }
        if (!read_guest_ascii(name_address, guest_last_load_library_name, api))
            return -1;
        std::string module_name = guest_last_load_library_name;
        const size_t separator = module_name.find_last_of("/\\");
        if (separator != std::string::npos)
            module_name.erase(0, separator + 1);
        module_name = lowercase_ascii(std::move(module_name));
        if (module_name.find('.') == std::string::npos)
            module_name += ".dll";
        const auto module = guest_module_handles.find(module_name);
        if (module == guest_module_handles.end()) {
            guest_last_error = 126;
            guest_last_load_library_error = guest_last_error;
            return return_kernel32_dword(0, api, 4);
        }
        guest_last_error = 0;
        guest_last_load_library_handle = module->second;
        return return_kernel32_dword(module->second, api, 4);
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

    int get_current_directory_a() {
        constexpr const char* api = "KERNEL32.dll!GetCurrentDirectoryA";
        uint32_t buffer_length = 0;
        uint32_t output_address = 0;
        if (!read_stack_argument(0, buffer_length, api) ||
            !read_stack_argument(1, output_address, api)) {
            return -1;
        }
        const std::string& path = guest_current_directory;
        const uint32_t required_size = static_cast<uint32_t>(path.size() + 1);
        if (buffer_length == 0 && output_address == 0)
            return return_kernel32_dword(required_size, api, 8);
        if (buffer_length < required_size)
            return return_kernel32_dword(required_size, api, 8);
        if (output_address == 0) {
            error = std::string(api) + " has an invalid output pointer";
            return -1;
        }
        if (!write_guest_bytes(output_address,
                               reinterpret_cast<const uint8_t*>(path.data()),
                               path.size(), api)) {
            return -1;
        }
        const uint8_t terminator = 0;
        if (!write_guest_bytes(output_address + required_size - 1,
                               &terminator, sizeof(terminator), api)) {
            return -1;
        }
        return return_kernel32_dword(static_cast<uint32_t>(path.size()), api,
                                     8);
    }

    int set_current_directory_a() {
        constexpr const char* api = "KERNEL32.dll!SetCurrentDirectoryA";
        uint32_t path_address = 0;
        if (!read_stack_argument(0, path_address, api)) return -1;
        std::string path;
        if (!read_guest_ascii(path_address, path, api)) return -1;

        std::filesystem::path candidate;
        if (!make_guest_path_candidate(path, candidate, api))
            return return_kernel32_dword(0, api, 4);
        std::error_code error_code;
        const std::filesystem::path canonical =
            std::filesystem::canonical(candidate, error_code);
        if (error_code || !path_is_within_guest_root(canonical) ||
            !std::filesystem::is_directory(canonical, error_code) ||
            error_code) {
            guest_last_error = error_code == std::errc::permission_denied ? 5 : 3;
            return return_kernel32_dword(0, api, 4);
        }

        const std::filesystem::path relative =
            canonical.lexically_relative(guest_filesystem_root);
        std::string logical_path = "C:\\";
        if (!relative.empty() && relative != ".") {
            for (const auto& component : relative) {
                if (logical_path.back() != '\\') logical_path.push_back('\\');
                logical_path += component.string();
            }
        }
        guest_current_host_directory = canonical;
        guest_current_directory = std::move(logical_path);
        guest_last_error = 0;
        return return_kernel32_dword(1, api, 4);
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

    int load_icon_w() {
        constexpr const char* api = "USER32.dll!LoadIconW";
        uint32_t instance = 0;
        uint32_t resource = 0;
        if (!read_stack_argument(0, instance, api) ||
            !read_stack_argument(1, resource, api)) {
            return -1;
        }
        (void)instance;
        if (resource == 0) return return_kernel32_dword(0, api, 8);
        if (resource > 0xffff && !valid_guest_pointer(resource, 2)) {
            error = std::string(api) + " has an invalid icon-name pointer";
            return -1;
        }
        return return_kernel32_dword(kGuestSyntheticIconHandle, api, 8);
    }

    int create_dca() {
        constexpr const char* api = "GDI32.dll!CreateDCA";
        uint32_t driver_address = 0;
        uint32_t device_address = 0;
        uint32_t output_address = 0;
        uint32_t init_data_address = 0;
        if (!read_stack_argument(0, driver_address, api) ||
            !read_stack_argument(1, device_address, api) ||
            !read_stack_argument(2, output_address, api) ||
            !read_stack_argument(3, init_data_address, api)) {
            return -1;
        }
        (void)device_address;
        (void)output_address;
        (void)init_data_address;
        if (driver_address != 0) {
            std::string driver;
            if (!read_guest_ascii(driver_address, driver, api)) return -1;
            if (lowercase_ascii(std::move(driver)) != "display")
                return return_kernel32_dword(0, api, 16);
        }
        const uint32_t handle = next_guest_display_dc_handle;
        if (handle < kGuestSyntheticDisplayDcBase ||
            handle > UINT32_MAX - 4) {
            error = std::string(api) + " exhausted synthetic display DC handles";
            return -1;
        }
        next_guest_display_dc_handle += 4;
        guest_display_dc_handles.insert(handle);
        return return_kernel32_dword(handle, api, 16);
    }

    int delete_dc() {
        constexpr const char* api = "GDI32.dll!DeleteDC";
        uint32_t handle = 0;
        if (!read_stack_argument(0, handle, api)) return -1;
        return return_kernel32_dword(
            guest_display_dc_handles.erase(handle) != 0 ? 1 : 0, api, 4);
    }

    int ext_escape() {
        constexpr const char* api = "GDI32.dll!ExtEscape";
        uint32_t handle = 0;
        uint32_t escape = 0;
        uint32_t input_size = 0;
        uint32_t input_address = 0;
        uint32_t output_size = 0;
        uint32_t output_address = 0;
        if (!read_stack_argument(0, handle, api) ||
            !read_stack_argument(1, escape, api) ||
            !read_stack_argument(2, input_size, api) ||
            !read_stack_argument(3, input_address, api) ||
            !read_stack_argument(4, output_size, api) ||
            !read_stack_argument(5, output_address, api)) {
            return -1;
        }
        const bool valid_dc = guest_display_dc_handles.count(handle) != 0;
        const bool valid_input = input_size == 0 ||
            (input_address != 0 && valid_guest_pointer(input_address, input_size));
        const bool valid_output = output_size == 0 ||
            (output_address != 0 && valid_guest_pointer(output_address, output_size));
        if (!valid_dc || !valid_input || !valid_output) {
            return return_kernel32_dword(0, api, 24);
        }
        (void)escape;
        return return_kernel32_dword(0, api, 24);
    }

    int get_stock_object() {
        constexpr const char* api = "GDI32.dll!GetStockObject";
        uint32_t object = 0;
        if (!read_stack_argument(0, object, api)) return -1;
        if (object > 17) return return_kernel32_dword(0, api, 4);
        return return_kernel32_dword(
            kGuestSyntheticGdiObjectBase + object * 4, api, 4);
    }

    int register_class_ex_w() {
        constexpr const char* api = "USER32.dll!RegisterClassExW";
        uint32_t class_address = 0;
        if (!read_stack_argument(0, class_address, api)) return -1;
        uint32_t size = 0;
        uint32_t window_proc = 0;
        uint32_t class_name = 0;
        std::array<uint8_t, 2> first_name_character{};
        if (!valid_guest_pointer(class_address, 48) ||
            !read_guest_u32("ram", class_address, size) ||
            !read_guest_u32("ram", class_address + 8, window_proc) ||
            !read_guest_u32("ram", class_address + 40, class_name)) {
            error = std::string(api) + " received an invalid WNDCLASSEXW";
            return -1;
        }
        if (size != 48 || window_proc == 0 ||
            !valid_guest_pointer(class_name, first_name_character.size())) {
            return return_kernel32_dword(0, api, 4);
        }
        if (!read_guest("ram", class_name, sizeof(first_name_character),
                        first_name_character.data())) {
            error = std::string(api) + " could not read the class name";
            return -1;
        }
        if (first_name_character[0] == 0 && first_name_character[1] == 0)
            return return_kernel32_dword(0, api, 4);
        // ponytail: return an opaque atom until guest window classes map to the host.
        return return_kernel32_dword(1, api, 4);
    }

    int create_window_ex_w() {
        constexpr const char* api = "USER32.dll!CreateWindowExW";
        uint32_t class_name = 0;
        uint32_t window_name = 0;
        if (!read_stack_argument(1, class_name, api) ||
            !read_stack_argument(2, window_name, api)) {
            return -1;
        }
        const auto has_text = [this](uint32_t address) {
            if (address == 0 || !valid_guest_pointer(address, 2)) return false;
            std::array<uint8_t, 2> first_character{};
            return read_guest("ram", address, first_character.size(),
                              first_character.data()) &&
                   (first_character[0] != 0 || first_character[1] != 0);
        };
        if (class_name == 0 ||
            (class_name > 0xffff && !has_text(class_name)) ||
            (window_name != 0 && !valid_guest_pointer(window_name, 2))) {
            return return_kernel32_dword(0, api, 12 * sizeof(uint32_t));
        }
        // ponytail: map this opaque HWND to a host window when guest windowing is wired.
        return return_kernel32_dword(kGuestSyntheticWindowHandle, api,
                                     12 * sizeof(uint32_t));
    }

    int clip_cursor() {
        constexpr const char* api = "USER32.dll!ClipCursor";
        uint32_t rectangle = 0;
        if (!read_stack_argument(0, rectangle, api)) return -1;
        if (rectangle != 0 && !valid_guest_pointer(rectangle, 16))
            return return_kernel32_dword(0, api, 4);
        return return_kernel32_dword(1, api, 4);
    }

    int show_window() {
        constexpr const char* api = "USER32.dll!ShowWindow";
        uint32_t window = 0;
        uint32_t command = 0;
        if (!read_stack_argument(0, window, api) ||
            !read_stack_argument(1, command, api)) {
            return -1;
        }
        if (window != kGuestSyntheticWindowHandle)
            return return_kernel32_dword(0, api, 8);
        const uint32_t was_visible = guest_synthetic_window_visible ? 1 : 0;
        guest_synthetic_window_visible = command != 0;
        return return_kernel32_dword(was_visible, api, 8);
    }

    int peek_message_w() {
        constexpr const char* api = "USER32.dll!PeekMessageW";
        uint32_t message_address = 0;
        uint32_t window = 0;
        uint32_t minimum_message = 0;
        uint32_t maximum_message = 0;
        uint32_t remove_flags = 0;
        if (!read_stack_argument(0, message_address, api) ||
            !read_stack_argument(1, window, api) ||
            !read_stack_argument(2, minimum_message, api) ||
            !read_stack_argument(3, maximum_message, api) ||
            !read_stack_argument(4, remove_flags, api)) {
            return -1;
        }
        (void)message_address;
        (void)window;
        (void)minimum_message;
        (void)maximum_message;
        (void)remove_flags;
        return return_kernel32_dword(0, api, 5 * sizeof(uint32_t));
    }

    int system_parameters_info_a() {
        constexpr const char* api = "USER32.dll!SystemParametersInfoA";
        uint32_t action = 0;
        uint32_t parameter = 0;
        uint32_t buffer_address = 0;
        uint32_t flags = 0;
        if (!read_stack_argument(0, action, api) ||
            !read_stack_argument(1, parameter, api) ||
            !read_stack_argument(2, buffer_address, api) ||
            !read_stack_argument(3, flags, api)) {
            return -1;
        }

        uint32_t get_action = 0;
        size_t structure_size = 0;
        bool setting = false;
        switch (action) {
            case 0x0032: get_action = 0x0032; structure_size = 24; break;
            case 0x0033: get_action = 0x0032; structure_size = 24; setting = true; break;
            case 0x0034: get_action = 0x0034; structure_size = 8; break;
            case 0x0035: get_action = 0x0034; structure_size = 8; setting = true; break;
            case 0x0036: get_action = 0x0036; structure_size = 28; break;
            case 0x0037: get_action = 0x0036; structure_size = 28; setting = true; break;
            case 0x003a: get_action = 0x003a; structure_size = 8; break;
            case 0x003b: get_action = 0x003a; structure_size = 8; setting = true; break;
            case 0x0042: get_action = 0x0042; structure_size = 12; break;
            case 0x0043: get_action = 0x0042; structure_size = 12; setting = true; break;
            default:
                guest_last_error = 87;
                return return_kernel32_dword(0, api, 16);
        }
        if (parameter != structure_size || buffer_address == 0 ||
            (setting && flags != 0)) {
            guest_last_error = 87;
            return return_kernel32_dword(0, api, 16);
        }

        std::vector<uint8_t> value(structure_size);
        if (!read_guest_bytes(buffer_address, value.data(), value.size(), api))
            return -1;
        const uint32_t structure_bytes =
            static_cast<uint32_t>(value[0]) |
            (static_cast<uint32_t>(value[1]) << 8) |
            (static_cast<uint32_t>(value[2]) << 16) |
            (static_cast<uint32_t>(value[3]) << 24);
        if (structure_bytes != structure_size) {
            guest_last_error = 87;
            return return_kernel32_dword(0, api, 16);
        }

        if (setting) {
            guest_accessibility_parameters[get_action] = std::move(value);
        } else {
            auto [stored, inserted] =
                guest_accessibility_parameters.try_emplace(get_action);
            if (inserted) {
                stored->second.assign(structure_size, 0);
                stored->second[0] = static_cast<uint8_t>(structure_size);
                stored->second[1] = static_cast<uint8_t>(structure_size >> 8);
                stored->second[2] = static_cast<uint8_t>(structure_size >> 16);
                stored->second[3] = static_cast<uint8_t>(structure_size >> 24);
            }
            if (stored->second.size() != structure_size ||
                !write_guest_bytes(buffer_address, stored->second.data(),
                                   stored->second.size(), api)) {
                return -1;
            }
        }
        return return_kernel32_dword(1, api, 16);
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

    int output_debug_string_a() {
        constexpr const char* api = "KERNEL32.dll!OutputDebugStringA";
        uint32_t ignored_message_address = 0;
        if (!read_stack_argument(0, ignored_message_address, api)) return -1;
        // There is no attached debugger, so Win32's debug-only output has no
        // observable effect in this runtime.
        (void)ignored_message_address;
        return return_kernel32_dword(0, api, sizeof(uint32_t));
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
            trace_guest_allocation(api, size, 0);
            return return_kernel32_dword(0, api, 16);
        }
        if (size > kMaximumGuestVirtualAllocationSize) {
            guest_last_error = 8;
            trace_guest_allocation(api, size, 0);
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
            trace_guest_allocation(api, size, 0);
            return return_kernel32_dword(0, api, 16);
        }
        const uint32_t address = static_cast<uint32_t>(candidate);
        guest_virtual_allocations.emplace(address, allocation_size);
        if (requested_address == 0)
            guest_virtual_next_address = candidate + allocation_size;
        std::memset(static_cast<uint8_t*>(ram) + address, 0,
                    static_cast<size_t>(allocation_size));
        trace_guest_allocation(api, size, address);
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
            trace_guest_allocation(api, size, 0);
            if (!write_guest_u32("register", kX86EaxRegisterOffset, 0)) {
                error = std::string(api) + " cannot write EAX";
                return -1;
            }
            return finish_stdcall(12, api) ? 0 : -1;
        }
        if ((flags & 0x8) != 0 && size != 0)
            std::memset(static_cast<uint8_t*>(ram) + address, 0, size);
        trace_guest_allocation(api, size, address);
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

    RecompiledGuestSchedulerSnapshot guest_scheduler_snapshot() const {
        RecompiledGuestSchedulerSnapshot snapshot{};
        snapshot.entry_point_started = pe32_entry_point_started;
        snapshot.entry_point_complete = pe32_entry_point_complete;
        snapshot.main_thread_started = main_guest_thread.started;
        snapshot.main_thread_completed = main_guest_thread.completed;
        snapshot.main_thread_waiting = main_guest_thread.waiting;
        snapshot.main_thread_runnable = main_guest_thread.runnable;
        snapshot.main_thread_exit_requested =
            main_guest_thread.exit_requested;
        snapshot.main_thread_wait_handle = main_guest_thread.wait_handle;
        snapshot.main_thread_wait_result = main_guest_thread.wait_result;
        snapshot.main_thread_call_stack = main_guest_thread.active_functions;
        snapshot.main_thread_recent_functions.assign(
            main_guest_thread.recent_functions.begin(),
            main_guest_thread.recent_functions.end());
        snapshot.ui_state_gate_trace_enabled = ui_state_gate_trace_enabled;
        snapshot.ui_state_gate_trace_truncated = ui_state_gate_trace_truncated;
        snapshot.ui_state_gate_trace = ui_state_gate_trace_events;
        snapshot.guest_call_trace_enabled = guest_call_trace_enabled;
        snapshot.guest_call_trace_truncated = guest_call_trace_truncated;
        snapshot.guest_call_trace_caller = guest_call_trace_caller;
        snapshot.guest_call_trace_targets = guest_call_trace_targets;
        snapshot.guest_call_trace_imports = guest_call_trace_imports;
        snapshot.guest_call_trace_slot_offsets =
            guest_call_trace_slot_offsets;
        snapshot.guest_call_trace_target_slot_offsets =
            guest_call_trace_target_slot_offsets;
        snapshot.guest_call_trace_stack_slot_offsets =
            guest_call_trace_stack_slot_offsets;
        snapshot.guest_call_trace_string_slot_offsets =
            guest_call_trace_string_slot_offsets;
        snapshot.guest_call_trace = guest_call_trace_events;
        if (!main_guest_thread.active_functions.empty()) {
            snapshot.main_thread_current_function =
                main_guest_thread.active_functions.back();
        }
        snapshot.ready_thread_count = ready_guest_threads.size();
        snapshot.worker_thread_count = guest_threads.size();
        for (const auto& [handle, thread] : guest_threads) {
            (void)handle;
            snapshot.worker_waiting_count += thread.waiting ? 1u : 0u;
            snapshot.worker_runnable_count += thread.runnable ? 1u : 0u;
            snapshot.worker_completed_count += thread.completed ? 1u : 0u;
        }
        snapshot.d3d9_create_device_attempted =
            d3d9_create_device_attempted;
        snapshot.d3d9_create_device_callback_called =
            d3d9_create_device_callback_called;
        snapshot.d3d9_create_device_hresult = d3d9_create_device_hresult;
        snapshot.d3d9_create_device_rejection =
            d3d9_create_device_rejection;
        if (!guest_d3d9_devices.empty()) {
            const auto& device = guest_d3d9_devices.begin()->second;
            snapshot.d3d9_clear_call_count = device.clear_call_count;
            snapshot.d3d9_last_clear_flags = device.last_clear_flags;
            snapshot.d3d9_last_clear_color = device.last_clear_color;
            snapshot.d3d9_last_clear_depth_bits =
                device.last_clear_depth_bits;
            snapshot.d3d9_last_clear_stencil = device.last_clear_stencil;
            snapshot.d3d9_last_clear_rect_count =
                device.last_clear_rect_count;
        }
        snapshot.last_load_library_name = guest_last_load_library_name;
        snapshot.last_load_library_handle = guest_last_load_library_handle;
        snapshot.last_load_library_error = guest_last_load_library_error;
        return snapshot;
    }

    void append_guest_stack() {
        if (active_guest_functions.empty()) {
            return;
        }
        if (guest_call_trace_enabled && !guest_call_trace_events.empty() &&
            error.find("; guest_call_trace=[") == std::string::npos) {
            error += "; guest_call_trace=[";
            for (size_t index = 0; index < guest_call_trace_events.size();
                 ++index) {
                const auto& event = guest_call_trace_events[index];
                char call[320]{};
                char eax_return[20]{};
                char edi_return[20]{};
                if (event.completed && event.has_eax_return) {
                    std::snprintf(eax_return, sizeof(eax_return),
                                  "0x%08x", event.eax_return);
                } else {
                    std::snprintf(eax_return, sizeof(eax_return), "pending");
                }
                if (event.completed && event.has_edi_return) {
                    std::snprintf(edi_return, sizeof(edi_return),
                                  "0x%08x", event.edi_return);
                } else {
                    std::snprintf(edi_return, sizeof(edi_return), "pending");
                }
                std::snprintf(
                    call, sizeof(call),
                    "%s{target=0x%08x,return=0x%08x,ecx=0x%08x,eax=0x%08x,edx=0x%08x,edi=0x%08x,eax_return=%s,edi_return=%s,completed=%u%s%s}",
                    index == 0 ? "" : ",", event.function,
                    event.has_return_address ? event.return_address : 0,
                    event.ecx_entry, event.eax_entry, event.edx_entry,
                    event.edi_entry, eax_return, edi_return,
                    event.completed ? 1u : 0u,
                    event.is_import ? ",import=" : "",
                    event.is_import ? event.import_name.c_str() : "");
                error += call;
            }
            error += "]";
        }
        if (error.find("; guest_stack=[") != std::string::npos) return;
        error += "; guest_stack=[";
        const size_t first = active_guest_functions.size() > 8
                                 ? active_guest_functions.size() - 8
                                 : 0;
        for (size_t index = first;
             index < active_guest_functions.size(); ++index) {
            char address[20]{};
            std::snprintf(address, sizeof(address), "%s0x%08x",
                          index == first ? "" : " -> ",
                          active_guest_functions[index]);
            error += address;
        }
        error += "]";
        if (!active_guest_function_registers.empty()) {
            const auto& frame = active_guest_function_registers.back();
            char guest_frame[160]{};
            std::snprintf(
                guest_frame, sizeof(guest_frame),
                "; guest_frame={entry_EAX=0x%08x,entry_ECX=0x%08x,"
                "entry_EDX=0x%08x,entry_ESP=0x%08x,entry_ESI=0x%08x}",
                frame.eax, frame.ecx, frame.edx, frame.esp, frame.esi);
            error += guest_frame;
            if (diagnostic_guest_pointer_mapped(frame.ecx, 0x44)) {
                char object_header[64]{};
                std::snprintf(object_header, sizeof(object_header),
                              "; guest_entry_ecx_memory@0x%08x=",
                              frame.ecx);
                error += object_header;
                for (size_t offset = 0; offset < 0x44; offset += 4) {
                    uint32_t word = 0;
                    if (!read_guest_diagnostic_u32(
                            static_cast<uint64_t>(frame.ecx) + offset,
                            word)) {
                        break;
                    }
                    char value[16]{};
                    std::snprintf(value, sizeof(value), "%s%08x",
                                  offset == 0 ? "" : ",", word);
                    error += value;
                }
            }
            uint32_t ecx_first_pointer = 0;
            if (read_guest_diagnostic_u32(frame.ecx, ecx_first_pointer) &&
                diagnostic_guest_pointer_mapped(ecx_first_pointer, 8)) {
                uint32_t first_word = 0;
                uint32_t second_word = 0;
                if (read_guest_diagnostic_u32(ecx_first_pointer, first_word) &&
                    read_guest_diagnostic_u32(
                        static_cast<uint64_t>(ecx_first_pointer) + 4,
                        second_word)) {
                    char pointer_words[112]{};
                    std::snprintf(
                        pointer_words, sizeof(pointer_words),
                        "; guest_entry_ecx_first_pointer@0x%08x="
                        "[0x%08x,0x%08x]",
                        ecx_first_pointer, first_word, second_word);
                    error += pointer_words;
                }
            }
            if (frame.has_stack_arguments) {
                char arguments[96]{};
                std::snprintf(
                    arguments, sizeof(arguments),
                    "; guest_entry_stack={return=0x%08x,args=0x%08x,"
                    "0x%08x,0x%08x}",
                    frame.stack_return_slot, frame.stack_arguments[0],
                    frame.stack_arguments[1], frame.stack_arguments[2]);
                error += arguments;
            }
        }
        const auto register_value = [this](size_t offset) {
            uint32_t value = 0;
            std::memcpy(&value, registers.data() + offset, sizeof(value));
            return value;
        };
        char guest_registers[192]{};
        std::snprintf(
            guest_registers, sizeof(guest_registers),
            "; guest_regs={EAX=0x%08x,ECX=0x%08x,EDX=0x%08x,EBX=0x%08x,"
            "ESP=0x%08x,EBP=0x%08x,ESI=0x%08x,EDI=0x%08x}",
            register_value(kX86EaxRegisterOffset),
            register_value(kX86EcxRegisterOffset),
            register_value(kX86EdxRegisterOffset),
            register_value(kX86EbxRegisterOffset),
            register_value(kX86EspRegisterOffset),
            register_value(kX86EbpRegisterOffset),
            register_value(kX86EsiRegisterOffset),
            register_value(kX86EdiRegisterOffset));
        error += guest_registers;
        uint32_t guest_esi = register_value(kX86EsiRegisterOffset);
        if (diagnostic_guest_pointer_mapped(guest_esi, 0x44)) {
            char object_memory[256]{};
            size_t length = static_cast<size_t>(std::snprintf(
                object_memory, sizeof(object_memory),
                "; guest_esi_memory@0x%08x=", guest_esi));
            for (size_t index = 0; index < 0x44 / sizeof(uint32_t); ++index) {
                uint32_t value = 0;
                if (!read_guest_diagnostic_u32(
                        guest_esi + static_cast<uint32_t>(index * 4), value))
                    break;
                const int written = std::snprintf(
                    object_memory + length, sizeof(object_memory) - length,
                    "%s%08x", index == 0 ? "" : ",", value);
                if (written < 0 ||
                    static_cast<size_t>(written) >=
                        sizeof(object_memory) - length)
                    break;
                length += static_cast<size_t>(written);
            }
            error += object_memory;
        }
    }

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
            if (offset < kGuestMinimumUserAddress) {
                char access[112]{};
                std::snprintf(
                    access, sizeof(access),
                    "P-code RAM read at 0x%08x size %zu touched reserved low memory",
                    static_cast<uint32_t>(offset), size);
                error = access;
                append_guest_stack();
                return false;
            }
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
            if (offset < kGuestMinimumUserAddress) {
                char access[112]{};
                std::snprintf(
                    access, sizeof(access),
                    "P-code RAM write at 0x%08x size %zu touched reserved low memory",
                    static_cast<uint32_t>(offset), size);
                error = access;
                append_guest_stack();
                return false;
            }
            if (offset > kGuestRamSize || size > kGuestRamSize - offset) {
                error = "P-code RAM write is out of range";
                return false;
            }
            std::memcpy(static_cast<uint8_t*>(ram) + offset, input, size);
            record_guest_write_provenance(offset, size);
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
    bool guest_write_provenance_enabled_flag = false;
    bool guest_write_provenance_all_flag = false;
    std::vector<uint32_t> guest_write_provenance_targets_cache;
    std::unordered_map<uint32_t, GuestWriteProvenance> guest_last_writers;
    std::unordered_map<uint32_t, GuestWriteProvenance>
        guest_target_last_writers;
    std::unordered_map<std::string, uint32_t> guest_module_handles;
    std::unordered_map<uint32_t, std::string> guest_module_names;
    std::string guest_last_load_library_name;
    uint32_t guest_last_load_library_handle = 0;
    uint32_t guest_last_load_library_error = 0;
    std::unordered_map<uint32_t, GuestHeapBlock> heap_allocations;
    std::vector<GuestHeapBlock> free_heap_blocks;
    std::unordered_set<uint32_t> guest_heap_handles{kGuestProcessHeapHandle};
    std::unordered_set<uint32_t> allocated_tls_indices;
    std::unordered_map<uint32_t, uint32_t> tls_values;
    std::vector<uint32_t> free_tls_indices;
    std::unordered_map<uint32_t, GuestCriticalSection> critical_sections;
    std::unordered_map<uint32_t, GuestMutex> guest_mutexes;
    std::unordered_map<uint32_t, GuestFile> guest_files;
    std::filesystem::path guest_filesystem_root;
    std::filesystem::path guest_current_host_directory;
    std::string guest_current_directory = "C:\\";
    std::unordered_map<uint32_t, GuestEvent> guest_events;
    std::unordered_map<uint32_t, GuestSemaphore> guest_semaphores;
    std::unordered_map<uint32_t, GuestD3D9Interface> guest_d3d9_interfaces;
    std::unordered_map<uint32_t, GuestD3D9Device> guest_d3d9_devices;
    std::unordered_map<uint32_t, GuestD3D9Surface> guest_d3d9_surfaces;
    std::unordered_map<uint32_t, GuestD3D9Texture> guest_d3d9_textures;
    std::unordered_map<uint32_t, GuestD3D9VertexBuffer>
        guest_d3d9_vertex_buffers;
    bool guest_d3d9_adapter_info_available = false;
    bool d3d9_create_device_attempted = false;
    bool d3d9_create_device_callback_called = false;
    uint32_t d3d9_create_device_hresult = UINT32_MAX;
    std::string d3d9_create_device_rejection;
    // ponytail: guest visibility stays headless until HWNDs map to the host window.
    bool guest_synthetic_window_visible = false;
    RecompiledGuestD3d9AdapterInfo guest_d3d9_adapter_info;
    uint32_t guest_display_width = 1024;
    uint32_t guest_display_height = 768;
    uint32_t guest_display_refresh_rate = 0;
    uint32_t guest_display_format = kD3dFormatX8R8G8B8;
    std::unordered_set<uint32_t> guest_display_dc_handles;
    uint32_t next_guest_display_dc_handle = kGuestSyntheticDisplayDcBase;
    std::unordered_map<uint32_t, GuestFiber> guest_fibers;
    std::unordered_map<uint32_t, GuestThread> guest_threads;
    GuestThread main_guest_thread;
    ucontext_t scheduler_context{};
    std::deque<uint32_t> ready_guest_threads;
    std::unordered_map<uint32_t, uint32_t> guest_timer_period_requests;
    std::unordered_map<uint32_t, uint64_t> guest_virtual_allocations;
    std::unordered_map<std::string, uint32_t> guest_named_mutexes;
    std::unordered_map<std::string, uint32_t> guest_named_semaphores;
    std::unordered_map<std::string,
                       std::pair<std::string, std::string>>
        guest_environment_variables;
    std::unordered_map<uint32_t, std::vector<uint8_t>>
        guest_accessibility_parameters;
    std::unordered_set<uint32_t> guest_environment_blocks;
    std::vector<uint32_t> active_guest_functions;
    std::vector<GuestRegisterSnapshot> active_guest_function_registers;
    std::array<GuestPoolAllocationAttempt,
               kGuestAllocationPoolAttemptLimit>
        guest_pool_allocation_attempts{};
    size_t guest_pool_allocation_attempt_count = 0;
    size_t guest_pool_allocation_attempt_cursor = 0;
    uint64_t guest_pool_allocation_attempts_seen = 0;
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
    uint64_t guest_write_provenance_sequence = 0;
    std::unordered_set<uint32_t> unique_function_addresses;
    bool ui_state_gate_trace_enabled = false;
    bool ui_state_gate_trace_truncated = false;
    std::vector<RecompiledUiStateGateTraceEvent> ui_state_gate_trace_events;
    bool guest_call_trace_enabled = false;
    bool guest_call_trace_truncated = false;
    uint32_t guest_call_trace_caller = 0;
    std::vector<uint32_t> guest_call_trace_targets;
    std::vector<std::string> guest_call_trace_imports;
    std::vector<uint32_t> guest_call_trace_slot_offsets;
    std::vector<uint32_t> guest_call_trace_target_slot_offsets;
    std::vector<uint32_t> guest_call_trace_stack_slot_offsets;
    std::vector<uint32_t> guest_call_trace_string_slot_offsets;
    std::vector<RecompiledGuestCallTraceEvent> guest_call_trace_events;
    uint64_t guest_heap_next_address = kGuestHeapStartAddress;
    uint64_t guest_virtual_next_address = UINT64_C(0x20000000);
    uint64_t next_guest_heap_handle = kGuestProcessHeapHandle + 4;
    uint64_t next_guest_mutex_handle = 0x00030000;
    uint64_t next_guest_file_handle = kGuestFileHandleBase;
    uint64_t next_guest_event_handle = kGuestEventHandleBase;
    uint64_t next_guest_semaphore_handle = kGuestSemaphoreHandleBase;
    uint64_t next_guest_wait_sequence = 1;
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

RecompiledGuestSchedulerSnapshot
RecompiledPcodeModule::guest_scheduler_snapshot() const {
    return impl_->guest_scheduler_snapshot();
}

bool RecompiledPcodeModule::load_supplemental_module(
    const std::string& shared_object_path) {
    return impl_->load_supplemental_module(shared_object_path);
}

bool RecompiledPcodeModule::load_override_module(
    const std::string& shared_object_path) {
    return impl_->load_override_module(shared_object_path);
}

bool RecompiledPcodeModule::set_guest_display_mode(
    uint32_t width, uint32_t height, uint32_t refresh_rate,
    uint32_t format) {
    return impl_->set_guest_display_mode(width, height, refresh_rate, format);
}

bool RecompiledPcodeModule::set_guest_d3d9_adapter_info(
    const RecompiledGuestD3d9AdapterInfo& adapter_info) {
    return impl_->set_guest_d3d9_adapter_info(adapter_info);
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
