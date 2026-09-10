# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- Renamed the project and package from `zephyr-gatt-gen` / `gatt_gen` to
  `ble-gatt-generator` / `ble_gatt_generator`

### Added

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
