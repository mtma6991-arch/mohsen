#!/usr/bin/env bash
set -euo pipefail
if [[ "${EUID}" -ne 0 ]]; then
  echo "sudo bash uninstall.sh"
  exit 1
fi
systemctl disable --now mohsen || true
rm -f /etc/systemd/system/mohsen.service
systemctl daemon-reload || true
rm -f /etc/nginx/sites-enabled/mohsen.conf /etc/nginx/sites-available/mohsen.conf
systemctl reload nginx || true
rm -f /usr/local/bin/mohsen /usr/local/bin/Mohsen
echo "سرویس و دستور حذف شد. کد در /opt/mohsen و داده در /var/lib/mohsen باقی مانده است."
echo "برای پاک کردن کامل: rm -rf /opt/mohsen /var/lib/mohsen /etc/mohsen"
