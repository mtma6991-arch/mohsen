# راهنمای زیپ قالب
قالب‌های محسن فایل زیپ هستند و در پنل، بخش «قالب‌ها»، برای یک دسته بارگذاری می‌شوند. همان راهنما داخل پنل هم هست. از نسخه ۱.۱ هر قالب باید بر اساس صفحه‌ساز **معمار** باشد تا مشتری همان قالب خریداری‌شده را بعداً در پنل ویرایش کند و به قالب دیگری برخورد نکند.
## اصل معمار
معمار کاتالوگ ثابت ۵۰ المان ساخت وب است. هر المان یک `id` پایدار دارد (مثل ویجت المنتور). هر بار استفاده در یک قالب یک `uid` یکتا دارد. ویرایش مشتری در `website.settings.memar` با همین uid ذخیره می‌شود و تابع `memar()` آن را در صفحه چاپ می‌کند.
زیپ بدون `architect.json`، یا با شناسه خارج از این فهرست، رد می‌شود.
## ساختار
```
template.json
architect.json
layout/base.html
pages/home.html
pages/about.html
pages/contact.html
assets/style.css
assets/fonts/
```
اگر یک پوشه والد تنها وجود داشته باشد و هر دو فایل json داخل آن باشند، پذیرفته می‌شود.
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
| demo_data | خیر | شیء JSON داده نمونه؛ فهرست کالا اینجاست |
## architect.json
```json
{
  "builder": "memar",
  "version": "1.0",
  "nodes": [
    {"uid": "home-hero", "id": "hero", "page": "home", "settings": {}},
    {"uid": "home-title", "id": "heading", "page": "home", "parent": "home-hero", "settings": {}}
  ]
}
```
- `builder` باید دقیقاً `memar` باشد.
- `uid` یکتا و مطابق `[a-z0-9-]+`.
- `id` فقط از جدول زیر.
- `page` برابر slug یکی از صفحات `template.json` یا مقدار `layout` برای `layout/base.html`.
- `parent` اختیاری. والد باید در همان صفحه باشد و در کاتالوگ فرزند بپذیرد.
- `settings` فقط کلیدهای همان المان. مقدار خالی ذخیره نکنید؛ پیش‌فرض داخل قالب با آرگومان سوم `memar()` می‌ماند.
## نشانه‌گذاری HTML
هر دو ویژگی باید روی همان برچسب باشند:
```html
<h1 data-memar-id="heading" data-memar-uid="home-title">{{ memar('home-title', 'text', site.title) }}</h1>
```
`memar('uid', 'کلید', پیش‌فرض)` اگر مشتری در معمار مقداری ذخیره کرده باشد همان را برمی‌گرداند، وگرنه پیش‌فرض را. فراخوانی `memar('...')` باید به uid موجود در `architect.json` اشاره کند.
فرم تماس پلتفرم: المان `contact-form`، متد POST به `form_action('contact')`، فیلدهای `name` و `phone` و `email` و `message`، توکن `csrf_token`، و فیلد مخفی `company_website` به‌عنوان هانی‌پات.
## بافت Jinja2
موتور، محیط سندباکس با autoescape است.
- `site` مشخصات مشتری: title, tagline, description, phone, email, address, logo_text, domain, accent_color, category, category_slug
- `page` و `pages`
- `data` حاصل ادغام `demo_data` با JSON اختصاصی سایت
- `plugins.<slug>` خروجی افزونه‌های فعال همان دسته
- `memar(uid, key, default)` مقدار معمار
- `asset(path)` ، `page_url(slug)` ، `form_action(name)` ، `csrf_token` ، `sent`
## ۵۰ شناسه معمار
توسعه‌دهنده در زیپ فقط ستون شناسه را می‌نویسد. این شناسه‌ها ثابت‌اند و در قالب‌های بعدی هم همین‌ها استفاده می‌شوند.
### سازه
| شناسه | نام | فرزند می‌پذیرد |
| --- | --- | --- |
| `section` | بخش | بله |
| `container` | ظرف | بله |
| `columns` | ستون‌ها | بله |
| `inner-section` | بخش داخلی | بله |

### پایه
| شناسه | نام | فرزند می‌پذیرد |
| --- | --- | --- |
| `heading` | عنوان | خیر |
| `text` | متن | خیر |
| `image` | تصویر | خیر |
| `video` | ویدیو | خیر |
| `button` | دکمه | خیر |
| `divider` | جداکننده | خیر |
| `spacer` | فاصله | خیر |
| `icon` | آیکون | خیر |
| `icon-box` | جعبه آیکون | خیر |
| `icon-list` | فهرست آیکون | خیر |
| `image-box` | جعبه تصویر | خیر |
| `star-rating` | امتیاز ستاره | خیر |
| `alert` | هشدار | خیر |
| `html` | HTML سفارشی | خیر |
| `blockquote` | نقل‌قول | خیر |
| `menu-anchor` | لنگر منو | خیر |

### رسانه
| شناسه | نام | فرزند می‌پذیرد |
| --- | --- | --- |
| `gallery` | گالری | خیر |
| `image-carousel` | اسلایدر تصویر | خیر |
| `video-playlist` | فهرست ویدیو | خیر |
| `lottie` | انیمیشن | خیر |
| `google-maps` | نقشه | خیر |

### تعاملی
| شناسه | نام | فرزند می‌پذیرد |
| --- | --- | --- |
| `accordion` | آکاردئون | بله |
| `tabs` | زبانه‌ها | بله |
| `toggle` | سوییچ | خیر |
| `counter` | شمارنده | خیر |
| `progress` | نوار پیشرفت | خیر |
| `countdown` | شمارش معکوس | خیر |
| `form` | فرم | بله |
| `search-form` | فرم جستجو | خیر |
| `social-icons` | آیکون شبکه | خیر |
| `share-buttons` | دکمه‌های اشتراک | خیر |

### بازاریابی و سایت
| شناسه | نام | فرزند می‌پذیرد |
| --- | --- | --- |
| `hero` | قهرمان | بله |
| `call-to-action` | فراخوان | بله |
| `testimonial` | نظر مشتری | خیر |
| `testimonials-carousel` | اسلایدر نظرات | خیر |
| `price-table` | جدول قیمت | خیر |
| `price-list` | فهرست قیمت | خیر |
| `flip-box` | جعبه چرخشی | خیر |
| `slides` | اسلایدها | بله |
| `nav-menu` | منوی ناوبری | بله |
| `logo` | لوگو | خیر |
| `site-title` | عنوان سایت | خیر |
| `footer` | پاصفحه | بله |
| `contact-form` | فرم تماس | بله |
| `product-grid` | شبکه محصولات | بله |
| `posts-grid` | شبکه نوشته‌ها | بله |

## قواعد رد شدن زیپ
- نبود `architect.json` یا builder غیر از memar
- شناسه خارج از جدول، uid تکراری، uid بدون معادل HTML، یا HTML بدون معادل در سند
- فقط یکی از `data-memar-id` و `data-memar-uid` روی یک برچسب
- صفحه بدون المان معمار
- پسوند غیرمجاز، فایل پایتون، مسیر `..`، سیم‌لینک، زیپ خراب
- سقف تقریبی ۸۰ مگابایت فشرده و ۲۰۰ مگابایت باز شده
- خطای نحوی Jinja
نمونه‌های منطبق: `examples/templates/jewelry-atelier` و `examples/templates/silver-phones`.
