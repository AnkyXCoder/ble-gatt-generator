# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- M6: BabbleSim self-test generation
  - Every generated output gains a `bsim/` directory with a two-device
    `nrf52_bsim` self-test: the `peripheral` role runs the generated GATT
    services and pushes notifications/indications, the `central` role scans,
    connects, discovers every characteristic by UUID, verifies reads,
    write/read-back and CCC subscriptions, and counts incoming values
  - Devices coordinate over the `babblekit` backchannel (`bk_sync`), so the
    test needs no external orchestration; `bsim/run_test.sh` builds the binary
    on first run and launches the 2-device simulation
  - Twister-compatible `bsim/testcase.yaml` (`harness: bsim`, `build_only`)
  - `scripts/test_bsim.sh` runs the self-test for every sample; a
    `bsim-self-tests` CI job fetches/builds BabbleSim and runs it
  - Profiles with encrypted/authenticated permissions pair to the required
    `BT_SECURITY_L2`–`L4` level before exercising the attributes; L3/L4 use
    `CONFIG_BT_FIXED_PASSKEY` pairing inside the simulation
    (`CONFIG_BT_SMP_SC_ONLY` for LESC)
  - `Profile.required_security()`, `Profile.needs_mitm()`,
    `Profile.needs_sc_only()` and `Profile.any_ccc()` schema helpers
  - `examples/multi_service.yaml` (two services, notify + indicate) and
    `examples/kitchen_sink.yaml` (three services covering every property,
    permission level and descriptor, including broadcast,
    authenticated-signed-writes, extended properties and a 64-byte value)
- Generated central verification is ATT-MTU aware: reads expect
  `min(size, mtu-1)` bytes and writes are capped at `mtu-3` with partial
  read-back comparison

- Generation scope flags: `--services-only` emits only
  `src/<service>_service.[ch]`; `--no-clients`/`--no-bsim` skip those
  artifact groups (same flags on `west gatt-gen`)
- `initial_value` characteristic field (`0x…` hex or string) initialises the
  value buffer
- `variable` characteristic field tracks the actual written length and adds a
  `_len()` helper; reads serve the current length
- Weak application hooks for every characteristic: `_on_read()` before reads
  and `_on_ccc(enabled)` on CCC state changes (joining `_on_write()`)
- `role: peripheral|central|both` profile field (peripheral default); drives
  the generated Kconfig set
- Computed minimal-Kconfig report: `prj.conf` now carries the required
  symbols with advisory settings as comments, and `KCONFIG_NOTES.md`
  explains each requirement (MTU, SMP level, prepare-write buffers, signing,
  CCC persistence)
- `export-schema` subcommand dumps a JSON Schema of the profile format for
  editor validation
- 16-bit UUIDs on custom services/characteristics produce a warning about
  the SIG-assigned UUID range

### Changed

- `scripts/ci.sh` now builds every directory under `samples/` instead of a
  hardcoded list
- README: build/run instructions now use `west` commands only, and the
  profile reference was expanded into a full authoring guide with field,
  property, permission and descriptor tables plus a step-by-step example

- Renamed the project and package from `zephyr-gatt-gen` / `gatt_gen` to
  `ble-gatt-generator` / `ble_gatt_generator`
- Generated service now exposes `<SVC>_UUID`, `<SVC>_<CHRC>_UUID` and
  `<SVC>_<CHRC>_SIZE` macros; service table wrapped in `clang-format off/on`
  for one-attribute-per-line readability
- Write callback honours `BT_GATT_WRITE_FLAG_PREPARE` and calls a weak
  `<svc>_<chrc>_on_write()` hook after committing the value
- `main.c` includes every service header and picks
  `BT_DATA_UUID16_ALL`/`BT_DATA_UUID128_ALL` based on the UUID width
- Bleak client uses `client.services` (not the deprecated `get_services()`),
  covers all services, verifies write read-back and exits non-zero on failure
- Web client supports multiple services, hex input for writes, and
  subscribe/unsubscribe toggles
- Stricter schema validation: UUID shape, size 1..512, CEP requires
  `extended_properties`, no duplicate names/UUIDs/descriptor types, CCC is no
  longer a user-declared descriptor
- CLI/west now report Pydantic validation errors cleanly

### Added

- `--force` flag; `src/main.c`, `prj.conf`, `CMakeLists.txt` and `sample.yaml`
  are written once and never clobbered without it
- `tests/` pytest suite (36 tests) covering schema rules and generator output
- `scripts/regen_samples.sh` to regenerate and clang-format all samples
- GitHub Actions: unit tests on Python 3.10/3.12, stale-sample check, and
  `native_sim` builds in the Zephyr CI container
- `pyproject.toml` optional extras: `dev` (pytest) and `client` (bleak)

- M1: Minimal YAML-to-Zephyr GATT generator
  - `gatt-gen` CLI, Pydantic YAML schema, and Jinja2 templates
  - Generated `BT_GATT_SERVICE_DEFINE` C/H with SPDX headers and Doxygen comments
  - Generated `main.c`, `prj.conf`, `CMakeLists.txt`, and `sample.yaml`
  - `examples/minimal.yaml` and `samples/gatt_gen_minimal`
  - Verified `native_sim` build
- M2: Notify/indicate and descriptors
  - Added `notify` and `indicate` properties
  - Added per-characteristic `descriptors` support (`cud`, `cpf`, `cep`)
  - Generated `BT_GATT_CCC` with `cfg_changed` callback
  - Generated `*_notify()` and `*_indicate()` helpers
  - Added `examples/notify.yaml` and `samples/gatt_gen_notify`
  - Verified `native_sim` build
- M3: Thread-safe accessors and security Kconfig
  - Added `K_MUTEX_DEFINE` and lock-protected `get_*()`/`set_*()` helpers
  - Updated `read`/`write` callbacks, `notify()` and `indicate()` to use helpers
  - Added `Profile.needs_smp()` and automatic `CONFIG_BT_SMP` for
    encrypted/authenticated permissions
  - Added `examples/secure.yaml` and `samples/gatt_gen_secure`
  - Verified `native_sim` builds for `minimal`, `notify`, and `secure`
- Initial `README.md` and `CHANGELOG.md`
- M4: Test clients and CI
  - Added `bleak_client.py.j2` and `web_client.html.j2` client templates
  - Generate `test_client.py` and `web_client.html` with every profile
  - Added `scripts/ci.sh` to build all `native_sim` samples
  - Added `.github/workflows/ci.yml` for GitHub Actions
  - Verified all three samples pass `scripts/ci.sh`
- M5: Packaging and west extension
  - Fixed `pyproject.toml` distribution name and console script
  - Verified `pip install -e .` and `ble-gatt-generator` CLI
  - Added `west-commands.yml` and `src/ble_gatt_generator/west.py`
  - Added optional `west gatt-gen` extension command
