#!/usr/bin/env bash
# به‌روزرسانی محسن از مخزن گیت‌هاب، بدون پاک کردن پایگاه، رسانه و رمز.
#   sudo mohsen update
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "به‌روزرسانی را با root اجرا کنید: sudo mohsen update"
  exit 1
fi

if [[ "${BASH_SOURCE[0]}" != /tmp/mohsen-update.sh ]]; then
  cp "$BASH_SOURCE" /tmp/mohsen-update.sh
  exec bash /tmp/mohsen-update.sh "$@"
fi

REPO_URL="${MOHSEN_GIT_URL:-https://github.com/mtma6991-arch/mohsen.git}"
BRANCH="${MOHSEN_GIT_BRANCH:-main}"
ZIP_URL="${MOHSEN_GIT_ZIP:-https://github.com/mtma6991-arch/mohsen/archive/refs/heads/${BRANCH}.zip}"
TMP="$(mktemp -d /tmp/mohsen-src.XXXXXX)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

echo "به‌روزرسانی محسن از مخزن:"
echo "  ${REPO_URL}"
echo "  شاخه ${BRANCH}"
echo "پایگاه، رسانه و فایل /etc/mohsen/mohsen.env پاک نمی‌شود."

SRC=""
if ! command -v git >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y git ca-certificates curl unzip
fi
if git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP/src"; then
  SRC="$TMP/src"
fi
if [[ ! -f "${SRC}/install.sh" ]]; then
  echo "clone ناموفق بود. دریافت زیپ شاخه ${BRANCH} ..."
  curl -fsSL --retry 3 -o "$TMP/src.zip" "$ZIP_URL"
  rm -rf "$TMP/unzip"
  mkdir -p "$TMP/unzip"
  unzip -q "$TMP/src.zip" -d "$TMP/unzip"
  SRC="$(find "$TMP/unzip" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
fi
if [[ ! -f "${SRC}/install.sh" ]]; then
  echo "به‌روزرسانی ناموفق بود. مخزن در دسترس نیست یا install.sh داخل آن نیست."
  exit 1
fi

bash "$SRC/install.sh"
echo
echo "به‌روزرسانی از گیت‌هاب تمام شد."
echo "برای دیدن آدرس دقیق ورود: sudo mohsen"
