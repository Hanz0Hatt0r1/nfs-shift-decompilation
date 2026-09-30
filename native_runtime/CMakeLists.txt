cmake_minimum_required(VERSION 3.16)
project(shift_native_runtime LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Vulkan REQUIRED)
find_package(PkgConfig REQUIRED)
pkg_check_modules(XCB REQUIRED IMPORTED_TARGET xcb)
find_program(GLSLANG_VALIDATOR NAMES glslangValidator REQUIRED)

add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../native_ir
                 ${CMAKE_CURRENT_BINARY_DIR}/native_ir
                 EXCLUDE_FROM_ALL)

set(SHIFT_RUNTIME_SHADER_DIR ${CMAKE_CURRENT_BINARY_DIR}/shaders)
set(SHIFT_RUNTIME_VERT_SPV ${SHIFT_RUNTIME_SHADER_DIR}/runtime.vert.spv)
set(SHIFT_RUNTIME_FRAG_SPV ${SHIFT_RUNTIME_SHADER_DIR}/runtime.frag.spv)

add_custom_command(
  OUTPUT ${SHIFT_RUNTIME_VERT_SPV}
  COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_RUNTIME_SHADER_DIR}
  COMMAND ${GLSLANG_VALIDATOR} -V
          ${CMAKE_CURRENT_SOURCE_DIR}/shaders/runtime.vert
          -o ${SHIFT_RUNTIME_VERT_SPV}
  DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/runtime.vert
  VERBATIM
)

add_custom_command(
  OUTPUT ${SHIFT_RUNTIME_FRAG_SPV}
  COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_RUNTIME_SHADER_DIR}
  COMMAND ${GLSLANG_VALIDATOR} -V
          ${CMAKE_CURRENT_SOURCE_DIR}/shaders/runtime.frag
          -o ${SHIFT_RUNTIME_FRAG_SPV}
  DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/runtime.frag
  VERBATIM
)

add_custom_target(shift_runtime_shaders
  DEPENDS ${SHIFT_RUNTIME_VERT_SPV} ${SHIFT_RUNTIME_FRAG_SPV})

add_executable(shift_runtime src/shift_runtime.cpp)
add_dependencies(shift_runtime shift_runtime_shaders)
target_include_directories(shift_runtime PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/../native_vulkan/include
  ${CMAKE_CURRENT_SOURCE_DIR}/../native_ir/include)
target_link_libraries(shift_runtime PRIVATE
  shift_ir
  Vulkan::Vulkan
  PkgConfig::XCB)
target_compile_definitions(shift_runtime PRIVATE VK_USE_PLATFORM_XCB_KHR)
target_compile_options(shift_runtime PRIVATE -Wall -Wextra -Wpedantic)

install(TARGETS shift_runtime RUNTIME DESTINATION bin)
