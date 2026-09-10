"""gatt-gen CLI entry point."""

from __future__ import annotations

from pathlib import Path

import click

from gatt_gen.generator import generate
from gatt_gen.schema import load_profile


@click.command()
@click.option(
    "-i",
    "--input",
    "input_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Input YAML profile.",
)
@click.option(
    "-o",
    "--output",
    "output_dir",
    required=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Output directory for generated artifacts.",
)
@click.version_option(version="0.1.0")
def main(input_file: Path, output_dir: Path) -> None:
    """Generate a Zephyr GATT service from a YAML profile."""
    profile = load_profile(str(input_file))
    generate(profile, output_dir)
    click.echo(f"Generated {len(profile.services)} service(s) into {output_dir}")


if __name__ == "__main__":
    main()
