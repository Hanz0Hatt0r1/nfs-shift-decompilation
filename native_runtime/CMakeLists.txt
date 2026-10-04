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
  src/body_solver_export.cpp
  src/body_solver_export_frame.cpp
  src/body_export_solver_join.cpp
  src/body_preprojection.cpp
  src/body_constraint_assembly.cpp
  src/constraint_sample_refresh.cpp
  src/constraint_sample_relation_frame.cpp
  src/constraint_relation_reset_frame.cpp
  src/constraint_relation_state_mutation.cpp
  src/body_sparse_matrix_storage.cpp
  src/generated_body_solver_export.cpp
  src/generated_body_constraint_frame.cpp
  src/body_state_feedback.cpp
  src/vehicle_driveline_math.cpp
  src/body_frame_preparation.cpp
  src/body_accumulator_primitives.cpp
  src/wheel_contact_response.cpp
  src/body_point_transform.cpp
  src/aux_contact_response.cpp
  src/bar_projection.cpp
  src/bar_matrix_coupling.cpp
  src/hinge_projection.cpp
  src/hinge_bar_matrix_coupling.cpp
  src/hinge_matrix_coupling.cpp
  src/joint_matrix_coupling.cpp
  src/joint_projection.cpp
  src/post_solve_projection.cpp
  src/post_solve_row_kernel.cpp)
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

add_executable(shift_runtime_body_sparse_matrix_storage_check
  tests/body_sparse_matrix_storage_check.cpp)
target_link_libraries(shift_runtime_body_sparse_matrix_storage_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_body_sparse_matrix_storage_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_body_constraint_assembly_check
  tests/body_constraint_assembly_check.cpp)
target_link_libraries(shift_runtime_body_constraint_assembly_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_body_constraint_assembly_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_constraint_sample_refresh_check
  tests/constraint_sample_refresh_check.cpp)
target_link_libraries(shift_runtime_constraint_sample_refresh_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_constraint_sample_refresh_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_constraint_sample_relation_frame_check
  tests/constraint_sample_relation_frame_check.cpp)
target_link_libraries(
  shift_runtime_constraint_sample_relation_frame_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_constraint_sample_relation_frame_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_constraint_relation_reset_frame_check
  tests/constraint_relation_reset_frame_check.cpp)
target_link_libraries(
  shift_runtime_constraint_relation_reset_frame_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_constraint_relation_reset_frame_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_constraint_relation_state_mutation_check
  tests/constraint_relation_state_mutation_check.cpp)
target_link_libraries(
  shift_runtime_constraint_relation_state_mutation_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_constraint_relation_state_mutation_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_constraint_relation_state_dispatch_check
  tests/constraint_relation_state_dispatch_check.cpp)
target_link_libraries(
  shift_runtime_constraint_relation_state_dispatch_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_constraint_relation_state_dispatch_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_body_preprojection_check
  tests/body_preprojection_check.cpp)
target_link_libraries(shift_runtime_body_preprojection_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_body_preprojection_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_joint_matrix_coupling_check
  tests/joint_matrix_coupling_check.cpp)
target_link_libraries(shift_runtime_joint_matrix_coupling_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_joint_matrix_coupling_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_joint_projection_check
  tests/joint_projection_check.cpp)
target_link_libraries(shift_runtime_joint_projection_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_joint_projection_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_bar_matrix_coupling_check
  tests/bar_matrix_coupling_check.cpp)
target_link_libraries(shift_runtime_bar_matrix_coupling_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_bar_matrix_coupling_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_bar_projection_check
  tests/bar_projection_check.cpp)
target_link_libraries(shift_runtime_bar_projection_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_bar_projection_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_hinge_bar_matrix_coupling_check
  tests/hinge_bar_matrix_coupling_check.cpp)
target_link_libraries(shift_runtime_hinge_bar_matrix_coupling_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_hinge_bar_matrix_coupling_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_hinge_matrix_coupling_check
  tests/hinge_matrix_coupling_check.cpp)
target_link_libraries(shift_runtime_hinge_matrix_coupling_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_hinge_matrix_coupling_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_hinge_projection_check
  tests/hinge_projection_check.cpp)
target_link_libraries(shift_runtime_hinge_projection_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_hinge_projection_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_generated_body_constraint_frame_check
  tests/generated_body_constraint_frame_check.cpp)
target_link_libraries(shift_runtime_generated_body_constraint_frame_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_generated_body_constraint_frame_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_generated_body_solver_frame_join_check
  tests/generated_body_solver_frame_join_check.cpp)
target_link_libraries(
  shift_runtime_generated_body_solver_frame_join_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_generated_body_solver_frame_join_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_generated_body_solver_export_check
  tests/generated_body_solver_export_check.cpp)
target_link_libraries(shift_runtime_generated_body_solver_export_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_generated_body_solver_export_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_body_solver_export_check
  tests/body_solver_export_check.cpp)
target_link_libraries(shift_runtime_body_solver_export_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_body_solver_export_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_body_solver_export_frame_check
  tests/body_solver_export_frame_check.cpp)
target_link_libraries(shift_runtime_body_solver_export_frame_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_body_solver_export_frame_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_body_export_solver_join_check
  tests/body_export_solver_join_check.cpp)
target_link_libraries(shift_runtime_body_export_solver_join_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_body_export_solver_join_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_builtin_solver_frame_check
  tests/builtin_solver_frame_check.cpp)
target_link_libraries(shift_runtime_builtin_solver_frame_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_builtin_solver_frame_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_post_solve_projection_check
  tests/post_solve_projection_check.cpp)
target_link_libraries(shift_runtime_post_solve_projection_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_post_solve_projection_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_solver_post_solve_join_check
  tests/solver_post_solve_join_check.cpp)
target_link_libraries(shift_runtime_solver_post_solve_join_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_solver_post_solve_join_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_post_solve_persistence_check
  tests/post_solve_persistence_check.cpp)
target_link_libraries(shift_runtime_post_solve_persistence_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_post_solve_persistence_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_body_state_feedback_check
  tests/body_state_feedback_check.cpp)
target_link_libraries(shift_runtime_body_state_feedback_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_body_state_feedback_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_body_feedback_scheduler_check
  tests/runtime_body_feedback_scheduler_check.cpp)
target_include_directories(shift_runtime_body_feedback_scheduler_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(shift_runtime_body_feedback_scheduler_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_body_feedback_scheduler_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_vehicle_driveline_math_check
  tests/vehicle_driveline_math_check.cpp)
target_link_libraries(shift_runtime_vehicle_driveline_math_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_vehicle_driveline_math_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_body_frame_preparation_check
  tests/body_frame_preparation_check.cpp)
target_link_libraries(shift_runtime_body_frame_preparation_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_body_frame_preparation_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_body_accumulator_primitives_check
  tests/body_accumulator_primitives_check.cpp)
target_link_libraries(shift_runtime_body_accumulator_primitives_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_body_accumulator_primitives_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_wheel_contact_response_check
  tests/wheel_contact_response_check.cpp)
target_link_libraries(shift_runtime_wheel_contact_response_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_wheel_contact_response_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_body_point_transform_check
  tests/body_point_transform_check.cpp)
target_link_libraries(shift_runtime_body_point_transform_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_body_point_transform_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_aux_contact_response_check
  tests/aux_contact_response_check.cpp)
target_link_libraries(shift_runtime_aux_contact_response_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_aux_contact_response_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_loop_policy_check
  tests/runtime_loop_policy_check.cpp)
target_include_directories(shift_runtime_loop_policy_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_compile_options(shift_runtime_loop_policy_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_loop_policy
    COMMAND shift_runtime_loop_policy_check)
  add_test(
    NAME shift_runtime_builtin_sparse_solver
    COMMAND shift_runtime_builtin_solver_check)
  add_test(
    NAME shift_runtime_body_sparse_matrix_storage
    COMMAND shift_runtime_body_sparse_matrix_storage_check)
  add_test(
    NAME shift_runtime_body_constraint_assembly
    COMMAND shift_runtime_body_constraint_assembly_check)
  add_test(
    NAME shift_runtime_constraint_sample_refresh
    COMMAND shift_runtime_constraint_sample_refresh_check)
  add_test(
    NAME shift_runtime_constraint_sample_relation_frame_usage
    COMMAND shift_runtime_constraint_sample_relation_frame_check)
  set_tests_properties(
    shift_runtime_constraint_sample_relation_frame_usage
    PROPERTIES WILL_FAIL TRUE)
  add_test(
    NAME shift_runtime_constraint_relation_reset_frame_usage
    COMMAND shift_runtime_constraint_relation_reset_frame_check)
  set_tests_properties(
    shift_runtime_constraint_relation_reset_frame_usage
    PROPERTIES WILL_FAIL TRUE)
  add_test(
    NAME shift_runtime_constraint_relation_state_mutation
    COMMAND shift_runtime_constraint_relation_state_mutation_check)
  add_test(
    NAME shift_runtime_constraint_relation_state_dispatch
    COMMAND shift_runtime_constraint_relation_state_dispatch_check)
  add_test(
    NAME shift_runtime_body_preprojection
    COMMAND shift_runtime_body_preprojection_check)
  add_test(
    NAME shift_runtime_joint_matrix_coupling
    COMMAND shift_runtime_joint_matrix_coupling_check)
  add_test(
    NAME shift_runtime_joint_projection
    COMMAND shift_runtime_joint_projection_check)
  add_test(
    NAME shift_runtime_bar_matrix_coupling
    COMMAND shift_runtime_bar_matrix_coupling_check)
  add_test(
    NAME shift_runtime_bar_projection
    COMMAND shift_runtime_bar_projection_check)
  add_test(
    NAME shift_runtime_hinge_bar_matrix_coupling
    COMMAND shift_runtime_hinge_bar_matrix_coupling_check)
  add_test(
    NAME shift_runtime_hinge_matrix_coupling
    COMMAND shift_runtime_hinge_matrix_coupling_check)
  add_test(
    NAME shift_runtime_hinge_projection
    COMMAND shift_runtime_hinge_projection_check)
  add_test(
    NAME shift_runtime_generated_body_constraint_frame_usage
    COMMAND shift_runtime_generated_body_constraint_frame_check)
  set_tests_properties(
    shift_runtime_generated_body_constraint_frame_usage
    PROPERTIES WILL_FAIL TRUE)

  add_test(
    NAME shift_runtime_generated_body_solver_frame_join_usage
    COMMAND shift_runtime_generated_body_solver_frame_join_check)
  set_tests_properties(
    shift_runtime_generated_body_solver_frame_join_usage
    PROPERTIES WILL_FAIL TRUE)

  add_test(
    NAME shift_runtime_generated_body_solver_export
    COMMAND shift_runtime_generated_body_solver_export_check)
  add_test(
    NAME shift_runtime_body_solver_export
    COMMAND shift_runtime_body_solver_export_check)
  add_test(
    NAME shift_runtime_body_solver_export_frame_usage
    COMMAND shift_runtime_body_solver_export_frame_check)
  set_tests_properties(
    shift_runtime_body_solver_export_frame_usage
    PROPERTIES WILL_FAIL TRUE)

  add_test(
    NAME shift_runtime_body_export_solver_join_usage
    COMMAND shift_runtime_body_export_solver_join_check)
  set_tests_properties(
    shift_runtime_body_export_solver_join_usage
    PROPERTIES WILL_FAIL TRUE)
  add_test(
    NAME shift_runtime_builtin_solver_frame_usage
    COMMAND shift_runtime_builtin_solver_frame_check)
  set_tests_properties(
    shift_runtime_builtin_solver_frame_usage
    PROPERTIES WILL_FAIL TRUE)

  add_test(
    NAME shift_runtime_post_solve_projection_usage
    COMMAND shift_runtime_post_solve_projection_check)
  set_tests_properties(
    shift_runtime_post_solve_projection_usage
    PROPERTIES WILL_FAIL TRUE)

  add_test(
    NAME shift_runtime_solver_post_solve_join_usage
    COMMAND shift_runtime_solver_post_solve_join_check)
  set_tests_properties(
    shift_runtime_solver_post_solve_join_usage
    PROPERTIES WILL_FAIL TRUE)

  add_test(
    NAME shift_runtime_body_state_feedback
    COMMAND shift_runtime_body_state_feedback_check)
  add_test(
    NAME shift_runtime_body_feedback_scheduler
    COMMAND shift_runtime_body_feedback_scheduler_check)
  add_test(
    NAME shift_runtime_vehicle_driveline_math
    COMMAND shift_runtime_vehicle_driveline_math_check)
  add_test(
    NAME shift_runtime_body_frame_preparation
    COMMAND shift_runtime_body_frame_preparation_check)
  add_test(
    NAME shift_runtime_body_accumulator_primitives
    COMMAND shift_runtime_body_accumulator_primitives_check)
  add_test(
    NAME shift_runtime_wheel_contact_response
    COMMAND shift_runtime_wheel_contact_response_check)
  add_test(
    NAME shift_runtime_body_point_transform
    COMMAND shift_runtime_body_point_transform_check)
  add_test(
    NAME shift_runtime_aux_contact_response
    COMMAND shift_runtime_aux_contact_response_check)
endif()

include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/recent_physics.cmake)

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
