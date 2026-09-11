"""Pydantic models for the gatt-gen profile schema."""

from __future__ import annotations

import re
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


PROPERTY_MAP = {
    "broadcast": "BT_GATT_CHRC_BROADCAST",
    "read": "BT_GATT_CHRC_READ",
    "write_without_response": "BT_GATT_CHRC_WRITE_WITHOUT_RESP",
    "write": "BT_GATT_CHRC_WRITE",
    "notify": "BT_GATT_CHRC_NOTIFY",
    "indicate": "BT_GATT_CHRC_INDICATE",
    "authenticated_signed_writes": "BT_GATT_CHRC_AUTH",
    "extended_properties": "BT_GATT_CHRC_EXT_PROP",
}

PERMISSION_MAP = {
    "read": "BT_GATT_PERM_READ",
    "write": "BT_GATT_PERM_WRITE",
    "read_encrypt": "BT_GATT_PERM_READ_ENCRYPT",
    "write_encrypt": "BT_GATT_PERM_WRITE_ENCRYPT",
    "read_authen": "BT_GATT_PERM_READ_AUTHEN",
    "write_authen": "BT_GATT_PERM_WRITE_AUTHEN",
    "prepare_write": "BT_GATT_PERM_PREPARE_WRITE",
    "read_lesc": "BT_GATT_PERM_READ_LESC",
    "write_lesc": "BT_GATT_PERM_WRITE_LESC",
}


DESCRIPTOR_TYPES = {"cud", "cpf", "cep"}

READ_PERMISSIONS = {"read", "read_encrypt", "read_authen", "read_lesc"}
WRITE_PERMISSIONS = {"write", "write_encrypt", "write_authen", "write_lesc"}
SECURE_PERMISSIONS = {
    "read_encrypt", "write_encrypt", "read_authen",
    "write_authen", "read_lesc", "write_lesc",
}

_UUID16_RE = re.compile(r"^[0-9a-f]{4}$")
_UUID128_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def normalize_uuid(value: str) -> str:
    """Lowercase a UUID, strip an optional 0x prefix, and validate its shape."""
    v = value.strip().lower()
    if v.startswith("0x"):
        v = v[2:]
    if _UUID16_RE.match(v) or _UUID128_RE.match(v):
        return v
    raise ValueError(
        f"Invalid UUID {value!r}: expected 16-bit (e.g. 180f) or "
        "128-bit (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)")


class Descriptor(BaseModel):
    """A GATT descriptor attached to a characteristic."""

    type: str
    value: Optional[str] = None
    format: Optional[int] = None
    exponent: Optional[int] = None
    unit: Optional[int] = None
    name_space: Optional[int] = None
    description: Optional[int] = None
    reliable_write: Optional[bool] = None
    writable_aux: Optional[bool] = None

    @field_validator("type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in DESCRIPTOR_TYPES:
            raise ValueError(
                f"Unknown descriptor type: {v!r} (CCC is derived from notify/indicate)")
        return v

    @model_validator(mode="after")
    def _fields_match_type(self) -> "Descriptor":
        if self.type == "cud" and not self.value:
            raise ValueError("CUD descriptor requires a 'value' string")
        if self.type == "cpf" and self.format is None:
            raise ValueError("CPF descriptor requires at least a 'format'")
        if self.type == "cep" and not (self.reliable_write or self.writable_aux):
            raise ValueError(
                "CEP descriptor requires 'reliable_write' and/or 'writable_aux'")
        return self


class Characteristic(BaseModel):
    """A single GATT characteristic."""

    name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    uuid: str
    properties: list[str]
    permissions: list[str]
    size: int = Field(default=1, ge=1, le=512)
    thread_safe: bool = True
    variable: bool = False
    initial_value: Optional[str] = None
    descriptors: list[Descriptor] = Field(default_factory=list)

    @field_validator("uuid")
    @classmethod
    def _valid_uuid(cls, v: str) -> str:
        return normalize_uuid(v)

    @field_validator("initial_value")
    @classmethod
    def _valid_initial_value(cls, v: Optional[str]) -> Optional[str]:
        """Accept 0x-prefixed hex bytes or a plain string."""
        if v is None:
            return v
        if v.startswith("0x"):
            hexpart = v[2:]
            if not hexpart or len(hexpart) % 2:
                raise ValueError(
                    f"initial_value hex {v!r} needs an even number of digits")
            try:
                bytes.fromhex(hexpart)
            except ValueError:
                raise ValueError(
                    f"initial_value {v!r} is not valid hex") from None
        return v

    @field_validator("properties")
    @classmethod
    def _valid_properties(cls, v: list[str]) -> list[str]:
        for p in v:
            if p not in PROPERTY_MAP:
                raise ValueError(f"Unknown property: {p!r}")
        return v

    @field_validator("permissions")
    @classmethod
    def _valid_permissions(cls, v: list[str]) -> list[str]:
        for p in v:
            if p not in PERMISSION_MAP:
                raise ValueError(f"Unknown permission: {p!r}")
        return v

    @model_validator(mode="after")
    def _properties_consistent(self) -> "Characteristic":
        props = set(self.properties)
        perms = set(self.permissions)
        if not props:
            raise ValueError("A characteristic needs at least one property")
        if {"notify", "indicate"} <= props:
            raise ValueError(
                "A characteristic cannot be both notify and indicate in v1")
        if props & {"write", "write_without_response"} and not perms & WRITE_PERMISSIONS:
            raise ValueError("Write property requires a write permission")
        if "read" in props and not perms & READ_PERMISSIONS:
            raise ValueError("Read property requires a read permission")
        if self.cep_descriptor() and "extended_properties" not in props:
            raise ValueError(
                "CEP descriptor requires the 'extended_properties' property")
        types = [d.type for d in self.descriptors]
        if len(types) != len(set(types)):
            raise ValueError(
                "Duplicate descriptor types on one characteristic")
        if self.initial_bytes() and len(self.initial_bytes()) > self.size:
            raise ValueError(
                f"initial_value is {len(self.initial_bytes())} bytes but "
                f"size is {self.size}")
        return self

    def initial_bytes(self) -> bytes:
        """Return the decoded initial value, or empty bytes if unset."""
        if self.initial_value is None:
            return b""
        if self.initial_value.startswith("0x"):
            return bytes.fromhex(self.initial_value[2:])
        return self.initial_value.encode()

    def initial_c(self) -> str:
        """Return a C array initialiser for the decoded initial value."""
        return "{ " + ", ".join(f"0x{b:02x}" for b in self.initial_bytes()) + " }"

    def properties_macro(self) -> str:
        if not self.properties:
            return "0"
        return " | ".join(PROPERTY_MAP[p] for p in self.properties)

    def permissions_macro(self) -> str:
        if not self.permissions:
            return "BT_GATT_PERM_NONE"
        return " | ".join(PERMISSION_MAP[p] for p in self.permissions)

    def is_128_bit(self) -> bool:
        return "-" in self.uuid

    def has_read(self) -> bool:
        return "read" in self.properties

    def has_write(self) -> bool:
        return bool({"write", "write_without_response"} & set(self.properties))

    def has_notify(self) -> bool:
        return "notify" in self.properties

    def has_indicate(self) -> bool:
        return "indicate" in self.properties

    def needs_ccc(self) -> bool:
        return self.has_notify() or self.has_indicate()

    def ccc_flags(self) -> str:
        """Return the default CCC value string (e.g. BT_GATT_CCC_NOTIFY)."""
        flags = []
        if self.has_notify():
            flags.append("BT_GATT_CCC_NOTIFY")
        if self.has_indicate():
            flags.append("BT_GATT_CCC_INDICATE")
        return " | ".join(flags) if flags else "0"

    def _descriptor(self, kind: str) -> Optional[Descriptor]:
        return next((d for d in self.descriptors if d.type == kind), None)

    def cpf_descriptor(self) -> Optional[Descriptor]:
        return self._descriptor("cpf")

    def cep_descriptor(self) -> Optional[Descriptor]:
        return self._descriptor("cep")

    def cud_descriptor(self) -> Optional[Descriptor]:
        return self._descriptor("cud")


class Service(BaseModel):
    """A GATT service."""

    name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    uuid: str
    characteristics: list[Characteristic]

    @field_validator("uuid")
    @classmethod
    def _valid_uuid(cls, v: str) -> str:
        return normalize_uuid(v)

    @model_validator(mode="after")
    def _unique_characteristics(self) -> "Service":
        if not self.characteristics:
            raise ValueError(
                f"Service {self.name!r} needs at least one characteristic")
        names = [c.name for c in self.characteristics]
        if len(names) != len(set(names)):
            raise ValueError(
                f"Duplicate characteristic names in service {self.name!r}")
        uuids = [c.uuid for c in self.characteristics]
        if len(uuids) != len(set(uuids)):
            raise ValueError(
                f"Duplicate characteristic UUIDs in service {self.name!r}")
        return self

    def is_128_bit(self) -> bool:
        return "-" in self.uuid


class Profile(BaseModel):
    """Top-level GATT profile."""

    name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    role: str = "peripheral"
    services: list[Service]

    @field_validator("role")
    @classmethod
    def _valid_role(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ("peripheral", "central", "both"):
            raise ValueError(
                f"role must be peripheral, central or both, got {v!r}")
        return v

    @model_validator(mode="after")
    def _non_empty(self) -> "Profile":
        if not self.services:
            raise ValueError("At least one service is required")
        names = [s.name for s in self.services]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate service names in profile")
        return self

    def needs_smp(self) -> bool:
        """Return True if any characteristic requires encryption or authentication."""
        return any(
            set(chrc.permissions) & SECURE_PERMISSIONS
            for svc in self.services
            for chrc in svc.characteristics
        )

    def required_security(self) -> str:
        """Return the bt_security_t level needed by the strictest permission."""
        perms = {
            perm
            for svc in self.services
            for chrc in svc.characteristics
            for perm in chrc.permissions
        }
        if perms & {"read_lesc", "write_lesc"}:
            return "BT_SECURITY_L4"
        if perms & {"read_authen", "write_authen"}:
            return "BT_SECURITY_L3"
        return "BT_SECURITY_L2"

    def needs_mitm(self) -> bool:
        """Return True if any characteristic needs authenticated pairing."""
        return self.required_security() in ("BT_SECURITY_L3", "BT_SECURITY_L4")

    def needs_sc_only(self) -> bool:
        """Return True if any characteristic needs LE Secure Connections."""
        return self.required_security() == "BT_SECURITY_L4"

    def any_ccc(self) -> bool:
        """Return True if any characteristic supports notify or indicate."""
        return any(
            chrc.needs_ccc()
            for svc in self.services
            for chrc in svc.characteristics
        )

    def is_peripheral(self) -> bool:
        return self.role in ("peripheral", "both")

    def is_central(self) -> bool:
        return self.role in ("central", "both")

    def sig_uuid_warnings(self) -> list[str]:
        """Warn when custom entities use the SIG-reserved 16-bit UUID range."""
        warnings = []
        for svc in self.services:
            if not svc.is_128_bit():
                warnings.append(
                    f"service {svc.name!r} uses 16-bit UUID {svc.uuid} — "
                    "16-bit UUIDs are assigned by the Bluetooth SIG; use a "
                    "128-bit UUID for custom services")
            for chrc in svc.characteristics:
                if not chrc.is_128_bit():
                    warnings.append(
                        f"characteristic {svc.name}/{chrc.name} uses 16-bit "
                        f"UUID {chrc.uuid} — ensure it matches a SIG-assigned "
                        "characteristic")
        return warnings


def load_profile(path: str) -> Profile:
    """Load and validate a YAML profile."""
    with open(path, "r", encoding="utf-8") as f:
        data: Any = yaml.safe_load(f)
    if not isinstance(data, dict) or "profile" not in data:
        raise ValueError("YAML root must contain a 'profile' key")
    return Profile(**data["profile"])
