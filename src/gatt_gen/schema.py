"""Pydantic models for the gatt-gen profile schema."""

from __future__ import annotations

from typing import Any

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


class Characteristic(BaseModel):
    """A single GATT characteristic."""

    name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    uuid: str
    properties: list[str]
    permissions: list[str]
    size: int = Field(default=1, ge=0)
    thread_safe: bool = True

    @field_validator("uuid")
    @classmethod
    def _valid_uuid(cls, v: str) -> str:
        return v.lower().strip()

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
        if "notify" in self.properties and "indicate" in self.properties:
            raise ValueError("A characteristic cannot be both notify and indicate in v1")
        if "write" in self.properties or "write_without_response" in self.properties:
            if "write" not in self.permissions and "write_encrypt" not in self.permissions and "write_authen" not in self.permissions and "write_lesc" not in self.permissions:
                raise ValueError("Write property requires a write permission")
        if "read" in self.properties:
            if "read" not in self.permissions and "read_encrypt" not in self.permissions and "read_authen" not in self.permissions and "read_lesc" not in self.permissions:
                raise ValueError("Read property requires a read permission")
        return self

    def properties_macro(self) -> str:
        if not self.properties:
            return "0"
        return " | ".join(PROPERTY_MAP[p] for p in self.properties)

    def permissions_macro(self) -> str:
        if not self.permissions:
            return "BT_GATT_PERM_NONE"
        return " | ".join(PERMISSION_MAP[p] for p in self.permissions)

    def is_128_bit(self) -> bool:
        return len(self.uuid) > 6 or "-" in self.uuid


class Service(BaseModel):
    """A GATT service."""

    name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    uuid: str
    characteristics: list[Characteristic]

    @field_validator("uuid")
    @classmethod
    def _valid_uuid(cls, v: str) -> str:
        return v.lower().strip()

    def is_128_bit(self) -> bool:
        return len(self.uuid) > 6 or "-" in self.uuid


class Profile(BaseModel):
    """Top-level GATT profile."""

    name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    services: list[Service]

    @model_validator(mode="after")
    def _non_empty(self) -> "Profile":
        if not self.services:
            raise ValueError("At least one service is required")
        return self


def load_profile(path: str) -> Profile:
    """Load and validate a YAML profile."""
    with open(path, "r", encoding="utf-8") as f:
        data: Any = yaml.safe_load(f)
    if not isinstance(data, dict) or "profile" not in data:
        raise ValueError("YAML root must contain a 'profile' key")
    return Profile(**data["profile"])
