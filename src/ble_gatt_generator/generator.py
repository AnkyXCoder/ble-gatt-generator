"""Jinja2-based C/H, sample, and test-client generator for Zephyr GATT services."""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from ble_gatt_generator.schema import Profile

# Files that a user is expected to customise. They are written only once and
# then left untouched unless generate() is called with force=True.
USER_OWNED_FILES = ("src/main.c", "prj.conf", "CMakeLists.txt", "sample.yaml")


def _normalize_uuid(uuid: str) -> str:
    """Return a lowercase UUID string with an optional 0x prefix removed."""
    cleaned = uuid.strip().lower()
    return cleaned[2:] if cleaned.startswith("0x") else cleaned


def _is_128_bit(uuid: str) -> bool:
    return len(_normalize_uuid(uuid).replace("-", "")) == 32


def _uuid_128_parts(uuid: str) -> tuple[str, str, str, str, str]:
    """Return the 5 integer groups of a 128-bit UUID."""
    cleaned = _normalize_uuid(uuid).replace("-", "")
    if len(cleaned) != 32:
        raise ValueError(f"Invalid 128-bit UUID: {uuid!r}")
    return (
        cleaned[0:8],
        cleaned[8:12],
        cleaned[12:16],
        cleaned[16:20],
        cleaned[20:32],
    )


def _uuid_encode(uuid: str) -> str:
    """Return the BT_UUID_*_ENCODE(...) expression for a UUID."""
    cleaned = _normalize_uuid(uuid)
    if len(cleaned) == 4:
        return f"BT_UUID_16_ENCODE(0x{cleaned})"
    if _is_128_bit(cleaned):
        g = _uuid_128_parts(cleaned)
        return f"BT_UUID_128_ENCODE(0x{g[0]}, 0x{g[1]}, 0x{g[2]}, 0x{g[3]}, 0x{g[4]})"
    raise ValueError(f"Unsupported UUID format: {uuid!r}")


def _uuid_macro(uuid: str) -> str:
    """Return a Zephyr UUID declaration macro for a service or characteristic."""
    cleaned = _normalize_uuid(uuid)
    if len(cleaned) == 4:
        return f"BT_UUID_DECLARE_16(0x{cleaned})"
    return f"BT_UUID_DECLARE_128({_uuid_encode(cleaned)})"


def _ad_uuid_bytes(uuid: str) -> str:
    """Return the UUID as an encode-macro for advertising data."""
    return _uuid_encode(uuid)


def _ad_uuid_type(uuid: str) -> str:
    """Return the advertising data type matching the UUID width."""
    return "BT_DATA_UUID128_ALL" if _is_128_bit(uuid) else "BT_DATA_UUID16_ALL"


def _client_uuid(uuid: str) -> str:
    """Return a UUID string usable by Bleak / Web Bluetooth.

    16-bit UUIDs are expanded to the Bluetooth Base UUID form so that both
    client stacks can address them directly.
    """
    cleaned = _normalize_uuid(uuid)
    if len(cleaned) == 4:
        return f"0000{cleaned}-0000-1000-8000-00805f9b34fb"
    return cleaned


def _c_guard(name: str) -> str:
    return f"BLE_GATT_GENERATOR_{re.sub(r'[^A-Z0-9]', '_', name.upper())}_H_"


def _make_env(subdir: str) -> Environment:
    env = Environment(
        loader=PackageLoader("ble_gatt_generator", f"templates/{subdir}"),
        autoescape=select_autoescape(disabled_extensions=("j2",)),
        keep_trailing_newline=True,
        lstrip_blocks=True,
        trim_blocks=True,
    )
    env.filters["uuid_macro"] = _uuid_macro
    env.filters["ad_uuid_bytes"] = _ad_uuid_bytes
    env.filters["ad_uuid_type"] = _ad_uuid_type
    env.filters["client_uuid"] = _client_uuid
    env.filters["c_guard"] = _c_guard
    return env


def _write(path: Path, text: str, *, force: bool, user_owned: bool) -> bool:
    """Write text to path, honouring the user-owned protection rule.

    Returns True if the file was written.
    """
    if user_owned and path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def generate(profile: Profile, output_dir: Path, *, force: bool = False) -> list[Path]:
    """Render all artifacts for a profile into output_dir.

    Generated service sources (``src/<service>_service.[ch]``) and test clients
    are always overwritten. Files listed in USER_OWNED_FILES are created only if
    missing unless ``force`` is set, so hand-edited application code survives
    regeneration.

    Returns the list of paths that were written.
    """
    zephyr = _make_env("zephyr")
    clients = _make_env("clients")
    output_dir = Path(output_dir)
    src_dir = output_dir / "src"
    written: list[Path] = []
    base_ctx = {"profile": profile, "year": str(_dt.date.today().year)}

    for service in profile.services:
        ctx = {**base_ctx, "service": service}
        for tmpl, name in (("service.c.j2", ".c"), ("service.h.j2", ".h")):
            path = src_dir / f"{service.name}_service{name}"
            if _write(path, zephyr.get_template(tmpl).render(ctx),
                      force=True, user_owned=False):
                written.append(path)

    for tmpl, rel in (
        ("main.c.j2", "src/main.c"),
        ("prj.conf.j2", "prj.conf"),
        ("CMakeLists.txt.j2", "CMakeLists.txt"),
        ("sample.yaml.j2", "sample.yaml"),
    ):
        path = output_dir / rel
        if _write(path, zephyr.get_template(tmpl).render(base_ctx),
                  force=force, user_owned=rel in USER_OWNED_FILES):
            written.append(path)

    for tmpl, rel, mode in (
        ("bleak_client.py.j2", "test_client.py", 0o755),
        ("web_client.html.j2", "web_client.html", None),
    ):
        path = output_dir / rel
        if _write(path, clients.get_template(tmpl).render(base_ctx),
                  force=True, user_owned=False):
            if mode is not None:
                path.chmod(mode)
            written.append(path)

    return written
