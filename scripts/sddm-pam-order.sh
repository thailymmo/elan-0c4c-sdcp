#!/bin/bash
# SDDM: check a typed password first, use the fingerprint only when the
# password field is left empty. Undo: sudo bash sddm-pam-order.sh --undo
set -euo pipefail
F=/etc/pam.d/sddm
[[ $EUID -eq 0 ]] || { echo "Can chay voi sudo" >&2; exit 1; }

if [[ ${1:-} == --undo ]]; then
  cp -a "$F.bak-order" "$F" && echo "Da khoi phuc $F"
  exit 0
fi

cp -a "$F" "$F.bak-order"
# Drop the line added by setup-pam.sh, then insert the new order after the header
sed -i '/pam_fprintd.so/d' "$F"
sed -i '1a auth       required     pam_faillock.so preauth\
auth       [success=done default=ignore] pam_unix.so try_first_pass\
auth       sufficient   pam_fprintd.so max-tries=1 timeout=10' "$F"
echo "Da cap nhat $F:"
grep -n '^auth' "$F"
