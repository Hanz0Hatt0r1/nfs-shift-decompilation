# Incremental native physics registrations added after the main runtime target.
# Keeping recent phases here avoids repeatedly rewriting the large top-level file.

target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/wheel_force_aggregate.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/surface_probe.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/contact_outer_kernel.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/wheel_contact_factor.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/collision_query_contract.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/wheel_query_response_join.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/wheel_longitudinal_velocity.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/wheel_kinematics.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/spring_gap_state.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/wheel_spring_gap_join.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/wheel_spring_gap_batch.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/tire_thermal.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/wheel_thermal_integrator.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/body_frame_integration.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/body_record_adapter.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/body_feedback_record_bridge.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/body_feedback_integration_join.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/fun_007afdd0_source_core.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/fun_007afdd0_scalar_provider_join.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/fun_00770e80_two_half_step_schedule.cpp)

add_executable(shift_runtime_wheel_force_aggregate_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/wheel_force_aggregate_check.cpp)
target_link_libraries(shift_runtime_wheel_force_aggregate_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_wheel_force_aggregate_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_surface_probe_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/surface_probe_check.cpp)
target_link_libraries(shift_runtime_surface_probe_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_surface_probe_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_contact_outer_kernel_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/contact_outer_kernel_check.cpp)
target_link_libraries(shift_runtime_contact_outer_kernel_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_contact_outer_kernel_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_aux_contact_pair_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/aux_contact_pair_check.cpp)
target_link_libraries(shift_runtime_aux_contact_pair_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_aux_contact_pair_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_wheel_contact_factor_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/wheel_contact_factor_check.cpp)
target_link_libraries(shift_runtime_wheel_contact_factor_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_wheel_contact_factor_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_collision_query_contract_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/collision_query_contract_check.cpp)
target_link_libraries(shift_runtime_collision_query_contract_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_collision_query_contract_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_wheel_query_response_join_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/wheel_query_response_join_check.cpp)
target_link_libraries(shift_runtime_wheel_query_response_join_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_wheel_query_response_join_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_wheel_longitudinal_velocity_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/wheel_longitudinal_velocity_check.cpp)
target_link_libraries(shift_runtime_wheel_longitudinal_velocity_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_wheel_longitudinal_velocity_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_wheel_kinematics_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/wheel_kinematics_check.cpp)
target_link_libraries(shift_runtime_wheel_kinematics_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_wheel_kinematics_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_spring_gap_state_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/spring_gap_state_check.cpp)
target_link_libraries(shift_runtime_spring_gap_state_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_spring_gap_state_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_wheel_spring_gap_join_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/wheel_spring_gap_join_check.cpp)
target_link_libraries(shift_runtime_wheel_spring_gap_join_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_wheel_spring_gap_join_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_wheel_spring_gap_batch_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/wheel_spring_gap_batch_check.cpp)
target_link_libraries(shift_runtime_wheel_spring_gap_batch_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_wheel_spring_gap_batch_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_tire_thermal_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/tire_thermal_check.cpp)
target_link_libraries(shift_runtime_tire_thermal_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_tire_thermal_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_wheel_thermal_core_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/wheel_thermal_integrator_check.cpp)
target_link_libraries(shift_runtime_wheel_thermal_core_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_wheel_thermal_core_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_body_frame_integration_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/body_frame_integration_check.cpp)
target_link_libraries(shift_runtime_body_frame_integration_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_body_frame_integration_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_body_array_basis_callback_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/body_array_basis_callback_check.cpp)
target_link_libraries(shift_runtime_body_array_basis_callback_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_body_array_basis_callback_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_body_record_adapter_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/body_record_adapter_check.cpp)
target_link_libraries(shift_runtime_body_record_adapter_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_body_record_adapter_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_body_feedback_record_bridge_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/body_feedback_record_bridge_check.cpp)
target_link_libraries(shift_runtime_body_feedback_record_bridge_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_body_feedback_record_bridge_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_body_feedback_integration_join_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/body_feedback_integration_join_check.cpp)
target_link_libraries(shift_runtime_body_feedback_integration_join_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_body_feedback_integration_join_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_fun_007afdd0_source_core_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007afdd0_source_core_check.cpp)
target_link_libraries(shift_runtime_fun_007afdd0_source_core_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_fun_007afdd0_source_core_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_fun_007afdd0_scalar_provider_join_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007afdd0_scalar_provider_join_check.cpp)
target_link_libraries(shift_runtime_fun_007afdd0_scalar_provider_join_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_fun_007afdd0_scalar_provider_join_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_fun_00770e80_two_half_step_schedule_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00770e80_two_half_step_schedule_check.cpp)
target_link_libraries(shift_runtime_fun_00770e80_two_half_step_schedule_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_fun_00770e80_two_half_step_schedule_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_wheel_force_aggregate
    COMMAND shift_runtime_wheel_force_aggregate_check)
  add_test(
    NAME shift_runtime_surface_probe
    COMMAND shift_runtime_surface_probe_check)
  add_test(
    NAME shift_runtime_contact_outer_kernel
    COMMAND shift_runtime_contact_outer_kernel_check)
  add_test(
    NAME shift_runtime_aux_contact_pair
    COMMAND shift_runtime_aux_contact_pair_check)
  add_test(
    NAME shift_runtime_wheel_contact_factor
    COMMAND shift_runtime_wheel_contact_factor_check)
  add_test(
    NAME shift_runtime_collision_query_contract
    COMMAND shift_runtime_collision_query_contract_check)
  add_test(
    NAME shift_runtime_wheel_query_response_join
    COMMAND shift_runtime_wheel_query_response_join_check)
  add_test(
    NAME shift_runtime_wheel_longitudinal_velocity
    COMMAND shift_runtime_wheel_longitudinal_velocity_check)
  add_test(
    NAME shift_runtime_wheel_kinematics
    COMMAND shift_runtime_wheel_kinematics_check)
  add_test(
    NAME shift_runtime_spring_gap_state
    COMMAND shift_runtime_spring_gap_state_check)
  add_test(
    NAME shift_runtime_wheel_spring_gap_join
    COMMAND shift_runtime_wheel_spring_gap_join_check)
  add_test(
    NAME shift_runtime_wheel_spring_gap_batch
    COMMAND shift_runtime_wheel_spring_gap_batch_check)
  add_test(
    NAME shift_runtime_tire_thermal
    COMMAND shift_runtime_tire_thermal_check)
  add_test(
    NAME shift_runtime_wheel_thermal_core
    COMMAND shift_runtime_wheel_thermal_core_check)
  add_test(
    NAME shift_runtime_body_frame_integration
    COMMAND shift_runtime_body_frame_integration_check)
  add_test(
    NAME shift_runtime_body_array_basis_callback
    COMMAND shift_runtime_body_array_basis_callback_check)
  add_test(
    NAME shift_runtime_body_record_adapter
    COMMAND shift_runtime_body_record_adapter_check)
  add_test(
    NAME shift_runtime_body_feedback_record_bridge
    COMMAND shift_runtime_body_feedback_record_bridge_check)
  add_test(
    NAME shift_runtime_body_feedback_integration_join
    COMMAND shift_runtime_body_feedback_integration_join_check)
  add_test(
    NAME shift_runtime_fun_007afdd0_source_core
    COMMAND shift_runtime_fun_007afdd0_source_core_check)
  add_test(
    NAME shift_runtime_fun_007afdd0_scalar_provider_join
    COMMAND shift_runtime_fun_007afdd0_scalar_provider_join_check)
  add_test(
    NAME shift_runtime_fun_00770e80_two_half_step_schedule
    COMMAND shift_runtime_fun_00770e80_two_half_step_schedule_check)
endif()
