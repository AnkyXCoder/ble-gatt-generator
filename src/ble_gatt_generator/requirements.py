"""Compute the minimal Zephyr Kconfig set a generated profile needs.

The generator renders these requirements two ways: commented minimums in the
generated ``prj.conf`` and a human-readable ``KCONFIG_NOTES.md`` explaining
why each symbol is needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .schema import Profile


@dataclass
class KconfigReq:
    """One Kconfig symbol the generated application relies on."""

    symbol: str
    value: str  # "y" or a number as a string
    reason: str
    mandatory: bool = True  # False => advisory note, not emitted to prj.conf


def required_kconfigs(profile: "Profile") -> list[KconfigReq]:
    """Return the Kconfig requirements implied by the profile."""
    reqs: list[KconfigReq] = [
        KconfigReq("CONFIG_BT", "y", "Bluetooth host stack"),
        KconfigReq(
            "CONFIG_BT_DEVICE_NAME", f'"GATT Gen {profile.name}"',
            "Name shown to scanning peers",
        ),
    ]

    if profile.is_peripheral():
        reqs.append(
            KconfigReq("CONFIG_BT_PERIPHERAL", "y",
                       "Advertising / accepting connections (GATT server role)"))
    if profile.is_central():
        reqs += [
            KconfigReq("CONFIG_BT_CENTRAL", "y",
                       "Initiating connections (GATT client role)"),
            KconfigReq("CONFIG_BT_OBSERVER", "y",
                       "Scanning for advertising peers"),
            KconfigReq("CONFIG_BT_GATT_CLIENT", "y",
                       "Service discovery, reads, writes and subscriptions"),
        ]

    if profile.needs_smp():
        reqs.append(
            KconfigReq("CONFIG_BT_SMP", "y",
                       f"Encrypted/authenticated permissions need pairing "
                       f"({profile.required_security()})"))
        if profile.needs_mitm():
            reqs.append(
                KconfigReq(
                    "CONFIG_BT_FIXED_PASSKEY", "y",
                    "Used by the generated BabbleSim test only — do NOT enable "
                    "in production; a real device needs MITM-capable IO "
                    "(display/keyboard) or OOB instead",
                    mandatory=False))
        if profile.needs_sc_only():
            reqs.append(
                KconfigReq(
                    "CONFIG_BT_SMP_SC_ONLY", "y",
                    "read_lesc/write_lesc permissions need LE Secure "
                    "Connections pairing",
                    mandatory=False))

    props = {
        p
        for svc in profile.services
        for chrc in svc.characteristics
        for p in chrc.properties
    }
    perms = {
        p
        for svc in profile.services
        for chrc in svc.characteristics
        for p in chrc.permissions
    }

    if "authenticated_signed_writes" in props:
        reqs.append(
            KconfigReq(
                "CONFIG_BT_SIGNING", "y",
                "authenticated_signed_writes needs signing support; the app "
                "must also provision signing keys / bonded peer",
                mandatory=False))

    if "prepare_write" in perms:
        reqs.append(
            KconfigReq("CONFIG_BT_ATT_PREPARE_COUNT", "2",
                       "Buffers for the prepare-write queue used by "
                       "prepare_write permissions"))

    max_size = max(
        (chrc.size for svc in profile.services for chrc in svc.characteristics),
        default=1,
    )
    # ATT MTU is MIN(BT_L2CAP_RX_MTU, BT_L2CAP_TX_MTU); a single-PDU write
    # needs MTU >= size + 3 (ATT header), a read needs MTU >= size + 1.
    min_mtu = max_size + 4
    if min_mtu > 64:  # larger than the default (65 with SMP, 64 without)
        reqs.append(
            KconfigReq("CONFIG_BT_L2CAP_TX_MTU", str(min_mtu),
                       f"Single-PDU access to the largest characteristic "
                       f"({max_size} bytes); otherwise the stack truncates "
                       "reads and rejects oversized writes"))
        reqs.append(
            KconfigReq("CONFIG_BT_BUF_ACL_TX_SIZE", str(min_mtu + 4),
                       "ACL TX buffer must fit the L2CAP SDU + header",
                       mandatory=False))
        reqs.append(
            KconfigReq("CONFIG_BT_BUF_ACL_RX_SIZE", str(min_mtu + 4),
                       "ACL RX buffer must fit the L2CAP SDU + header",
                       mandatory=False))

    if profile.any_ccc():
        reqs.append(
            KconfigReq("CONFIG_BT_GATT_NOTIFY_MULTIPLE", "y",
                       "Optional: batch notifications when several CCCs are "
                       "enabled at once",
                       mandatory=False))

    return reqs


def requirements_markdown(profile: "Profile") -> str:
    """Render the requirements as the body of KCONFIG_NOTES.md."""
    lines = [
        f"# Kconfig notes for `{profile.name}`",
        "",
        "Minimum Zephyr configuration implied by the generated profile.",
        "`prj.conf` already sets the mandatory symbols; advisory rows explain",
        "settings you may need in a real application.",
        "",
        "| Symbol | Value | Why |",
        "| ------ | ----- | --- |",
    ]
    for req in required_kconfigs(profile):
        suffix = "" if req.mandatory else " *(advisory)*"
        lines.append(
            f"| `{req.symbol}` | `{req.value}` | {req.reason}{suffix} |")
    lines += [
        "",
        "Other symbols worth knowing:",
        "",
        "- `CONFIG_BT_GATT_SERVICE_CHANGED` (default `y`): keep enabled if the",
        "  attribute table can change across firmware versions so bonded peers",
        "  rediscover services.",
        "- `CONFIG_BT_SETTINGS` + `CONFIG_BT_SETTINGS_CCC_STORE_ON_WRITE`:",
        "  persist CCC subscription state and bonds across reboots.",
        "- `CONFIG_BT_MAX_CONN`: raise if the device must serve more than one",
        "  central at a time.",
        "",
    ]
    return "\n".join(lines)
