#!/bin/bash
# Build and run the generated BabbleSim self-tests for every sample.
#
# Requires:
#   - ZEPHYR_BASE pointing at a Zephyr tree
#   - a compiled BabbleSim at ${ZEPHYR_BASE}/../tools/bsim (or BSIM_OUT_PATH);
#     fetch it with `west config manifest.group-filter -- +babblesim &&
#     west update`, then `make -C ${ZEPHYR_BASE}/../tools/bsim everything`
#   - west on PATH
set -euo pipefail

: "${ZEPHYR_BASE:?ZEPHYR_BASE is required}"
export BSIM_OUT_PATH="${BSIM_OUT_PATH:-${ZEPHYR_BASE}/../tools/bsim}"
export BSIM_COMPONENTS_PATH="${BSIM_COMPONENTS_PATH:-${BSIM_OUT_PATH}/components}"

cd "$(dirname "$0")/.."

for d in samples/*/bsim; do
    echo "Running self-test in $d ..."
    (cd "$d" && ./run_test.sh --rebuild)
done

echo "All BabbleSim self-tests passed."
