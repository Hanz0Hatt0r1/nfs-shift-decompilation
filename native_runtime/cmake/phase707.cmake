# Process 2 Phase 707: consume the positive Process 1 #1208 retail
# GlobalVehicleBodyOwnerIdentity contract and remove the manual identity argument
# from the retail BODY0 -> vehicle-world-transform wrapper.

target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/retail_global_vehicle_body_owner_identity.cpp)

add_executable(shift_runtime_retail_global_vehicle_body_owner_identity_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/retail_global_vehicle_body_owner_identity_check.cpp)
target_include_directories(
  shift_runtime_retail_global_vehicle_body_owner_identity_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_retail_global_vehicle_body_owner_identity_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_retail_global_vehicle_body_owner_identity_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_retail_global_vehicle_body_owner_identity
    COMMAND shift_runtime_retail_global_vehicle_body_owner_identity_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase711.cmake)
