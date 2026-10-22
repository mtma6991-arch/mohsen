# راهنمای زیپ قالب

قالب‌های محسن فایل زیپ هستند و در پنل، بخش «قالب‌ها»، برای یک دسته بارگذاری می‌شوند. همان راهنما داخل پنل در مسیر «راهنمای زیپ قالب» هم هست. این سند نسخه مخزن است.

## ساختار

```
template.json
layout/base.html
pages/home.html
pages/about.html
pages/contact.html
assets/style.css
assets/fonts/
```

اگر یک پوشه والد تنها وجود داشته باشد و `template.json` داخل آن باشد، پذیرفته می‌شود.

## فیلدهای template.json

| فیلد | الزام | توضیح |
| --- | --- | --- |
| name | بله | نام نمایشی |
| slug | بله | یکتا، `[a-z0-9-]+` |
| version | خیر | پیش‌فرض `1.0.0` |
| author | خیر | |
| description | خیر | |
| homepage | خیر | slug صفحه اول اگر حذف شود |
| pages | بله | آرایه `{slug,title,file,in_menu}` |
| demo_data | خیر | شیء JSON داده نمونه |

## بافت Jinja2

موتور، محیط سندباکس با autoescape است.

- `site` مشخصات مشتری: title, tagline, description, phone, email, address, logo_text, domain, accent_color, category, category_slug
- `page` و `pages`
- `data` حاصل ادغام `demo_data` با JSON اختصاصی سایت
- `plugins.<slug>` خروجی افزونه‌های فعال همان دسته
- `asset(path)` ، `page_url(slug)` ، `form_action(name)` ، `csrf_token` ، `sent`

## فرم تماس

`POST` به `form_action('contact')` با فیلدهای `name`، `phone`، `email`، `message` و `csrfmiddlewaretoken`. فیلد مخفی `company_website` هانی‌پات است.

## محدودیت‌ها

پسوندهای مجاز: html, css, js, json, svg, png, jpg, jpeg, webp, gif, ico, woff, woff2, txt, md, map, webmanifest. فایل پایتون، مسیر `..`، سیم‌لینک و زیپ خراب رد می‌شود. سقف تقریبی ۸۰ مگابایت فشرده و ۲۰۰ مگابایت باز شده.

نمونه‌ها: `examples/templates/jewelry-atelier` و `examples/templates/silver-phones`.
