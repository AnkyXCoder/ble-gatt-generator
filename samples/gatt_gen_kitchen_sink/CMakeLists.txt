cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(gatt_gen_full)

target_sources(app PRIVATE src/main.c)
target_sources(app PRIVATE src/props_svc_service.c)
target_sources(app PRIVATE src/sec_svc_service.c)
target_sources(app PRIVATE src/desc_svc_service.c)
