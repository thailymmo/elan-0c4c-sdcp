# ELAN 04f3:0c4c fingerprint reader on Linux (SDCP)

*[Tiếng Việt bên dưới](#tiếng-việt)*

Working Linux support for the **ELAN `04f3:0c4c` ("ELAN:ARM-M4") fingerprint
sensor with firmware 3.05**, found in laptops such as the **HP ENVY x360 15**
and **HP Spectre x360**. Stock libfprint lists this sensor as unsupported, and
the community `elanmoc2` driver enrolls but never matches on firmware 3.05,
because this firmware requires a Microsoft **SDCP** secure session.

This repository adds an `elansdcp` libfprint driver on top of libfprint's SDCP
framework, so `fprintd`, `sudo`, polkit dialogs, hyprlock and SDDM work with
the fingerprint reader. Matching happens on the sensor, and every match is
signed by the sensor and verified on the host.

## Status

Tested on an HP ENVY x360 15m-es1xxx (Arch Linux, sensor firmware 3.05):

| Feature | State |
|---|---|
| Enroll (`fprintd-enroll`) | works |
| Verify / identify (`fprintd-verify`, sudo, polkit, SDDM, hyprlock) | works |
| SDCP connect + Microsoft certificate chain validation | works |
| Wipe all templates on the sensor | works |
| Delete a single print / list prints on the sensor | **not supported** |

Check your sensor and firmware with `lsusb -d 04f3:0c4c -v | grep bcdDevice`
(firmware 3.05 shows `3.05`).

## Install (Arch Linux)

```sh
git clone https://github.com/thailymmo/elan-0c4c-sdcp
cd elan-0c4c-sdcp
bash install.sh
```

The script builds `libfprint-elansdcp-git` (replaces `libfprint`), restarts
`fprintd`, adds `pam_fprintd` to sudo, polkit and SDDM (with backups), installs
the overlay and enrolls your right index finger. To only build the library, use
`arch/PKGBUILD` (`makepkg -si`).

Other distributions: apply `patches/*.patch` to libfprint's
[`feature/sdcp-v2`](https://gitlab.freedesktop.org/libfprint/libfprint/-/tree/feature/sdcp-v2)
branch (commit `2d7c5277`).

## Extras

- `overlay/fp-overlay.py`: an on-screen fingerprint prompt (GTK3 + layer shell)
  for Hyprland and other wlroots compositors. It listens to fprintd's D-Bus
  signals and shows a card while sudo or a polkit dialog waits for your finger.
- `sddm/`: a fingerprint indicator for SDDM themes based on sddm-astronaut.
  Leave the password empty, press Enter, then touch the sensor.
  `scripts/sddm-pam-order.sh` makes SDDM check a typed password first.

## Uninstall

```sh
sudo bash scripts/setup-pam.sh --undo
sudo pacman -S libfprint   # back to the stock library
```

## Warnings

- **The sensor's template storage (about 10 slots) is shared by every OS on the
  machine, including Windows Hello.** Wiping the sensor (`fprintd-delete`,
  "clear storage") removes prints enrolled by other systems.
- The Windows driver may delete prints it does not know about when you enroll
  in Windows Hello. Re-run `fprintd-enroll` if Linux stops recognizing you.
- This depends on libfprint's SDCP branch, which is not merged upstream yet.

## How it works

See [`docs/PROTOCOL.md`](docs/PROTOCOL.md) for the command set. Short version:
the host and sensor run an SDCP connect (ECDH P-256 + KBKDF), enrollment is
committed with `HMAC(s, "enroll", nonce)`, and every match returns the
enrollment ID plus `HMAC(s, "identify", nonce, id)`.

## Credits

- Joshua Grisham and the libfprint maintainers: SDCP framework (`feature/sdcp-v2`).
- Davide Depau: the `elanmoc2` driver, which documented the ELAN MoC command set.
- Benjamin Berg: original SDCP work in libfprint.

## License

- `patches/`, `arch/`: LGPL-2.1-or-later (same as libfprint).
- `sddm/`: GPL-3.0-or-later (derived from sddm-astronaut-theme).
- Everything else: MIT, see `LICENSE`.

---

## Tiếng Việt

Hỗ trợ **cảm biến vân tay ELAN `04f3:0c4c` (firmware 3.05)** trên Linux, có trên
các máy **HP ENVY x360 15**, **HP Spectre x360**… libfprint gốc chưa hỗ trợ cảm
biến này. Driver cộng đồng `elanmoc2` đăng ký được nhưng không bao giờ nhận
diện được, vì firmware 3.05 bắt buộc dùng kênh bảo mật **SDCP** của Microsoft.

Repo này thêm driver `elansdcp` cho libfprint, dùng bộ khung SDCP có sẵn của
libfprint. Sau khi cài, vân tay dùng được cho `sudo`, hộp thoại polkit,
hyprlock và SDDM. Việc so khớp diễn ra trên chip, mỗi lần khớp đều có chữ ký
của chip và được máy tính kiểm tra.

### Cài đặt (Arch Linux)

```sh
git clone https://github.com/thailymmo/elan-0c4c-sdcp
cd elan-0c4c-sdcp
bash install.sh
```

Script sẽ biên dịch và cài `libfprint-elansdcp-git` (thay cho `libfprint`),
bật vân tay cho sudo, polkit và SDDM (có sao lưu), cài lớp phủ vân tay và đăng
ký ngón trỏ phải.

### Lưu ý

- **Bộ nhớ chip (khoảng 10 vân tay) dùng chung cho mọi hệ điều hành trên máy,
  kể cả Windows Hello.** Xóa toàn bộ bộ nhớ chip sẽ xóa luôn vân tay của các
  hệ khác.
- Chưa hỗ trợ xóa hoặc liệt kê từng vân tay trên chip.
- Gỡ cài đặt: `sudo bash scripts/setup-pam.sh --undo` rồi `sudo pacman -S libfprint`.
