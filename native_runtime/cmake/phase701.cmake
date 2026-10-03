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

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_native_vehicle_provider_session
    COMMAND shift_runtime_native_vehicle_provider_session_check)
endif()
