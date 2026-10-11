# Host Network Recovery — WiFi Interface Down

## Recovery Procedure

When `nmcli device status` shows `wlan0` in `disconnected` / `DOWN` with no IP:
1. `ip link set wlan0 up`
2. `nmcli device wifi list` — confirm AP is visible
3. `nmcli connection show <ssid>` — if `connection.interface-name:` isn't `wlan0` (or `*`), modify it
4. Remove any stale NM "cloned" connections created during earlier failed attempts (e.g., `"MyNet 1"` from trying to connect without secrets)
5. `nmcli connection up <ssid>`

## Root Cause Pattern

On this laptop, dmesg shows `iwlwifi ... renamed from wlan0` at boot, but NM profiles may retain the old interface name. NETWORKMANAGER ASSIGNS the interface name as part of profile binding, so `nmcli connection up` fails with *No suitable device found* until you either set `connection.interface-name` to the actual interface name or `*`.

## Caveats
- The WPA-PSK secret is stored in the saved connection profile; you do not need to re-enter it.
- Failed `device wifi connect <ssid>` attempts without the stored secret produce *Secrets were required, but not provided* and leave junk "name 1" profiles behind. Delete them before retrying.
