cmake_minimum_required(VERSION 3.16)
project(shift_native_runtime LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(CTest)

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

add_library(shift_runtime_physics STATIC
  src/builtin_sparse_solver.cpp
  src/builtin_solver_frame.cpp
  src/post_solve_application.cpp)
target_include_directories(shift_runtime_physics PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_compile_options(shift_runtime_physics PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_builtin_solver_check
  tests/builtin_sparse_solver_check.cpp)
target_link_libraries(shift_runtime_builtin_solver_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_builtin_solver_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_builtin_solver_frame_check
  tests/builtin_solver_frame_check.cpp)
target_link_libraries(shift_runtime_builtin_solver_frame_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_builtin_solver_frame_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_post_solve_check
  tests/post_solve_application_check.cpp)
target_link_libraries(shift_runtime_post_solve_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_post_solve_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_builtin_sparse_solver
    COMMAND shift_runtime_builtin_solver_check)
  add_test(
    NAME shift_runtime_builtin_solver_frame_usage
    COMMAND shift_runtime_builtin_solver_frame_check)
  set_tests_properties(
    shift_runtime_builtin_solver_frame_usage
    PROPERTIES WILL_FAIL TRUE)
  add_test(
    NAME shift_runtime_post_solve_application
    COMMAND shift_runtime_post_solve_check)
endif()

add_executable(shift_runtime src/shift_runtime.cpp)
add_dependencies(shift_runtime shift_runtime_shaders)
target_include_directories(shift_runtime PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/../native_vulkan/include
  ${CMAKE_CURRENT_SOURCE_DIR}/../native_ir/include)
target_link_libraries(shift_runtime PRIVATE
  shift_ir
  shift_runtime_physics
  Vulkan::Vulkan
  PkgConfig::XCB)
target_compile_definitions(shift_runtime PRIVATE VK_USE_PLATFORM_XCB_KHR)
target_compile_options(shift_runtime PRIVATE -Wall -Wextra -Wpedantic)

install(TARGETS shift_runtime RUNTIME DESTINATION bin)
