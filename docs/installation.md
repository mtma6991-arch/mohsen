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

1. نصب `python3`, `python3-venv`, `nginx`, `curl`, `openssl`, `socat` و ابزار ساخت.
2. کپی پروژه در `/opt/mohsen`.
3. ساخت محیط مجازی. اگر پوشه `vendor/wheels` پر باشد، نصب پکیج‌ها آفلاین است.
4. تولید کلید جنگو، مسیر محرمانه پنل (web pass) و رمز مدیر. در نصب مجدد، رمز قبلی حفظ می‌شود.
5. مهاجرت پایگاه SQLite در `/var/lib/mohsen` (یا Postgres با `--postgres`).
6. بارگذاری دسته‌های طلایی و نقره‌ای، قالب‌های نمونه و افزونه‌های نمونه.
7. سرویس systemd به نام `mohsen`، سوکت صدور `mohsen-tlsd`، تایمر `mohsen-tls.timer` و nginx روی پورت ۸۰، ۴۴۳ و ۸۷۸۷.
8. نصب `acme.sh` در `/root/.acme.sh` برای Let’s Encrypt.
9. نصب دستورهای `mohsen` و `Mohsen`.
10. چاپ آدرس پنل، نام کاربری و رمز در ترمینال و ذخیره در `/root/mohsen-credentials.txt`.

پورت‌های ۸۰ و ۴۴۳ باید از اینترنت به این سرور برسند. وگرنه صدور گواهی خطا می‌دهد و سایت‌ها روی HTTP می‌مانند.

## بعد از نصب

```bash
sudo mohsen
```

گزینه `2` یا صفحه «گواهی TLS» داخل پنل، دامنه پنل را ثبت می‌کند. بعد از رکورد A:

- `http://IP:8787/<web-pass>/` برای ورود اضطراری
- `https://DOMAIN/<web-pass>/` وقتی گواهی پنل فعال شد

سایت مشتری را در پنل بسازید. اگر وضعیتش فعال باشد و DNS به سرور اشاره کند، گواهی همان دامنه هم خودکار صادر می‌شود. توضیح کامل در [tls.md](tls.md).

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

پنل توسعه: `http://127.0.0.1:8787/panel/` با کاربر `admin` و رمز `admin12345`. صدور TLS در توسعه محلی اجرا نمی‌شود، چون به root، nginx و DNS عمومی نیاز دارد.

## به‌روزرسانی از گیت‌هاب

```bash
sudo mohsen update
```

این دستور شاخه `main` را از https://github.com/mtma6991-arch/mohsen می‌گیرد و دوباره `install.sh` را اجرا می‌کند. پایگاه، رسانه، رمز و کلیدهای اضافی فایل محیط پاک نمی‌شوند. آدرس ورود بعد از آن با `sudo mohsen` چاپ می‌شود.

اگر کد را دستی در یک کلون دارید، همان کلون را به‌روز کنید و `sudo bash install.sh` را اجرا کنید. این حالت هم داده را پاک نمی‌کند.

## حذف کامل

```bash
sudo mohsen uninstall --yes
```

سرویس، تایمر TLS، سایت nginx محسن، دستور `mohsen`، کد، پایگاه، رسانه، تنظیمات، گواهی‌ها، acme.sh، پشتیبان و فایل رمز پاک می‌شود. برای نصب دوباره مخزن را از نو کلون کنید.
