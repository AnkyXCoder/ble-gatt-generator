#!/bin/bash
set -e

: "${ZEPHYR_BASE:?ZEPHYR_BASE is required}"
: "${PYTHON_EXECUTABLE:?PYTHON_EXECUTABLE is required}"

SAMPLES=(
    "samples/gatt_gen_minimal"
    "samples/gatt_gen_notify"
    "samples/gatt_gen_secure"
)

for s in "${SAMPLES[@]}"; do
    name=$(basename "$s")
    build_dir="build-$name"
    rm -rf "$build_dir"
    echo "Building $s ..."
    cmake -B "$build_dir" -S "$s" -DBOARD=native_sim -DPython3_EXECUTABLE="$PYTHON_EXECUTABLE"
    cmake --build "$build_dir"
done

echo "All samples built successfully."
