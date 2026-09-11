# Kconfig notes for `gatt_gen_secure`

Minimum Zephyr configuration implied by the generated profile.
`prj.conf` already sets the mandatory symbols; advisory rows explain
settings you may need in a real application.

| Symbol | Value | Why |
| ------ | ----- | --- |
| `CONFIG_BT` | `y` | Bluetooth host stack |
| `CONFIG_BT_DEVICE_NAME` | `"GATT Gen gatt_gen_secure"` | Name shown to scanning peers |
| `CONFIG_BT_PERIPHERAL` | `y` | Advertising / accepting connections (GATT server role) |
| `CONFIG_BT_SMP` | `y` | Encrypted/authenticated permissions need pairing (BT_SECURITY_L2) |

Other symbols worth knowing:

- `CONFIG_BT_GATT_SERVICE_CHANGED` (default `y`): keep enabled if the
  attribute table can change across firmware versions so bonded peers
  rediscover services.
- `CONFIG_BT_SETTINGS` + `CONFIG_BT_SETTINGS_CCC_STORE_ON_WRITE`:
  persist CCC subscription state and bonds across reboots.
- `CONFIG_BT_MAX_CONN`: raise if the device must serve more than one
  central at a time.
