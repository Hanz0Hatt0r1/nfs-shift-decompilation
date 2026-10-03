# Incremental native physics registrations added after the main runtime target.
# Keeping recent phases here avoids repeatedly rewriting the large top-level file.

target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/wheel_force_aggregate.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/surface_probe.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/contact_outer_kernel.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/wheel_contact_factor.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/collision_query_contract.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/wheel_query_response_join.cpp)

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
endif()
