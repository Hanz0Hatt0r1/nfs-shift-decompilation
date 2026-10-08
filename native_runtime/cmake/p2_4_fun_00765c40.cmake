# Process 2 P2.4: consume the completed P1.2 FUN_00765c40 handoff without
# inventing the lower collision implementation. These blocker-based targets
# grow the exact residual pass while provider removal remains fail-closed.

add_executable(shift_runtime_fun_00765c40_residual_pass_contract_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00765c40_residual_pass_contract_check.cpp)
target_include_directories(
  shift_runtime_fun_00765c40_residual_pass_contract_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00765c40_residual_pass_contract_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00765c40_residual_pass_contract_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_fun_007584f0_persistent_write_stage_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007584f0_persistent_write_stage_check.cpp)
target_include_directories(
  shift_runtime_fun_007584f0_persistent_write_stage_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_007584f0_persistent_write_stage_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_007584f0_persistent_write_stage_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_fun_00765c40_wheel_pair_refresh_stage_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00765c40_wheel_pair_refresh_stage_check.cpp)
target_include_directories(
  shift_runtime_fun_00765c40_wheel_pair_refresh_stage_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00765c40_wheel_pair_refresh_stage_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00765c40_wheel_pair_refresh_stage_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_fun_00765c40_contact_array_sweep_stage_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00765c40_contact_array_sweep_stage_check.cpp)
target_include_directories(
  shift_runtime_fun_00765c40_contact_array_sweep_stage_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00765c40_contact_array_sweep_stage_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00765c40_contact_array_sweep_stage_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_fun_00765c40_bounded_state_tail_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00765c40_bounded_state_tail_check.cpp)
target_include_directories(
  shift_runtime_fun_00765c40_bounded_state_tail_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00765c40_bounded_state_tail_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00765c40_bounded_state_tail_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_fun_00765c40_optional_body_accumulator_sweep_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00765c40_optional_body_accumulator_sweep_check.cpp)
target_include_directories(
  shift_runtime_fun_00765c40_optional_body_accumulator_sweep_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00765c40_optional_body_accumulator_sweep_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00765c40_optional_body_accumulator_sweep_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_fun_00765c40_contact_body_accumulation_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00765c40_contact_body_accumulation_check.cpp)
target_include_directories(
  shift_runtime_fun_00765c40_contact_body_accumulation_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00765c40_contact_body_accumulation_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00765c40_contact_body_accumulation_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_fun_00765c40_wheel_plane_refresh_stage_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00765c40_wheel_plane_refresh_stage_check.cpp)
target_include_directories(
  shift_runtime_fun_00765c40_wheel_plane_refresh_stage_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00765c40_wheel_plane_refresh_stage_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00765c40_wheel_plane_refresh_stage_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_fun_00765c40_wheel_job_scheduling_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00765c40_wheel_job_scheduling_check.cpp)
target_include_directories(
  shift_runtime_fun_00765c40_wheel_job_scheduling_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00765c40_wheel_job_scheduling_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00765c40_wheel_job_scheduling_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00765c40_residual_pass_contract
    COMMAND shift_runtime_fun_00765c40_residual_pass_contract_check)
  add_test(
    NAME shift_runtime_fun_007584f0_persistent_write_stage
    COMMAND shift_runtime_fun_007584f0_persistent_write_stage_check)
  add_test(
    NAME shift_runtime_fun_00765c40_wheel_pair_refresh_stage
    COMMAND shift_runtime_fun_00765c40_wheel_pair_refresh_stage_check)
  add_test(
    NAME shift_runtime_fun_00765c40_contact_array_sweep_stage
    COMMAND shift_runtime_fun_00765c40_contact_array_sweep_stage_check)
  add_test(
    NAME shift_runtime_fun_00765c40_bounded_state_tail
    COMMAND shift_runtime_fun_00765c40_bounded_state_tail_check)
  add_test(
    NAME shift_runtime_fun_00765c40_optional_body_accumulator_sweep
    COMMAND shift_runtime_fun_00765c40_optional_body_accumulator_sweep_check)
  add_test(
    NAME shift_runtime_fun_00765c40_contact_body_accumulation
    COMMAND shift_runtime_fun_00765c40_contact_body_accumulation_check)
  add_test(
    NAME shift_runtime_fun_00765c40_wheel_plane_refresh_stage
    COMMAND shift_runtime_fun_00765c40_wheel_plane_refresh_stage_check)
  add_test(
    NAME shift_runtime_fun_00765c40_wheel_job_scheduling
    COMMAND shift_runtime_fun_00765c40_wheel_job_scheduling_check)
endif()
