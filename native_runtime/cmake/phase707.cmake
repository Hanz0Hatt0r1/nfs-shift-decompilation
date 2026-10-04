# Process 2 Phase 707: consume Process 1 #1208 retail BODY-owner identity
# and replace the external FUN_007682c0 BODY +0x50 delta consumer with a
# chain-owned persistent BODY0 f64 application.

target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/fun_007682c0_body0_delta_consumer_chain.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/native_body0_delta_runtime.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/native_vehicle_provider_session_v2.cpp)

add_executable(shift_runtime_native_vehicle_provider_session_v2_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/native_vehicle_provider_session_v2_check.cpp)
target_include_directories(shift_runtime_native_vehicle_provider_session_v2_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(shift_runtime_native_vehicle_provider_session_v2_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_native_vehicle_provider_session_v2_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_native_vehicle_provider_session_v2
    COMMAND shift_runtime_native_vehicle_provider_session_v2_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase648.cmake)
