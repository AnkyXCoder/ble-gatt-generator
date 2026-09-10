"""Generator output tests (no Zephyr toolchain required)."""

import re
from pathlib import Path

import pytest

from ble_gatt_generator.generator import (
    USER_OWNED_FILES,
    _ad_uuid_type,
    _client_uuid,
    _uuid_macro,
    generate,
)
from ble_gatt_generator.schema import load_profile

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def notify_profile():
    return load_profile(str(EXAMPLES / "notify.yaml"))


@pytest.fixture
def secure_profile():
    return load_profile(str(EXAMPLES / "secure.yaml"))


def test_uuid_macro_16_and_128():
    assert _uuid_macro("180f") == "BT_UUID_DECLARE_16(0x180f)"
    assert _uuid_macro("0x180F") == "BT_UUID_DECLARE_16(0x180f)"
    assert _uuid_macro("12345678-1234-5678-1234-56789abcdef0") == (
        "BT_UUID_DECLARE_128(BT_UUID_128_ENCODE("
        "0x12345678, 0x1234, 0x5678, 0x1234, 0x56789abcdef0))"
    )


def test_ad_uuid_type():
    assert _ad_uuid_type("180f") == "BT_DATA_UUID16_ALL"
    assert _ad_uuid_type(
        "12345678-1234-5678-1234-56789abcdef0") == "BT_DATA_UUID128_ALL"


def test_client_uuid_expands_16_bit():
    assert _client_uuid("2a19") == "00002a19-0000-1000-8000-00805f9b34fb"
    full = "12345678-1234-5678-1234-56789abcdef0"
    assert _client_uuid(full) == full


def test_generate_writes_expected_files(tmp_path, notify_profile):
    written = generate(notify_profile, tmp_path)
    names = {p.relative_to(tmp_path).as_posix() for p in written}
    assert names == {
        "src/notify_svc_service.c",
        "src/notify_svc_service.h",
        "src/main.c",
        "prj.conf",
        "CMakeLists.txt",
        "sample.yaml",
        "test_client.py",
        "web_client.html",
        "bsim/CMakeLists.txt",
        "bsim/prj.conf",
        "bsim/testcase.yaml",
        "bsim/run_test.sh",
        "bsim/src/main.c",
        "bsim/src/peripheral.c",
        "bsim/src/central.c",
    }
    assert (tmp_path / "test_client.py").stat().st_mode & 0o111
    assert (tmp_path / "bsim/run_test.sh").stat().st_mode & 0o111


def test_user_owned_files_not_clobbered(tmp_path, notify_profile):
    generate(notify_profile, tmp_path)
    marker = "/* hand edited */\n"
    for rel in USER_OWNED_FILES:
        (tmp_path / rel).write_text(marker)

    written = generate(notify_profile, tmp_path)
    rewritten = {p.relative_to(tmp_path).as_posix() for p in written}
    assert not rewritten & set(USER_OWNED_FILES)
    for rel in USER_OWNED_FILES:
        assert (tmp_path / rel).read_text() == marker

    generate(notify_profile, tmp_path, force=True)
    for rel in USER_OWNED_FILES:
        assert (tmp_path / rel).read_text() != marker


def test_service_c_contents(tmp_path, notify_profile):
    generate(notify_profile, tmp_path)
    c = (tmp_path / "src/notify_svc_service.c").read_text()
    h = (tmp_path / "src/notify_svc_service.h").read_text()

    assert "BT_GATT_SERVICE_DEFINE(notify_svc," in c
    assert "static K_MUTEX_DEFINE(notify_svc_button_lock);" in c
    assert "BT_GATT_CCC(notify_svc_button_ccc_cfg_changed" in c
    assert 'BT_GATT_CUD("Button state", BT_GATT_PERM_READ)' in c
    assert "BT_GATT_CPF(&notify_svc_button_cpf)" in c
    assert "BT_GATT_CEP(&notify_svc_led_cep)" in c
    assert ".properties = BT_GATT_CEP_RELIABLE_WRITE," in c
    assert "int notify_svc_button_notify(const uint8_t *data, uint16_t len)" in c
    assert "bt_gatt_notify_uuid(" in c
    assert "BT_GATT_WRITE_FLAG_PREPARE" in c
    assert "__weak void notify_svc_led_on_write(" in c
    # read-only characteristics must not get a write hook
    assert "notify_svc_button_on_write" not in c

    assert "#define NOTIFY_SVC_BUTTON_SIZE 1" in h
    assert "void notify_svc_led_on_write(const uint8_t *data, uint16_t len);" in h
    assert "notify_svc_button_indicate" not in h
    assert "SPDX-License-Identifier: Apache-2.0" in h
    assert 'extern "C"' in h


def test_thread_safe_false_omits_mutex(tmp_path, notify_profile):
    notify_profile.services[0].characteristics[0].thread_safe = False
    generate(notify_profile, tmp_path)
    c = (tmp_path / "src/notify_svc_service.c").read_text()
    assert "notify_svc_button_lock" not in c
    assert "notify_svc_led_lock" in c


def test_prj_conf_enables_smp_only_when_needed(tmp_path, notify_profile, secure_profile):
    generate(notify_profile, tmp_path / "a")
    generate(secure_profile, tmp_path / "b")
    assert "CONFIG_BT_SMP" not in (tmp_path / "a/prj.conf").read_text()
    assert "CONFIG_BT_SMP=y" in (tmp_path / "b/prj.conf").read_text()


def test_clients_cover_every_characteristic(tmp_path, notify_profile):
    generate(notify_profile, tmp_path)
    py = (tmp_path / "test_client.py").read_text()
    html = (tmp_path / "web_client.html").read_text()
    for svc in notify_profile.services:
        assert svc.uuid in py and svc.uuid in html
        for chrc in svc.characteristics:
            assert chrc.uuid in py and chrc.uuid in html
            assert f'"{chrc.name}"' in py and f'"{chrc.name}"' in html
    assert "get_services" not in py  # deprecated Bleak API


def test_generated_c_has_no_tabs_after_spaces_mix(tmp_path, notify_profile):
    """Guard against indentation mixing that clang-format would flag."""
    generate(notify_profile, tmp_path)
    c = (tmp_path / "src/notify_svc_service.c").read_text()
    for line in c.splitlines():
        assert not re.match(r"^ +\t", line), line


def test_bsim_artifacts_cover_every_characteristic(tmp_path, notify_profile):
    generate(notify_profile, tmp_path)
    central = (tmp_path / "bsim/src/central.c").read_text()
    peripheral = (tmp_path / "bsim/src/peripheral.c").read_text()

    for svc in notify_profile.services:
        for chrc in svc.characteristics:
            base = f"{svc.name}_{chrc.name}"
            assert f"{base}_handle = discover_chrc(" in central
            if chrc.has_read():
                assert f"read_chrc({base}_handle)" in central
            if chrc.has_write():
                assert f"{base}_handle, pattern" in central
            if chrc.needs_ccc():
                assert f"{base}_sub.value_handle" in central
                assert f"{base}_received" in central
            if chrc.has_notify():
                assert f"{base}_notify(payload" in peripheral
            if chrc.has_indicate():
                assert f"{base}_indicate(payload" in peripheral

    # Both roles registered for the same binary.
    main_c = (tmp_path / "bsim/src/main.c").read_text()
    assert "test_peripheral_install" in main_c
    assert "test_central_install" in main_c
    assert 'test_id = "peripheral"' in peripheral
    assert 'test_id = "central"' in central


def test_bsim_testcase_and_run_script(tmp_path, notify_profile):
    generate(notify_profile, tmp_path)
    testcase = (tmp_path / "bsim/testcase.yaml").read_text()
    run = (tmp_path / "bsim/run_test.sh").read_text()

    assert "harness: bsim" in testcase
    assert "nrf52_bsim/native" in testcase
    assert "bsim_exe_name: gatt_gen_gatt_gen_notify_selftest" in testcase
    assert "bs_nrf52_bsim_native_gatt_gen_gatt_gen_notify_selftest" in run
    assert "-testid=central" in run and "-testid=peripheral" in run
    assert "bs_2G4_phy_v1" in run


def test_bsim_prj_conf_security(tmp_path, notify_profile, secure_profile):
    generate(notify_profile, tmp_path / "a")
    generate(secure_profile, tmp_path / "b")

    conf_a = (tmp_path / "a/bsim/prj.conf").read_text()
    conf_b = (tmp_path / "b/bsim/prj.conf").read_text()
    central_b = (tmp_path / "b/bsim/src/central.c").read_text()

    for conf in (conf_a, conf_b):
        assert "CONFIG_BT_CENTRAL=y" in conf
        assert "CONFIG_BT_PERIPHERAL=y" in conf
        assert "CONFIG_BT_GATT_CLIENT=y" in conf
        assert "CONFIG_BT_GATT_AUTO_DISCOVER_CCC=y" in conf

    assert "CONFIG_BT_SMP" not in conf_a
    assert "CONFIG_BT_SMP=y" in conf_b
    assert "bt_conn_set_security" in central_b
    assert "BT_SECURITY_L2" in central_b


def test_bsim_no_ccc_profile_has_no_subscription(tmp_path):
    profile = load_profile(str(EXAMPLES / "minimal.yaml"))
    generate(profile, tmp_path)
    central = (tmp_path / "bsim/src/central.c").read_text()
    assert "bt_gatt_subscribe" not in central
    assert "_subscribed" not in central


def test_multi_service_example(tmp_path):
    profile = load_profile(str(EXAMPLES / "multi_service.yaml"))
    written = generate(profile, tmp_path)
    names = {p.relative_to(tmp_path).as_posix() for p in written}

    assert "src/sensor_svc_service.c" in names
    assert "src/device_svc_service.c" in names
    cmake = (tmp_path / "CMakeLists.txt").read_text()
    assert "sensor_svc_service.c" in cmake
    assert "device_svc_service.c" in cmake

    central = (tmp_path / "bsim/src/central.c").read_text()
    assert "sensor_svc_temperature_handle" in central
    assert "device_svc_reboot_handle" in central
    # indicate characteristic uses the indicate helper on the peripheral
    peripheral = (tmp_path / "bsim/src/peripheral.c").read_text()
    assert "sensor_svc_humidity_indicate(payload" in peripheral
    assert "device_svc_event_flag_notify(payload" in peripheral


def test_kitchen_sink_example_security_levels(tmp_path):
    profile = load_profile(str(EXAMPLES / "kitchen_sink.yaml"))
    assert len(profile.services) == 3
    assert profile.required_security() == "BT_SECURITY_L4"
    assert profile.needs_mitm()
    assert profile.needs_sc_only()

    generate(profile, tmp_path)
    conf = (tmp_path / "bsim/prj.conf").read_text()
    assert "CONFIG_BT_SMP=y" in conf
    assert "CONFIG_BT_FIXED_PASSKEY=y" in conf
    assert "CONFIG_BT_SMP_SC_ONLY=y" in conf

    central = (tmp_path / "bsim/src/central.c").read_text()
    peripheral = (tmp_path / "bsim/src/peripheral.c").read_text()
    assert "bt_passkey_set(TEST_PASSKEY)" in central
    assert "bt_conn_auth_cb_register" in central
    assert "bt_passkey_set(TEST_PASSKEY)" in peripheral
    assert "bt_gatt_get_mtu" in central

    # every characteristic is exercised by the generated central
    for svc in profile.services:
        for chrc in svc.characteristics:
            assert f"{svc.name}_{chrc.name}_handle" in central
