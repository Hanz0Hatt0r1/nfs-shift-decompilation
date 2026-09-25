cmake_minimum_required(VERSION 3.16)
project(shift_vulkan_probe LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Vulkan QUIET)

if(NOT Vulkan_FOUND)
  message(STATUS "Vulkan SDK not found; shift_vulkan_probe will not be built")
  return()
endif()

add_executable(shift_vulkan_probe src/vulkan_probe.cpp)
target_link_libraries(shift_vulkan_probe PRIVATE Vulkan::Vulkan)

add_executable(shift_vulkan_headless_clear src/vulkan_headless_clear.cpp)
target_link_libraries(shift_vulkan_headless_clear PRIVATE Vulkan::Vulkan)

find_program(GLSLANG_VALIDATOR NAMES glslangValidator)

if(GLSLANG_VALIDATOR)
  set(SHIFT_VULKAN_SHADER_DIR ${CMAKE_CURRENT_BINARY_DIR}/shaders)
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/triangle.vert.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/triangle.vert
            -o ${SHIFT_VULKAN_SHADER_DIR}/triangle.vert.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/triangle.vert
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/triangle.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/triangle.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/triangle.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/triangle.frag
    VERBATIM
  )
  add_custom_target(shift_vulkan_triangle_shaders
    DEPENDS
      ${SHIFT_VULKAN_SHADER_DIR}/triangle.vert.spv
      ${SHIFT_VULKAN_SHADER_DIR}/triangle.frag.spv
  )
  add_executable(shift_vulkan_headless_triangle src/vulkan_headless_triangle.cpp)
  add_dependencies(shift_vulkan_headless_triangle shift_vulkan_triangle_shaders)
  target_link_libraries(shift_vulkan_headless_triangle PRIVATE Vulkan::Vulkan)
else()
  message(STATUS "glslangValidator not found; headless triangle target will not be built")
endif()

if(GLSLANG_VALIDATOR)
  add_executable(shift_vulkan_render_geometry src/vulkan_render_geometry.cpp)
  target_link_libraries(shift_vulkan_render_geometry PRIVATE Vulkan::Vulkan)
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/geometry.vert.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/geometry.vert
            -o ${SHIFT_VULKAN_SHADER_DIR}/geometry.vert.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/geometry.vert
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/geometry.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/geometry.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/geometry.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/geometry.frag
    VERBATIM
  )
  add_custom_target(shift_vulkan_geometry_shaders
    DEPENDS
      ${SHIFT_VULKAN_SHADER_DIR}/geometry.vert.spv
      ${SHIFT_VULKAN_SHADER_DIR}/geometry.frag.spv
  )
  add_dependencies(shift_vulkan_render_geometry shift_vulkan_geometry_shaders)
else()
  message(STATUS "glslangValidator not found; geometry shader target will not be built")
endif()

if(GLSLANG_VALIDATOR)
  add_executable(shift_vulkan_constant_upload src/vulkan_constant_upload.cpp)
  target_link_libraries(shift_vulkan_constant_upload PRIVATE Vulkan::Vulkan)
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/constants.vert.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/constants.vert
            -o ${SHIFT_VULKAN_SHADER_DIR}/constants.vert.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/constants.vert
    VERBATIM
  )
  add_custom_command(
    OUTPUT ${SHIFT_VULKAN_SHADER_DIR}/constants.frag.spv
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SHIFT_VULKAN_SHADER_DIR}
    COMMAND ${GLSLANG_VALIDATOR} -V
            ${CMAKE_CURRENT_SOURCE_DIR}/shaders/constants.frag
            -o ${SHIFT_VULKAN_SHADER_DIR}/constants.frag.spv
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/constants.frag
    VERBATIM
  )
  add_custom_target(shift_vulkan_constant_shaders
    DEPENDS
      ${SHIFT_VULKAN_SHADER_DIR}/constants.vert.spv
      ${SHIFT_VULKAN_SHADER_DIR}/constants.frag.spv
  )
  add_dependencies(shift_vulkan_constant_upload shift_vulkan_constant_shaders)
else()
  message(STATUS "glslangValidator not found; constant upload target will not be built")
endif()
