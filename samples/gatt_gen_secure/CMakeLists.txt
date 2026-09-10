cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(gatt_gen_secure)

target_sources(app PRIVATE src/main.c)
target_sources(app PRIVATE src/secure_svc_service.c)
