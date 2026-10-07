# Single-process S6 Phase 721: internalize selected BMW M3 E36 setup-fixed
# HDVehicle+0x4054 from the hash-locked CarPhysicsDetails wheel offsets.

target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/bmw_m3_e36_response_field_4054.cpp)

add_executable(shift_runtime_bmw_m3_e36_response_field_4054_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/bmw_m3_e36_response_field_4054_check.cpp)
target_include_directories(
  shift_runtime_bmw_m3_e36_response_field_4054_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(
  shift_runtime_bmw_m3_e36_response_field_4054_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_bmw_m3_e36_response_field_4054_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_bmw_m3_e36_response_field_4054
    COMMAND shift_runtime_bmw_m3_e36_response_field_4054_check)
endif()
