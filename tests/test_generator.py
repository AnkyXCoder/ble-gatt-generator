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
    assert _ad_uuid_type("12345678-1234-5678-1234-56789abcdef0") == "BT_DATA_UUID128_ALL"


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
    }
    assert (tmp_path / "test_client.py").stat().st_mode & 0o111


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
