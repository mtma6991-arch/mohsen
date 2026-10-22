#!/usr/bin/env bash
# نصب کامل سایت‌ساز محسن روی اوبونتو/دبیان.
#   sudo bash install.sh
#   sudo bash install.sh --postgres
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "نصب را با root اجرا کنید: sudo bash install.sh"
  exit 1
fi

USE_POSTGRES=0
if [[ "${1:-}" == "--postgres" ]]; then
  USE_POSTGRES=1
fi

if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
else
  ID=""
fi
case "${ID:-}" in
  ubuntu|debian) ;;
  *)
    echo "این اسکریپت برای اوبونتو و دبیان نوشته شده است. شناسه سیستم: ${ID:-unknown}"
    exit 1
    ;;
esac

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP=/opt/mohsen
ENV_DIR=/etc/mohsen
ENV_FILE="${ENV_DIR}/mohsen.env"
DATA_DIR=/var/lib/mohsen
CRED=/root/mohsen-credentials.txt

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-venv python3-pip python3-dev build-essential nginx curl ca-certificates rsync

PY=python3
if ! "$PY" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "پایتون ۳.۱۰ یا جدیدتر لازم است."
  exit 1
fi

if ! id mohsen >/dev/null 2>&1; then
  useradd --system --home "$APP" --shell /usr/sbin/nologin mohsen
fi

mkdir -p "$APP" "$ENV_DIR" "$DATA_DIR/media" /var/log/mohsen /var/backups/mohsen
rsync -a --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude 'media' \
  --exclude 'data' \
  --exclude 'staticfiles' \
  --exclude 'mohsen.env' \
  --exclude '__pycache__' \
  "$SRC"/ "$APP"/

if [[ ! -f "$ENV_FILE" ]]; then
  SECRET="$("$PY" -c 'import secrets; print(secrets.token_urlsafe(48))')"
  WEB_PASS="$("$PY" -c 'import secrets; print(secrets.token_urlsafe(9))')"
  ADMIN_PASS="$("$PY" -c 'import secrets; print(secrets.token_urlsafe(12))')"
  FIRST_INSTALL=1
else
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  SECRET="${MOHSEN_SECRET_KEY}"
  WEB_PASS="${MOHSEN_WEB_PASS}"
  ADMIN_PASS=""
  FIRST_INSTALL=0
fi

DB_URL_LINE=""
if [[ "$USE_POSTGRES" -eq 1 ]]; then
  apt-get install -y postgresql postgresql-contrib libpq-dev
  PG_PASS="${MOHSEN_PG_PASS:-$("$PY" -c 'import secrets; print(secrets.token_urlsafe(18))')}"
  sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='mohsen'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER mohsen WITH PASSWORD '${PG_PASS}'"
  sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='mohsen'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE mohsen OWNER mohsen"
  DB_URL_LINE="DATABASE_URL=postgresql://mohsen:${PG_PASS}@127.0.0.1:5432/mohsen"
fi

cat > "$ENV_FILE" <<EOF
MOHSEN_SECRET_KEY=${SECRET}
MOHSEN_WEB_PASS=${WEB_PASS}
MOHSEN_PORT=8787
MOHSEN_ADMIN_USER=${MOHSEN_ADMIN_USER:-admin}
MOHSEN_DEBUG=0
MOHSEN_HTTPS=0
MOHSEN_DATA_DIR=${DATA_DIR}
MOHSEN_MEDIA_ROOT=${DATA_DIR}/media
MOHSEN_STATIC_ROOT=${APP}/staticfiles
DJANGO_SETTINGS_MODULE=config.settings.prod
${DB_URL_LINE}
EOF
chown root:mohsen "$ENV_FILE"
chmod 640 "$ENV_FILE"
cp "$ENV_FILE" "$APP/mohsen.env"
chown root:mohsen "$APP/mohsen.env"
chmod 640 "$APP/mohsen.env"

if [[ ! -d "$APP/.venv" ]]; then
  "$PY" -m venv "$APP/.venv"
fi
if compgen -G "$APP/vendor/wheels/*.whl" > /dev/null; then
  "$APP/.venv/bin/pip" install --no-index --find-links="$APP/vendor/wheels" -r "$APP/requirements.txt"
else
  "$APP/.venv/bin/pip" install --upgrade pip
  "$APP/.venv/bin/pip" install -r "$APP/requirements.txt"
fi
if [[ "$USE_POSTGRES" -eq 1 ]]; then
  "$APP/.venv/bin/pip" install -r "$APP/requirements-postgres.txt" || true
fi

chown -R mohsen:mohsen "$APP" "$DATA_DIR" /var/log/mohsen
chmod 750 "$DATA_DIR"

run_manage() {
  sudo -u mohsen bash -lc "set -a; source '$ENV_FILE'; set +a; cd '$APP'; exec .venv/bin/python manage.py $*"
}

if [[ "$FIRST_INSTALL" -eq 1 ]]; then
  grep -q '^MOHSEN_ADMIN_PASSWORD=' "$ENV_FILE" || echo "MOHSEN_ADMIN_PASSWORD=${ADMIN_PASS}" >> "$ENV_FILE"
  echo "MOHSEN_ADMIN_RESET=1" >> "$ENV_FILE"
fi

run_manage migrate --noinput
run_manage bootstrap
if [[ "$FIRST_INSTALL" -eq 1 ]]; then
  run_manage ensure_admin
  # رمز را بعد از ساخت کاربر از فایل محیط برمی‌داریم تا در سرویس روزمره نماند.
  sed -i '/^MOHSEN_ADMIN_PASSWORD=/d;/^MOHSEN_ADMIN_RESET=/d' "$ENV_FILE"
  cp "$ENV_FILE" "$APP/mohsen.env"
  chown root:mohsen "$ENV_FILE" "$APP/mohsen.env"
  chmod 640 "$ENV_FILE" "$APP/mohsen.env"
fi
run_manage collectstatic --noinput

install -m 0755 "$APP/bin/mohsen" /usr/local/bin/mohsen
ln -sfn /usr/local/bin/mohsen /usr/local/bin/Mohsen

install -m 0644 "$APP/deploy/systemd/mohsen.service" /etc/systemd/system/mohsen.service
systemctl daemon-reload
systemctl enable mohsen
systemctl restart mohsen

install -m 0644 "$APP/deploy/nginx/mohsen.conf" /etc/nginx/sites-available/mohsen.conf
ln -sfn /etc/nginx/sites-available/mohsen.conf /etc/nginx/sites-enabled/mohsen.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
systemctl reload nginx

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
if [[ -z "${IP}" ]]; then
  IP="SERVER_IP"
fi
ADMIN_USER="${MOHSEN_ADMIN_USER:-admin}"

if [[ "$FIRST_INSTALL" -eq 1 ]]; then
  cat > "$CRED" <<EOF
محسن — مشخصات نصب
آدرس پنل با آی‌پی و پورت: http://${IP}:8787/${WEB_PASS}/
آدرس پنل روی پورت ۸۰:     http://${IP}/${WEB_PASS}/
نام کاربری: ${ADMIN_USER}
رمز عبور: ${ADMIN_PASS}
دستور مدیریت: sudo mohsen
افزودن دامنه پنل: داخل دستور mohsen گزینه add domain
EOF
  chmod 600 "$CRED"
  echo
  echo "============================================================"
  echo "  محسن — سایت‌ساز نصب شد"
  echo "============================================================"
  echo "  آدرس پنل با آی‌پی:"
  echo "    http://${IP}:8787/${WEB_PASS}/"
  echo "  آدرس پنل روی پورت ۸۰:"
  echo "    http://${IP}/${WEB_PASS}/"
  echo "  نام کاربری: ${ADMIN_USER}"
  echo "  رمز عبور:   ${ADMIN_PASS}"
  echo
  echo "  دستور مدیریت (منو، شامل add domain):"
  echo "    sudo mohsen"
  echo
  echo "  رونوشت محرمانه:"
  echo "    ${CRED}"
  echo "============================================================"
else
  echo
  echo "به‌روزرسانی انجام شد. رمز مدیر عوض نشده است."
  echo "پنل: http://${IP}:8787/${WEB_PASS}/"
  echo "دستور مدیریت: sudo mohsen"
fi
