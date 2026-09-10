# ble-gatt-generator

A schema-driven generator for Zephyr BLE GATT services.

`ble-gatt-generator` reads a YAML profile and emits idiomatic, formatted Zephyr
C source, ready-to-build `prj.conf`/`CMakeLists.txt`/sample definitions, and
companion Python/Bleak and Web Bluetooth test clients.

## Status

This repository is a work in progress. Milestones M1–M4 are complete and build
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
* `test_client.py` — Bleak-based Python client to scan, read, write, and
  subscribe to notifications/indications.
* `web_client.html` — static Web Bluetooth page with the same operations.

## Test clients

The generated `test_client.py` and `web_client.html` already know the service
and characteristic UUIDs from the profile, so you can immediately exercise the
peripheral without hand-writing client code.

```bash
# With a Bluetooth adapter and the peripheral running
pip install bleak
python samples/gatt_gen_minimal/test_client.py --name "GATT Gen gatt_gen_minimal"
```

The `web_client.html` file can be opened in a Chromium-based browser with
Web Bluetooth support and the experimental `#enable-web-bluetooth` flag if
needed.

## CI

The `scripts/ci.sh` script builds all included `native_sim` samples. It is also
used by the GitHub Actions workflow in `.github/workflows/ci.yml`.

```bash
export ZEPHYR_BASE=/path/to/zephyr
export PYTHON_EXECUTABLE=/path/to/python
bash scripts/ci.sh
```

## Features

| Feature                                                          | Status       |
| ---------------------------------------------------------------- | ------------ |
| YAML profile schema with Pydantic validation                     | Done         |
| `BT_GATT_SERVICE_DEFINE` / `BT_GATT_CHARACTERISTIC` generation   | Done         |
| Read, write, write-without-response, notify, indicate properties | Done         |
| Security/permission flags including encrypted and authenticated  | Done         |
| `k_mutex`-protected `get_*` / `set_*` helpers                    | Done         |
| `BT_GATT_CCC`, `BT_GATT_CUD`, `BT_GATT_CPF`, `BT_GATT_CEP`       | Done         |
| Generated `*_notify()` and `*_indicate()` helpers                | Done         |
| `native_sim` build validation                                    | Done         |
| Python/Bleak test client                                         | Done         |
| Web Bluetooth test client                                        | Done         |
| Local CI script and GitHub Actions workflow                      | Done         |
| `west` extension                                                 | Planned (M5) |

## Project layout

```
.
├── examples/                      # Example YAML profiles
├── samples/                       # Generated Zephyr samples
├── scripts/                       # CI helper scripts
├── .github/workflows/             # GitHub Actions workflows
├── src/ble_gatt_generator/        # Python generator and Jinja2 templates
│   ├── cli.py
│   ├── schema.py
│   ├── generator.py
│   └── templates/
│       ├── clients/               # Bleak + Web Bluetooth client templates
│       └── zephyr/                # Zephyr C/H and sample templates
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

## License

Apache-2.0 (same as Zephyr).
