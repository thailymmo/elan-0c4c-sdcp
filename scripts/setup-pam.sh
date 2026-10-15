#!/bin/bash
# Enable fingerprint (pam_fprintd) for sudo, polkit dialogs and SDDM.
# Every file is backed up to /etc/pam.d/*.bak-fprint first.
# Undo: sudo bash scripts/setup-pam.sh --undo
set -euo pipefail

LINE_SUDO='auth       sufficient   pam_fprintd.so max-tries=2 timeout=20'
LINE_POLKIT='auth       sufficient   pam_fprintd.so max-tries=2 timeout=30'
LINE_SDDM='auth       sufficient   pam_fprintd.so max-tries=1 timeout=10'

if [[ $EUID -ne 0 ]]; then
  echo "Can chay voi sudo" >&2
  exit 1
fi

if [[ ${1:-} == --undo ]]; then
  for f in sudo sddm polkit-1; do
    if [[ -e /etc/pam.d/$f.bak-fprint ]]; then
      mv /etc/pam.d/$f.bak-fprint /etc/pam.d/$f
      echo "Da khoi phuc /etc/pam.d/$f"
    elif [[ $f == polkit-1 && -e /etc/pam.d/polkit-1.created-fprint ]]; then
      rm -f /etc/pam.d/polkit-1 /etc/pam.d/polkit-1.created-fprint
      echo "Da xoa /etc/pam.d/polkit-1 (dung lai ban mac dinh)"
    fi
  done
  exit 0
fi

add_line() {
  local file=$1 line=$2
  if grep -q pam_fprintd "$file"; then
    echo "$file da co pam_fprintd, bo qua"
    return
  fi
  cp -a "$file" "$file.bak-fprint"
  # Insert right after the #%PAM-1.0 header (or at the top if there is none)
  if head -1 "$file" | grep -q '^#%PAM'; then
    sed -i "1a $line" "$file"
  else
    sed -i "1i $line" "$file"
  fi
  echo "Da them van tay vao $file"
}

add_line /etc/pam.d/sudo "$LINE_SUDO"
add_line /etc/pam.d/sddm "$LINE_SDDM"

if [[ ! -e /etc/pam.d/polkit-1 ]]; then
  cp /usr/lib/pam.d/polkit-1 /etc/pam.d/polkit-1
  touch /etc/pam.d/polkit-1.created-fprint
fi
add_line /etc/pam.d/polkit-1 "$LINE_POLKIT"

echo
echo "Xong. Mo terminal moi va thu: sudo -k; sudo true"
