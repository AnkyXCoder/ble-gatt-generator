"""ble-gatt-generator CLI entry point."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from pydantic import ValidationError

from ble_gatt_generator import __version__
from ble_gatt_generator.generator import generate
from ble_gatt_generator.schema import Profile, load_profile


@click.group(invoke_without_command=True)
@click.option(
    "-i",
    "--input",
    "input_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Input YAML profile.",
)
@click.option(
    "-o",
    "--output",
    "output_dir",
    type=click.Path(file_okay=False, path_type=Path),
    help="Output directory for generated artifacts.",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Overwrite user-owned files (main.c, prj.conf, CMakeLists.txt, sample.yaml).",
)
@click.option(
    "--services-only",
    is_flag=True,
    help="Emit only src/<service>_service.[ch] — no app, clients or bsim files.",
)
@click.option(
    "--no-clients",
    is_flag=True,
    help="Skip the Bleak/Web Bluetooth test clients.",
)
@click.option(
    "--no-bsim",
    is_flag=True,
    help="Skip the BabbleSim self-test under bsim/.",
)
@click.version_option(version=__version__)
@click.pass_context
def main(
    ctx: click.Context,
    input_file: Path | None,
    output_dir: Path | None,
    force: bool,
    services_only: bool,
    no_clients: bool,
    no_bsim: bool,
) -> None:
    """Generate a Zephyr GATT service from a YAML profile."""
    if ctx.invoked_subcommand is not None:
        return
    if input_file is None or output_dir is None:
        raise click.UsageError(
            "-i/--input and -o/--output are required "
            "(or use a subcommand; see --help)")

    profile = _load(input_file)
    for warning in profile.sig_uuid_warnings():
        click.echo(f"warning: {warning}", err=True)

    written = generate(
        profile,
        output_dir,
        force=force,
        services_only=services_only,
        clients=not no_clients,
        bsim=not no_bsim,
    )
    click.echo(
        f"Generated {len(profile.services)} service(s), "
        f"{len(written)} file(s) into {output_dir}"
    )


def _load(input_file: Path) -> Profile:
    try:
        return load_profile(str(input_file))
    except (ValidationError, ValueError) as exc:
        raise click.ClickException(
            f"Invalid profile {input_file}:\n{exc}") from exc


@main.command(name="export-schema")
@click.option(
    "-o",
    "--output",
    "output_file",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Where to write the JSON schema (stdout if omitted).",
)
def export_schema(output_file: Path | None) -> None:
    """Print the JSON schema for profile YAML files (editor validation)."""
    text = json.dumps(Profile.model_json_schema(), indent=2)
    if output_file is None:
        sys.stdout.write(text + "\n")
    else:
        output_file.write_text(text + "\n", encoding="utf-8")
        click.echo(f"Wrote {output_file}")


if __name__ == "__main__":
    main()
