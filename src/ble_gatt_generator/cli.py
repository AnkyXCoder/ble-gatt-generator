"""ble-gatt-generator CLI entry point."""

from __future__ import annotations

from pathlib import Path

import click
from pydantic import ValidationError

from ble_gatt_generator import __version__
from ble_gatt_generator.generator import generate
from ble_gatt_generator.schema import load_profile


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
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Overwrite user-owned files (main.c, prj.conf, CMakeLists.txt, sample.yaml).",
)
@click.version_option(version=__version__)
def main(input_file: Path, output_dir: Path, force: bool) -> None:
    """Generate a Zephyr GATT service from a YAML profile."""
    try:
        profile = load_profile(str(input_file))
    except (ValidationError, ValueError) as exc:
        raise click.ClickException(
            f"Invalid profile {input_file}:\n{exc}") from exc

    written = generate(profile, output_dir, force=force)
    click.echo(
        f"Generated {len(profile.services)} service(s), "
        f"{len(written)} file(s) into {output_dir}"
    )


if __name__ == "__main__":
    main()
