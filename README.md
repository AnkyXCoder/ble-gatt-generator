# ble-gatt-generator

A schema-driven generator for Zephyr BLE GATT services.

Describe your GATT profile once in YAML and get:

* idiomatic, `clang-format`-clean Zephyr C/H with `BT_GATT_SERVICE_DEFINE`,
  `k_mutex`-protected accessors, notify/indicate helpers and descriptor tables;
* a buildable Zephyr sample (`main.c`, `prj.conf`, `CMakeLists.txt`,
  `sample.yaml`) that you own and can edit freely;
* a Python/Bleak test client and a Web Bluetooth page that already know every
  UUID, so you can verify the peripheral without writing client code;
* a two-device [BabbleSim](https://babblesim.github.io/) self-test under
  `bsim/` that connects a generated central to the generated services and
  verifies discovery, reads, write/read-back and notifications on
  `nrf52_bsim` — real BLE traffic, no hardware.

Everything is verified on `native_sim` (build) and `nrf52_bsim`
(end-to-end over a simulated radio), so no hardware is needed for CI.

## Installation

Requirements: Python 3.10+, and a Zephyr workspace (4.x) if you want to build
the generated samples.

```bash
# From PyPI (once published) or a local checkout
pip install ble-gatt-generator

# Local development checkout
git clone <repo-url> ble-gatt-generator
cd ble-gatt-generator
pip install -e ".[dev]"           # includes pytest
pip install -e ".[client]"        # adds bleak for the generated test client
```

This installs the `ble-gatt-generator` CLI. If the repository is part of a
west workspace, `west gatt-gen` is also registered via `west-commands.yml`.

## Usage

### CLI

```bash
ble-gatt-generator -i examples/minimal.yaml -o my_app
```

Options:

| Flag           | Description                                                                             |
| -------------- | --------------------------------------------------------------------------------------- |
| `-i, --input`  | YAML profile to read.                                                                   |
| `-o, --output` | Output directory (created if missing).                                                  |
| `-f, --force`  | Overwrite user-owned files (`src/main.c`, `prj.conf`, `CMakeLists.txt`, `sample.yaml`). |
| `--version`    | Print the tool version.                                                                 |

Equivalent west form:

```bash
west gatt-gen -i examples/minimal.yaml -o my_app
```

### Regeneration is safe

Generated files fall into two groups:

| Always overwritten (do not edit)    | Written once, then yours (`--force` to reset) |
| ----------------------------------- | --------------------------------------------- |
| `src/<service>_service.c`           | `src/main.c`                                  |
| `src/<service>_service.h`           | `prj.conf`                                    |
| `test_client.py`, `web_client.html` | `CMakeLists.txt`, `sample.yaml`               |
| `bsim/` (whole directory)           |                                               |

Put your application logic in `main.c` or your own sources and talk to the
service through the generated API. Re-running the generator after a YAML change
updates the service files without touching your code.

### Build and run on `native_sim`

```bash
export ZEPHYR_BASE=/path/to/zephyr
cmake -B build -S my_app -DBOARD=native_sim
cmake --build build
./build/zephyr/zephyr.exe --bt-dev=hci0     # attach a host HCI adapter, or
./build/zephyr/zephyr.exe                    # boots, reports missing HCI
```

### Talk to the device

```bash
pip install bleak
python my_app/test_client.py                 # scans for "GATT Gen <profile>"
python my_app/test_client.py --address AA:BB:CC:DD:EE:FF --notify-seconds 10
```

The client reads every readable characteristic, writes a test pattern to every
writable one and verifies the read-back, subscribes to notify/indicate
characteristics, and exits non-zero on any mismatch — suitable for scripting.

`web_client.html` offers the same operations from a Chromium-based browser
(must be served over `https://` or `http://localhost`).

### Hardware-free end-to-end test (`bsim/`)

Each generated output contains a `bsim/` BabbleSim self-test. One binary
plays both roles: the `peripheral` device advertises and serves the generated
GATT services, the `central` device scans, connects, discovers every
characteristic by UUID, reads back readable values, writes and verifies
writable ones, subscribes to every CCC, and counts the notifications the
peripheral then pushes.

```bash
# One-time: fetch and build BabbleSim in your west workspace
cd <west-workspace>
west config manifest.group-filter -- +babblesim
west update
make -C tools/bsim everything -j$(nproc)

# Then, from anywhere with ZEPHYR_BASE set:
export ZEPHYR_BASE=/path/to/zephyr
my_app/bsim/run_test.sh            # builds the test binary on first run
my_app/bsim/run_test.sh --rebuild  # force a rebuild
```

The script exits non-zero on failure and both devices print `passed` on
success. `bsim/testcase.yaml` is Twister-compatible (`harness: bsim`,
`build_only`), so the test app also builds in `west twister` runs on
`nrf52_bsim`. `scripts/test_bsim.sh` runs the self-test for every sample in
this repository, and CI does the same.

Characteristics with `read_authen`/`write_authen`/`read_lesc`/`write_lesc`
permissions request `BT_SECURITY_L3`/`L4` pairing in the test; the plain
`*_encrypt` permissions use just-works pairing to `BT_SECURITY_L2`, which the
simulated link supports out of the box.

## Profile reference

```yaml
profile:
  name: my_profile                # C identifier; used for CONFIG_BT_DEVICE_NAME
  services:
    - name: battery               # C identifier; prefix for all generated symbols
      uuid: 180f                  # 16-bit (xxxx) or 128-bit (8-4-4-4-12) UUID
      characteristics:
        - name: level
          uuid: 2a19
          size: 1                 # value buffer size in bytes (1..512)
          thread_safe: true       # default true; false skips the k_mutex
          properties: [read, notify]
          permissions: [read]
          descriptors:
            - type: cud           # Characteristic User Description
              value: "Battery level"
            - type: cpf           # Characteristic Presentation Format
              format: 4           # uint8
              exponent: 0
              unit: 0x27ad        # percentage
              name_space: 1
              description: 0
        - name: control
          uuid: 12345678-1234-5678-1234-56789abcdef1
          size: 4
          properties: [read, write, extended_properties]
          permissions: [read_encrypt, write_encrypt, prepare_write]
          descriptors:
            - type: cep           # Characteristic Extended Properties
              reliable_write: true
```

**Properties** map to `BT_GATT_CHRC_*`: `broadcast`, `read`,
`write_without_response`, `write`, `notify`, `indicate`,
`authenticated_signed_writes`, `extended_properties`.

**Permissions** map to `BT_GATT_PERM_*`: `read`, `write`, `read_encrypt`,
`write_encrypt`, `read_authen`, `write_authen`, `read_lesc`, `write_lesc`,
`prepare_write`. Any encrypted/authenticated permission automatically enables
`CONFIG_BT_SMP` in the generated `prj.conf`.

Validation rules enforced at load time:

* `read` requires a read permission; `write`/`write_without_response` require a
  write permission.
* `notify` and `indicate` are mutually exclusive on one characteristic (v1).
* `broadcast` and `authenticated_signed_writes` only set the characteristic
  property bit; they do not change the generated callbacks.

## Examples

| Profile                       | Demonstrates                                                       |
| ----------------------------- | ------------------------------------------------------------------ |
| `examples/minimal.yaml`       | One service, read-only and read/write characteristics.             |
| `examples/notify.yaml`        | Notify, CCC, CUD/CPF/CEP descriptors, prepare-write permission.    |
| `examples/secure.yaml`        | Encrypted read/write (`CONFIG_BT_SMP` auto-enabled).               |
| `examples/multi_service.yaml` | Two services, notify + indicate, write-only and notify-only chars. |
| `examples/kitchen_sink.yaml`  | Every property, permission level and descriptor; 3 services.       |

Each `examples/*.yaml` has a matching generated `samples/gatt_gen_*`
directory (kept in sync by CI).
* A `cep` descriptor requires the `extended_properties` property.
* CCC descriptors are derived automatically from `notify`/`indicate`; do not
  list them.
* Names and UUIDs must be unique within their parent.

## Generated C API

For a characteristic `level` in service `battery`:

```c
#define BATTERY_UUID        BT_UUID_DECLARE_16(0x180f)
#define BATTERY_LEVEL_UUID  BT_UUID_DECLARE_16(0x2a19)
#define BATTERY_LEVEL_SIZE  1

int  battery_level_set(const uint8_t *data, uint16_t len);   /* thread-safe */
int  battery_level_get(uint8_t *data, uint16_t len);         /* thread-safe */
int  battery_level_notify(const uint8_t *data, uint16_t len); /* if notify */
int  battery_level_indicate(const uint8_t *data, uint16_t len); /* if indicate */

/* Weak hook, only for writable characteristics. Define it in your code: */
void battery_control_on_write(const uint8_t *data, uint16_t len);
```

Read/write GATT callbacks, prepare-write handling, CCC change logging and the
descriptor tables are generated for you.

## Repository layout

```
.
├── examples/                   # Example YAML profiles (one per sample)
├── samples/                    # Generated samples (kept in sync by CI)
├── scripts/
│   ├── ci.sh                   # Build every sample for native_sim
│   ├── test_bsim.sh            # Build + run every sample's BabbleSim self-test
│   └── regen_samples.sh        # Regenerate + clang-format all samples
├── src/ble_gatt_generator/
│   ├── cli.py                  # click entry point
│   ├── schema.py               # Pydantic profile model + validation
│   ├── generator.py            # Jinja2 rendering, overwrite policy
│   ├── west.py                 # `west gatt-gen` command
│   └── templates/
│       ├── zephyr/             # service.c/h, main.c, prj.conf, CMake, sample.yaml
│       ├── clients/            # Bleak client, Web Bluetooth page
│       └── bsim/               # BabbleSim two-device self-test
├── tests/                      # pytest suite (schema + generator)
├── west-commands.yml
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

## Development

```bash
pip install -e ".[dev]"
pytest -q                                              # unit tests, no Zephyr needed

export ZEPHYR_BASE=/path/to/zephyr
export PYTHON_EXECUTABLE=$(which python)               # one with Zephyr's requirements
bash scripts/regen_samples.sh                          # after editing templates
bash scripts/ci.sh                                     # build all samples for native_sim
bash scripts/test_bsim.sh                              # needs a compiled BabbleSim
```

`.github/workflows/ci.yml` runs the unit tests, checks that `samples/` match
the templates, builds every sample for `native_sim`, and runs the generated
BabbleSim self-tests on `nrf52_bsim`.

## Feature status

| Feature                                                        | Status  |
| -------------------------------------------------------------- | ------- |
| YAML profile schema with Pydantic validation                   | Done    |
| `BT_GATT_SERVICE_DEFINE` / `BT_GATT_CHARACTERISTIC` generation | Done    |
| Read, write, write-without-response, notify, indicate          | Done    |
| Encrypted / authenticated / LESC permissions, `CONFIG_BT_SMP`  | Done    |
| `k_mutex`-protected `get_*` / `set_*` helpers                  | Done    |
| `BT_GATT_CCC`, `BT_GATT_CUD`, `BT_GATT_CPF`, `BT_GATT_CEP`     | Done    |
| Prepare-write aware write callback, weak `on_write` hooks      | Done    |
| User-owned file protection with `--force`                      | Done    |
| Python/Bleak and Web Bluetooth test clients (multi-service)    | Done    |
| `west gatt-gen` extension                                      | Done    |
| Unit tests + `native_sim` CI                                   | Done    |
| BabbleSim two-device self-tests (`bsim/`, `nrf52_bsim`)        | Done    |
| Included services, multiple notify targets per connection      | Planned |

## License

Apache-2.0 (same as Zephyr).
