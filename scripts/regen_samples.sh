#!/bin/bash
# Regenerate every sample from its example profile and format the C sources
# with Zephyr's clang-format configuration. Run this after changing templates.
set -euo pipefail

: "${ZEPHYR_BASE:?ZEPHYR_BASE is required}"
PYTHON="${PYTHON_EXECUTABLE:-python3}"
CLANG_FORMAT="${CLANG_FORMAT:-clang-format}"

cd "$(dirname "$0")/.."

for example in examples/*.yaml; do
    name=$(basename "$example" .yaml)
    out="samples/gatt_gen_$name"
    echo "Regenerating $out from $example ..."
    PYTHONPATH=src "$PYTHON" -m ble_gatt_generator.cli -i "$example" -o "$out" --force
    "$CLANG_FORMAT" -i --style="file:$ZEPHYR_BASE/.clang-format" "$out"/src/*.c "$out"/src/*.h
done

echo "Samples regenerated."
