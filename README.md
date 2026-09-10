# ble-gatt-generator

A schema-driven generator for Zephyr BLE GATT services.

`ble-gatt-generator` reads a YAML profile and emits idiomatic, formatted Zephyr
C source, ready-to-build `prj.conf`/`CMakeLists.txt`/sample definitions, and
(coming in M4) companion Python/Bleak and Web Bluetooth test clients.

## Status

This repository is a work in progress. Milestones M1–M3 are complete and build
for `native_sim` without hardware.

## Quick start

```bash
# From the repo root with the Zephyr tree referenced
PYTHONPATH=src python -m ble_gatt_generator.cli \
    -i examples/minimal.yaml \
    -o samples/gatt_gen_minimal

# Format the generated files with Zephyr's own .clang-format
clang-format -i --style=file:$ZEPHYR_BASE/.clang-format \
    samples/gatt_gen_minimal/src/*.c \
    samples/gatt_gen_minimal/src/*.h

# Build the generated sample for native_sim
cmake -B build -S samples/gatt_gen_minimal -DBOARD=native_sim
cmake --build build
```

## Example profile

```yaml
profile:
  name: gatt_gen_minimal
  services:
    - name: minimal_svc
      uuid: 12345678-1234-5678-1234-56789abcdef0
      characteristics:
        - name: read_only
          uuid: 12345678-1234-5678-1234-56789abcdef1
          properties:
            - read
          permissions:
            - read
          size: 1
        - name: read_write
          uuid: 12345678-1234-5678-1234-56789abcdef2
          properties:
            - read
            - write
          permissions:
            - read
            - write
          size: 20
```

## What is generated

For each service the tool emits:

* `src/<service>_service.c` — `BT_GATT_SERVICE_DEFINE`, value buffers,
  thread-safe `get_*`/`set_*` helpers, `*_notify()` / `*_indicate()` helpers,
  and `BT_GATT_CCC` / `BT_GATT_CUD` / `BT_GATT_CPF` / `BT_GATT_CEP` descriptors.
* `src/<service>_service.h` — public helper declarations.
* `src/main.c` — sample main that enables Bluetooth and starts advertising.
* `prj.conf` — Bluetooth Kconfig, including `CONFIG_BT_SMP` when encryption or
  authentication is required.
* `CMakeLists.txt` and `sample.yaml` — build and Twister metadata.

## Features

| Feature                                                          | Status          |
| ---------------------------------------------------------------- | --------------- |
| YAML profile schema with Pydantic validation                     | Done            |
| `BT_GATT_SERVICE_DEFINE` / `BT_GATT_CHARACTERISTIC` generation   | Done            |
| Read, write, write-without-response, notify, indicate properties | Done            |
| Security/permission flags including encrypted and authenticated  | Done            |
| `k_mutex`-protected `get_*` / `set_*` helpers                    | Done            |
| `BT_GATT_CCC`, `BT_GATT_CUD`, `BT_GATT_CPF`, `BT_GATT_CEP`       | Done            |
| Generated `*_notify()` and `*_indicate()` helpers                | Done            |
| `native_sim` build validation                                    | Done            |
| Python/Bleak test client                                         | Planned (M4)    |
| Web Bluetooth test client                                        | Planned (M4)    |
| `west` extension and CI                                          | Planned (M4/M5) |

## Project layout

```
.
├── examples/              # Example YAML profiles
├── samples/               # Generated Zephyr samples
├── src/ble_gatt_generator/ # Python generator and Jinja2 templates
│   ├── cli.py
│   ├── schema.py
│   ├── generator.py
│   └── templates/zephyr/
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

## License

Apache-2.0 (same as Zephyr).
