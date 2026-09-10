# SPDX-License-Identifier: Apache-2.0

# BabbleSim self-test for the generated gatt_gen_minimal GATT profile.
# Build for nrf52_bsim and run with ./run_test.sh (requires a compiled
# BabbleSim at ${ZEPHYR_BASE}/../tools/bsim or $BSIM_OUT_PATH).

cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(bsim_test_gatt_gen_minimal)

add_subdirectory(${ZEPHYR_BASE}/tests/bsim/babblekit babblekit)
target_link_libraries(app PRIVATE babblekit)

FILE(GLOB app_sources src/*.c)
target_sources(app PRIVATE ${app_sources})

# The generated GATT services under test live in the parent sample.
target_sources(app PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/../src/minimal_svc_service.c)
target_include_directories(app PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/../src)

zephyr_include_directories(
  ${BSIM_COMPONENTS_PATH}/libUtilv1/src/
  ${BSIM_COMPONENTS_PATH}/libPhyComv1/src/
  )
