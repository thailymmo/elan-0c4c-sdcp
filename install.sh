#!/bin/bash
# Arch Linux installer for the ELAN 04f3:0c4c (SDCP) fingerprint sensor.
# Run as your normal user:  bash install.sh
# 1. build + install patched libfprint   2. restart fprintd
# 3. enable pam_fprintd for sudo, polkit, SDDM   4. fingerprint overlay
# 5. enroll your right index finger
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

if [[ $EUID -eq 0 ]]; then
  echo "Run as a normal user; the script calls sudo when needed." >&2
  exit 1
fi

if ! lsusb 2>/dev/null | grep -qi '04f3:0c4c' && ! grep -qsi '0c4c' /sys/bus/usb/devices/*/idProduct; then
  echo "ELAN 04f3:0c4c sensor not found - this setup is only for that sensor." >&2
  exit 1
fi

echo "==> 1/5 Building libfprint with the elansdcp driver"
sudo pacman -S --needed --noconfirm base-devel git meson gobject-introspection \
  fprintd python-gobject gtk3 gtk-layer-shell
BUILD=$(mktemp -d)
cp -L "$HERE"/arch/* "$BUILD"/
(cd "$BUILD" && makepkg -si --noconfirm)

echo "==> 2/5 Restarting fprintd"
sudo systemctl restart fprintd

echo "==> 3/5 Enabling fingerprint for sudo, polkit and SDDM"
sudo bash "$HERE/scripts/setup-pam.sh"

echo "==> 4/5 Installing the fingerprint overlay"
install -Dm755 "$HERE/overlay/fp-overlay.py" "$HOME/.local/bin/fp-overlay"
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/fp-overlay.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Fingerprint overlay
Exec=$HOME/.local/bin/fp-overlay
EOF
if [[ -f "$HOME/.config/hypr/hyprland.conf" ]] && ! grep -rqs 'fp-overlay' "$HOME/.config/hypr"; then
  echo "exec-once = $HOME/.local/bin/fp-overlay" >> "$HOME/.config/hypr/hyprland.conf"
fi
pgrep -f "$HOME/.local/bin/fp-overlay" >/dev/null || (nohup "$HOME/.local/bin/fp-overlay" >/dev/null 2>&1 &)

echo "==> 5/5 Enrolling your right index finger (touch the sensor ~8 times)"
fprintd-enroll -f right-index-finger

echo
echo "Done. Try: sudo -k; sudo true"
