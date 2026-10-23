# محسن — سایت‌ساز

مخزن: [github.com/mtma6991-arch/mohsen](https://github.com/mtma6991-arch/mohsen)

پنل جنگو برای ساخت و تحویل وب‌سایت مشتری. شما دسته تعریف می‌کنید (طلایی، نقره‌ای، …)، برای هر دسته قالبِ زیپ‌شده می‌گذارید، در مرکز افزونه بسته پایتون نصب می‌کنید و آن را به دسته اضافه می‌کنید. بعد برای هر مشتری یک دامنه و یک قالب از همان دسته ثبت می‌کنید. با باز شدن دامنه، همان سایت بالا می‌آید.

افزونه‌ای که به دسته اضافه شود روی **همه** سایت‌های آن دسته فعال است. نمونه همراه پروژه: پیامک برای دسته طلایی، صفحه‌ساز برای دسته نقره‌ای.

## امکانات پنل

- دسته با رنگ، نام، توضیح و فهرست افزونه
- قالب از فایل زیپ، با اعتبارسنجی ساختار و کامپایل Jinja2
- راهنمای کدنویسی زیپ قالب و زیپ افزونه داخل خود پنل
- مرکز افزونه و اتصال افزونه به دسته
- ثبت مشتری: دامنه، دسته، قالب، مشخصات تماس، محتوای JSON
- پیش‌نمایش مدیر قبل از وصل شدن DNS
- فرم تماس سایت، صندوق پیام، گزارش فعالیت
- مسیر پنل محرمانه است: `http://IP:PORT/<web-pass>/`

## نصب روی سرور

اوبونتو ۲۲.۰۴ / ۲۴.۰۴ یا دبیان ۱۲:

```bash
git clone https://github.com/mtma6991-arch/mohsen.git
cd mohsen
sudo bash install.sh
```

در پایان، آدرس دقیق پنل (قابل چسباندن در نوار مرورگر)، نام کاربری و رمز در ترمینال چاپ می‌شود و در `/root/mohsen-credentials.txt` هم ذخیره می‌گردد. آدرس ساختگی چاپ نمی‌شود.

وابستگی‌های پایتون داخل `vendor/wheels` همراه مخزن است تا نصب پکیج‌ها بدون PyPI هم ممکن باشد. بسته‌های سیستم (پایتون، nginx) را خود اسکریپت با apt می‌گیرد.

جزئیات، Postgres و به‌روزرسانی: [docs/installation.md](docs/installation.md)

## دستور mohsen

```bash
sudo mohsen
```

با اجرای همین دستور، آدرس واقعی ورود و نام کاربری و رمز نشان داده می‌شود. منو:

1. وضعیت سیستم
2. افزودن دامنه پنل (**add domain**)
3. نمایش دوباره اطلاعات ورود
4. تغییر رمز مدیر
5. تغییر web pass
6. راه‌اندازی مجدد
7. پشتیبان‌گیری
8. حذف دامنه پنل
9. به‌روزرسانی از گیت‌هاب
10. حذف کامل پروژه

دستورهای دقیق:

```bash
sudo mohsen update
sudo mohsen uninstall --yes
```

`update` از https://github.com/mtma6991-arch/mohsen شاخه `main` می‌گیرد و داده را پاک نمی‌کند. `uninstall --yes` کل نصب را برمی‌دارد.

`sudo Mohsen` هم همان دستور است. شرح گزینه‌ها: [docs/cli.md](docs/cli.md)

## توسعه محلی

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py bootstrap
python manage.py test
python manage.py runserver 0.0.0.0:8787
```

ورود توسعه: `admin` / `admin12345` روی `http://127.0.0.1:8787/panel/`

نمونه‌ها بعد از bootstrap:

| دامنه | دسته | قالب |
| --- | --- | --- |
| zarrin.local | طلایی | آتلیه جواهر + افزونه پیامک |
| hamrah.local | نقره‌ای | فروشگاه گوشی + صفحه‌ساز |

پیش‌نمایش بعد از ورود به پنل: `/_preview/zarrin.local/`

## ساخت قالب و افزونه

قالب‌ها باید بر اساس صفحه‌ساز معمار باشند: فایل `architect.json` و شناسه ۵۰ المان. مشتری بعداً همان قالب را در پنل با «ویرایش با معمار» عوض می‌کند.

- [docs/template-zip-guide.md](docs/template-zip-guide.md)
- [docs/plugin-development.md](docs/plugin-development.md)
- نمونه‌ها در `examples/templates` و `examples/plugins`
- معماری: [docs/architecture.md](docs/architecture.md)

## لایسنس

MIT. فایل [LICENSE](LICENSE).
