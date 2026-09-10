"""Jinja2-based C/H and sample generator for Zephyr GATT services."""

from __future__ import annotations

import os
import re
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from ble_gatt_generator.schema import Profile, Service


def _uuid_128_parts(uuid: str) -> tuple[str, str, str, str, str]:
    """Return the 5 integer groups of a 128-bit UUID."""
    cleaned = uuid.replace("-", "").replace("0x", "").strip().lower()
    if len(cleaned) != 32:
        raise ValueError(f"Invalid 128-bit UUID: {uuid!r}")
    return (
        cleaned[0:8],
        cleaned[8:12],
        cleaned[12:16],
        cleaned[16:20],
        cleaned[20:32],
    )


def _uuid_macro(uuid: str) -> str:
    """Return a Zephyr UUID declaration macro for a service or characteristic."""
    if len(uuid) == 4:
        return f"BT_UUID_DECLARE_16(0x{uuid.lower()})"
    if "-" in uuid or len(uuid.replace("-", "").replace("0x", "").strip()) == 32:
        groups = _uuid_128_parts(uuid)
        return (
            "BT_UUID_DECLARE_128(BT_UUID_128_ENCODE("
            f"0x{groups[0]}, 0x{groups[1]}, 0x{groups[2]}, 0x{groups[3]}, 0x{groups[4]}"
            "))"
        )
    raise ValueError(f"Unsupported UUID format: {uuid!r}")


def _ad_uuid_bytes(uuid: str) -> str:
    """Return the UUID as a byte list for advertising data."""
    if len(uuid) == 4:
        return f"BT_UUID_16_ENCODE(0x{uuid.lower()})"
    groups = _uuid_128_parts(uuid)
    return f"BT_UUID_128_ENCODE(0x{groups[0]}, 0x{groups[1]}, 0x{groups[2]}, 0x{groups[3]}, 0x{groups[4]})"


def _c_guard(name: str) -> str:
    return f"BLE_GATT_GENERATOR_{re.sub(r'[^A-Z0-9]', '_', name.upper())}_H_"


def _make_env() -> Environment:
    env = Environment(
        loader=PackageLoader("ble_gatt_generator", "templates/zephyr"),
        autoescape=select_autoescape(disabled_extensions=("j2",)),
        keep_trailing_newline=True,
        lstrip_blocks=True,
        trim_blocks=True,
    )
    env.filters["uuid_macro"] = _uuid_macro
    env.filters["ad_uuid_bytes"] = _ad_uuid_bytes
    env.filters["c_guard"] = _c_guard
    return env


def generate(profile: Profile, output_dir: Path) -> None:
    """Render all artifacts for a profile into output_dir."""
    env = _make_env()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    src_dir = output_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    for service in profile.services:
        ctx = {
            "profile": profile,
            "service": service,
            "year": "2026",
        }

        c_template = env.get_template("service.c.j2")
        h_template = env.get_template("service.h.j2")

        c_path = src_dir / f"{service.name}_service.c"
        h_path = src_dir / f"{service.name}_service.h"

        c_path.write_text(c_template.render(ctx), encoding="utf-8")
        h_path.write_text(h_template.render(ctx), encoding="utf-8")

    main_template = env.get_template("main.c.j2")
    main_path = src_dir / "main.c"
    main_path.write_text(main_template.render({
        "profile": profile,
        "year": "2026",
    }), encoding="utf-8")

    for template_name, out_name in [
        ("prj.conf.j2", "prj.conf"),
        ("CMakeLists.txt.j2", "CMakeLists.txt"),
        ("sample.yaml.j2", "sample.yaml"),
    ]:
        text = env.get_template(template_name).render({"profile": profile})
        (output_dir / out_name).write_text(text, encoding="utf-8")

    clients_env = Environment(
        loader=PackageLoader("ble_gatt_generator", "templates/clients"),
        autoescape=select_autoescape(disabled_extensions=("j2",)),
        keep_trailing_newline=True,
        lstrip_blocks=True,
        trim_blocks=True,
    )
    client_ctx = {
        "profile": profile,
        "service": profile.services[0],
        "year": "2026",
    }
    bleak_t = clients_env.get_template("bleak_client.py.j2")
    (output_dir / "test_client.py").write_text(
        bleak_t.render(client_ctx), encoding="utf-8")
    (output_dir / "test_client.py").chmod(0o755)

    web_t = clients_env.get_template("web_client.html.j2")
    (output_dir / "web_client.html").write_text(
        web_t.render(client_ctx), encoding="utf-8")
