# راهنمای افزونه

افزونه‌ها در «مرکز افزونه» با زیپ نصب می‌شوند و سپس به دسته‌ها اضافه می‌شوند. هر وب‌سایت، افزونه‌های دسته خودش را دارد.

## ساختار

```
plugin.json
plugin.py
```

`plugin.json`: `name`, `slug`, `version`, `author`, `description`, `entry` (پیش‌فرض `plugin.py`), `class` (پیش‌فرض `Plugin`), `hooks`.

کلاس باید از `mohsen_sdk.BasePlugin` ارث ببرد.

## قلاب‌ها

- `site_context(website, request)` مقدار `plugins.<slug>` در قالب
- `head_html(website, request)`
- `on_form_submit(website, form_name, data)`
- `admin_panel` / `handle_admin_post` برای ویرایش هر سایت
- `category_admin_panel` / `handle_category_post` برای تنظیم پیش‌فرض دسته

ذخیره: `plugin_get`, `plugin_set`, `merged_plugin_settings`, `category_plugin_settings`.

افزونه با سطح دسترسی سرویس اجرا می‌شود. فقط کد امضاشده خودتان را نصب کنید.

نمونه‌ها: `examples/plugins/sms` (کاوه‌نگار یا گزارش) و `examples/plugins/page-builder`.

نصب نمونه در `bootstrap`: پیامک به دسته طلایی و صفحه‌ساز به دسته نقره‌ای وصل می‌شود. این اتصال را از پنل می‌توانید عوض کنید.
