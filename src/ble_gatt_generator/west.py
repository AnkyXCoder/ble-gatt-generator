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
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Overwrite user-owned files (main.c, prj.conf, CMakeLists.txt, sample.yaml).",
        )
        parser.add_argument(
            "--services-only",
            action="store_true",
            help="Emit only src/<service>_service.[ch].",
        )
        parser.add_argument(
            "--no-clients",
            action="store_true",
            help="Skip the Bleak/Web Bluetooth test clients.",
        )
        parser.add_argument(
            "--no-bsim",
            action="store_true",
            help="Skip the BabbleSim self-test under bsim/.",
        )
        return parser

    def do_run(self, args, unknown_args) -> None:
        load_profile, generate = _import_core()
        try:
            profile = load_profile(args.input)
        except ValueError as exc:
            self.die(f"Invalid profile {args.input}:\n{exc}")
        for warning in profile.sig_uuid_warnings():
            self.wrn(warning)
        output_dir = Path(args.output)
        written = generate(
            profile,
            output_dir,
            force=args.force,
            services_only=args.services_only,
            clients=not args.no_clients,
            bsim=not args.no_bsim,
        )
        self.inf(f"Generated {len(profile.services)} service(s), "
                 f"{len(written)} file(s) into {output_dir}")
