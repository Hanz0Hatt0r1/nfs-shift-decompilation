target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/native_vehicle_provider_session.cpp)

add_executable(shift_runtime_native_vehicle_provider_session_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/native_vehicle_provider_session_check.cpp)
target_include_directories(shift_runtime_native_vehicle_provider_session_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(shift_runtime_native_vehicle_provider_session_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_native_vehicle_provider_session_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_selected_session_physics_tweaker_rate_handoff_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/selected_session_physics_tweaker_rate_handoff_check.cpp)
target_include_directories(
  shift_runtime_selected_session_physics_tweaker_rate_handoff_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_compile_options(
  shift_runtime_selected_session_physics_tweaker_rate_handoff_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_native_vehicle_provider_session
    COMMAND shift_runtime_native_vehicle_provider_session_check)
  add_test(
    NAME shift_runtime_selected_session_physics_tweaker_rate_handoff
    COMMAND shift_runtime_selected_session_physics_tweaker_rate_handoff_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase702.cmake)
