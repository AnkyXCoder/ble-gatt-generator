# Kconfig notes for `gatt_gen_full`

Minimum Zephyr configuration implied by the generated profile.
`prj.conf` already sets the mandatory symbols; advisory rows explain
settings you may need in a real application.

| Symbol | Value | Why |
| ------ | ----- | --- |
| `CONFIG_BT` | `y` | Bluetooth host stack |
| `CONFIG_BT_DEVICE_NAME` | `"GATT Gen gatt_gen_full"` | Name shown to scanning peers |
| `CONFIG_BT_PERIPHERAL` | `y` | Advertising / accepting connections (GATT server role) |
| `CONFIG_BT_SMP` | `y` | Encrypted/authenticated permissions need pairing (BT_SECURITY_L4) |
| `CONFIG_BT_FIXED_PASSKEY` | `y` | Used by the generated BabbleSim test only — do NOT enable in production; a real device needs MITM-capable IO (display/keyboard) or OOB instead *(advisory)* |
| `CONFIG_BT_SMP_SC_ONLY` | `y` | read_lesc/write_lesc permissions need LE Secure Connections pairing *(advisory)* |
| `CONFIG_BT_SIGNING` | `y` | authenticated_signed_writes needs signing support; the app must also provision signing keys / bonded peer *(advisory)* |
| `CONFIG_BT_ATT_PREPARE_COUNT` | `2` | Buffers for the prepare-write queue used by prepare_write permissions |
| `CONFIG_BT_L2CAP_TX_MTU` | `68` | Single-PDU access to the largest characteristic (64 bytes); otherwise the stack truncates reads and rejects oversized writes |
| `CONFIG_BT_BUF_ACL_TX_SIZE` | `72` | ACL TX buffer must fit the L2CAP SDU + header *(advisory)* |
| `CONFIG_BT_BUF_ACL_RX_SIZE` | `72` | ACL RX buffer must fit the L2CAP SDU + header *(advisory)* |
| `CONFIG_BT_GATT_NOTIFY_MULTIPLE` | `y` | Optional: batch notifications when several CCCs are enabled at once *(advisory)* |

Other symbols worth knowing:

- `CONFIG_BT_GATT_SERVICE_CHANGED` (default `y`): keep enabled if the
  attribute table can change across firmware versions so bonded peers
  rediscover services.
- `CONFIG_BT_SETTINGS` + `CONFIG_BT_SETTINGS_CCC_STORE_ON_WRITE`:
  persist CCC subscription state and bonds across reboots.
- `CONFIG_BT_MAX_CONN`: raise if the device must serve more than one
  central at a time.
