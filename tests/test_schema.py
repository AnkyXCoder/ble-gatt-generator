"""Schema validation tests."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from ble_gatt_generator.schema import (
    Characteristic,
    Descriptor,
    Profile,
    Service,
    load_profile,
    normalize_uuid,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _chrc(**overrides):
    base = {
        "name": "value",
        "uuid": "2a19",
        "properties": ["read"],
        "permissions": ["read"],
        "size": 1,
    }
    base.update(overrides)
    return Characteristic(**base)


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.yaml")))
def test_examples_load(path):
    profile = load_profile(str(path))
    assert profile.services


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("180F", "180f"),
        ("0x180f", "180f"),
        (" 12345678-1234-5678-1234-56789ABCDEF0 ", "12345678-1234-5678-1234-56789abcdef0"),
    ],
)
def test_normalize_uuid(raw, expected):
    assert normalize_uuid(raw) == expected


@pytest.mark.parametrize("raw", ["180", "12345", "not-a-uuid", "1234567812345678123456789abcdef0"])
def test_normalize_uuid_rejects_bad_shapes(raw):
    with pytest.raises(ValueError):
        normalize_uuid(raw)


def test_unknown_property_rejected():
    with pytest.raises(ValidationError, match="Unknown property"):
        _chrc(properties=["bogus"])


def test_unknown_permission_rejected():
    with pytest.raises(ValidationError, match="Unknown permission"):
        _chrc(permissions=["bogus"])


def test_read_requires_read_permission():
    with pytest.raises(ValidationError, match="Read property requires"):
        _chrc(properties=["read"], permissions=["write"])


def test_write_requires_write_permission():
    with pytest.raises(ValidationError, match="Write property requires"):
        _chrc(properties=["write"], permissions=["read"])


def test_encrypted_permission_satisfies_read():
    c = _chrc(permissions=["read_encrypt"])
    assert c.permissions_macro() == "BT_GATT_PERM_READ_ENCRYPT"


def test_notify_and_indicate_exclusive():
    with pytest.raises(ValidationError, match="notify and indicate"):
        _chrc(properties=["read", "notify", "indicate"])


def test_ccc_flags_follow_properties():
    assert _chrc(properties=["read", "notify"]).ccc_flags() == "BT_GATT_CCC_NOTIFY"
    assert _chrc(properties=["read", "indicate"]).ccc_flags() == "BT_GATT_CCC_INDICATE"
    assert _chrc().needs_ccc() is False


def test_size_bounds():
    with pytest.raises(ValidationError):
        _chrc(size=0)
    with pytest.raises(ValidationError):
        _chrc(size=513)


def test_macros_join_with_pipes():
    c = _chrc(properties=["read", "write"], permissions=["read", "write"])
    assert c.properties_macro() == "BT_GATT_CHRC_READ | BT_GATT_CHRC_WRITE"
    assert c.permissions_macro() == "BT_GATT_PERM_READ | BT_GATT_PERM_WRITE"


def test_descriptor_type_validation():
    with pytest.raises(ValidationError, match="Unknown descriptor type"):
        Descriptor(type="ccc")
    with pytest.raises(ValidationError, match="CUD descriptor requires"):
        Descriptor(type="cud")
    with pytest.raises(ValidationError, match="CPF descriptor requires"):
        Descriptor(type="cpf")
    with pytest.raises(ValidationError, match="CEP descriptor requires"):
        Descriptor(type="cep")


def test_cep_requires_extended_properties():
    with pytest.raises(ValidationError, match="extended_properties"):
        _chrc(descriptors=[{"type": "cep", "reliable_write": True}])
    c = _chrc(
        properties=["read", "extended_properties"],
        descriptors=[{"type": "cep", "reliable_write": True}],
    )
    assert c.cep_descriptor() is not None


def test_duplicate_descriptor_types_rejected():
    with pytest.raises(ValidationError, match="Duplicate descriptor"):
        _chrc(descriptors=[{"type": "cud", "value": "a"}, {"type": "cud", "value": "b"}])


def test_service_rejects_duplicate_characteristics():
    a = {"name": "x", "uuid": "2a19", "properties": ["read"], "permissions": ["read"]}
    with pytest.raises(ValidationError, match="Duplicate characteristic names"):
        Service(name="svc", uuid="180f", characteristics=[a, a])
    b = {**a, "name": "y"}
    with pytest.raises(ValidationError, match="Duplicate characteristic UUIDs"):
        Service(name="svc", uuid="180f", characteristics=[a, b])


def test_profile_requires_services_and_unique_names():
    with pytest.raises(ValidationError, match="At least one service"):
        Profile(name="p", services=[])
    svc = {
        "name": "svc",
        "uuid": "180f",
        "characteristics": [
            {"name": "x", "uuid": "2a19", "properties": ["read"], "permissions": ["read"]}
        ],
    }
    with pytest.raises(ValidationError, match="Duplicate service names"):
        Profile(name="p", services=[svc, svc])


def test_needs_smp():
    plain = load_profile(str(EXAMPLES / "minimal.yaml"))
    secure = load_profile(str(EXAMPLES / "secure.yaml"))
    assert plain.needs_smp() is False
    assert secure.needs_smp() is True


def test_load_profile_requires_root_key(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("services: []\n")
    with pytest.raises(ValueError, match="'profile' key"):
        load_profile(str(bad))
