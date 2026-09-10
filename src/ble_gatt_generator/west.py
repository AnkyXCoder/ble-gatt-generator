"""West extension for ble-gatt-generator."""

from __future__ import annotations

import sys
from pathlib import Path

from west.commands import WestCommand


def _import_core() -> tuple:
    """Import schema and generator, falling back to the source tree."""
    try:
        from ble_gatt_generator.schema import load_profile
        from ble_gatt_generator.generator import generate
    except ImportError:
        # Running from a west project without pip installing the package.
        repo_root = Path(__file__).parents[2]
        src = str(repo_root / "src")
        if src not in sys.path:
            sys.path.insert(0, src)
        from ble_gatt_generator.schema import load_profile
        from ble_gatt_generator.generator import generate
    return load_profile, generate


class GattGen(WestCommand):
    """West command: gatt-gen"""

    def __init__(self) -> None:
        super().__init__(
            "gatt-gen",
            "Generate a Zephyr BLE GATT service from a YAML profile.",
            """Generate idiomatic Zephyr C/H source, prj.conf, build files,
            a Bleak test client, and a Web Bluetooth test page from a YAML
            GATT profile.""",
            accepts_unknown_args=False,
        )

    def do_add_parser(self, parser_adder):
        parser = parser_adder.add_parser(
            self.name, help=self.help, description=self.description
        )
        parser.add_argument(
            "-i",
            "--input",
            required=True,
            help="Input YAML profile.",
        )
        parser.add_argument(
            "-o",
            "--output",
            required=True,
            help="Output directory for generated artifacts.",
        )
        return parser

    def do_run(self, args, unknown_args) -> None:
        load_profile, generate = _import_core()
        profile = load_profile(args.input)
        output_dir = Path(args.output)
        generate(profile, output_dir)
        print(f"Generated {len(profile.services)} service(s) into {output_dir}")
