# نصب روی سرور

مخزن: https://github.com/mtma6991-arch/mohsen

سیستم هدف: اوبونتو ۲۲.۰۴ یا ۲۴.۰۴ و دبیان ۱۲، با دسترسی root.

## نصب

```bash
git clone https://github.com/mtma6991-arch/mohsen.git
cd mohsen
sudo bash install.sh
```

اسکریپت این‌ها را انجام می‌دهد:

1. نصب `python3`, `python3-venv`, `nginx`, `curl`, `rsync` و ابزار ساخت.
2. کپی پروژه در `/opt/mohsen`.
3. ساخت محیط مجازی. اگر پوشه `vendor/wheels` پر باشد، نصب پکیج‌ها آفلاین است.
4. تولید کلید جنگو، مسیر محرمانه پنل (web pass) و رمز مدیر. در نصب مجدد، رمز قبلی حفظ می‌شود.
5. مهاجرت پایگاه SQLite در `/var/lib/mohsen` (یا Postgres با `--postgres`).
6. بارگذاری دسته‌های طلایی و نقره‌ای، قالب‌های نمونه و افزونه‌های نمونه.
7. سرویس systemd به نام `mohsen` و nginx روی پورت ۸۰ و ۸۷۸۷.
8. نصب دستورهای `mohsen` و `Mohsen`.
9. چاپ آدرس پنل، نام کاربری و رمز در ترمینال و ذخیره در `/root/mohsen-credentials.txt`.

## بعد از نصب

```bash
sudo mohsen
```

گزینه `2` یعنی افزودن دامنه پنل (add domain). بعد از ثبت دامنه و اشاره رکورد A به سرور، هر دو آدرس کار می‌کنند:

- `http://IP:8787/<web-pass>/`
- `http://DOMAIN/<web-pass>/`

سایت‌های مشتری هم با همین nginx و بر اساس هدر Host سرو می‌شوند. برای هر مشتری در پنل دامنه بسازید و DNS را به سرور بدهید.

## Postgres

```bash
sudo bash install.sh --postgres
```

کاربر و پایگاه `mohsen` ساخته می‌شود. بسته `psycopg` باید جدا نصب شود اگر در wheels نباشد:

```bash
sudo /opt/mohsen/.venv/bin/pip install "psycopg[binary]"
```

و `DATABASE_URL` را در `/etc/mohsen/mohsen.env` بگذارید و سرویس را مجدد راه بیندازید.

## توسعه روی رایانه خودتان

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py bootstrap
python manage.py runserver 0.0.0.0:8787
```

پنل توسعه: `http://127.0.0.1:8787/panel/` با کاربر `admin` و رمز `admin12345`.

## به‌روزرسانی

کد تازه را در پوشه کلون بریزید و دوباره `sudo bash install.sh` را اجرا کنید. پایگاه و رسانه و رمز پاک نمی‌شوند.

## حذف

```bash
sudo bash uninstall.sh
```
