#!/usr/bin/env bash
# حذف کامل سایت‌ساز محسن.
#   sudo mohsen uninstall
#   sudo mohsen uninstall --yes
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "حذف را با root اجرا کنید: sudo mohsen uninstall --yes"
  exit 1
fi

if [[ "${BASH_SOURCE[0]}" != /tmp/mohsen-uninstall.sh ]]; then
  cp "$BASH_SOURCE" /tmp/mohsen-uninstall.sh
  chmod 700 /tmp/mohsen-uninstall.sh
  exec bash /tmp/mohsen-uninstall.sh "$@"
fi

YES=0
for arg in "$@"; do
  if [[ "$arg" == "--yes" || "$arg" == "-y" ]]; then
    YES=1
  fi
done

if [[ "$YES" -ne 1 ]]; then
  echo "حذف کامل محسن این‌ها را پاک می‌کند:"
  echo "  سرویس systemd، پیکربندی nginx همین برنامه، دستور mohsen"
  echo "  کد /opt/mohsen"
  echo "  داده و رسانه /var/lib/mohsen"
  echo "  گواهی‌ها /etc/mohsen/ssl و کلاینت /root/.acme.sh و وب‌روت /var/lib/mohsen-acme"
  echo "  تنظیم /etc/mohsen"
  echo "  لاگ /var/log/mohsen و پشتیبان /var/backups/mohsen"
  echo "  فایل رمز /root/mohsen-credentials.txt"
  echo "  کاربر سیستمی mohsen"
  echo "nginx خود سیستم پاک نمی‌شود."
  echo "برای تأیید دقیقاً بنویسید: uninstall"
  read -r answer
  if [[ "$answer" != "uninstall" ]]; then
    echo "لغو شد."
    exit 1
  fi
fi

systemctl disable --now mohsen-tls.timer mohsen-tlsd mohsen >/dev/null 2>&1 || true
rm -f /etc/systemd/system/mohsen.service \
  /etc/systemd/system/mohsen-tlsd.service \
  /etc/systemd/system/mohsen-tls.service \
  /etc/systemd/system/mohsen-tls.timer
systemctl daemon-reload || true
rm -rf /root/.acme.sh /var/lib/mohsen-acme
rm -f /run/mohsen/tls.sock

rm -f /etc/nginx/sites-enabled/mohsen.conf /etc/nginx/sites-available/mohsen.conf
if command -v nginx >/dev/null 2>&1; then
  nginx -t >/dev/null 2>&1 && systemctl reload nginx >/dev/null 2>&1 || true
fi

rm -f /usr/local/bin/mohsen /usr/local/bin/Mohsen

if id mohsen >/dev/null 2>&1; then
  userdel mohsen >/dev/null 2>&1 || true
fi

rm -rf /opt/mohsen /var/lib/mohsen /etc/mohsen /var/log/mohsen /var/backups/mohsen
rm -f /root/mohsen-credentials.txt

echo "محسن کاملاً حذف شد."
echo "برای نصب دوباره: git clone https://github.com/mtma6991-arch/mohsen.git && cd mohsen && sudo bash install.sh"
rm -f /tmp/mohsen-uninstall.sh
