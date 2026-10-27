"""کاتالوگ ثابت المان‌های صفحه‌ساز معمار.

شناسه هر المان (id) قرارداد عمومی است. قالب‌های فعلی و بعدی فقط از همین
شناسه‌ها استفاده می‌کنند تا مشتری بعداً همان قالب را در معمار ویرایش کند.
شناسه‌ها را عوض نکنید؛ المان تازه فقط با شناسه جدید اضافه می‌شود.
"""


def _f(key, label, kind="text", **extra):
    item = {"key": key, "label": label, "type": kind}
    item.update(extra)
    return item


def _element(element_id, name, group, *, accepts_children=False, settings=None):
    return {
        "id": element_id,
        "name": name,
        "group": group,
        "accepts_children": accepts_children,
        "settings": list(settings or []),
    }


_HEADING = [
    _f("text", "متن عنوان"),
    _f("tag", "سطح عنوان", "select", options=["h1", "h2", "h3", "h4", "h5", "h6"]),
]
_TEXT = [_f("text", "متن", "textarea")]
_BUTTON = [_f("text", "متن دکمه"), _f("url", "پیوند", "url")]
_IMAGE = [_f("src", "مسیر تصویر"), _f("alt", "متن جایگزین"), _f("url", "پیوند", "url")]

ELEMENTS = [
    _element("section", "بخش", "layout", accepts_children=True, settings=[_f("css_class", "کلاس CSS"), _f("anchor", "لنگر")]),
    _element("container", "ظرف", "layout", accepts_children=True, settings=[_f("css_class", "کلاس CSS")]),
    _element("columns", "ستون‌ها", "layout", accepts_children=True, settings=[_f("count", "تعداد ستون", "select", options=["2", "3", "4"])]),
    _element("inner-section", "بخش داخلی", "layout", accepts_children=True, settings=[_f("css_class", "کلاس CSS")]),
    _element("heading", "عنوان", "basic", settings=_HEADING),
    _element("text", "متن", "basic", settings=_TEXT),
    _element("image", "تصویر", "basic", settings=_IMAGE),
    _element("video", "ویدیو", "basic", settings=[_f("url", "نشانی ویدیو", "url"), _f("title", "عنوان")]),
    _element("button", "دکمه", "basic", settings=_BUTTON),
    _element("divider", "جداکننده", "basic", settings=[_f("style", "سبک", "select", options=["solid", "dashed", "dotted"])]),
    _element("spacer", "فاصله", "basic", settings=[_f("size", "اندازه", "select", options=["sm", "md", "lg"])]),
    _element("icon", "آیکون", "basic", settings=[_f("name", "نام آیکون"), _f("url", "پیوند", "url")]),
    _element("icon-box", "جعبه آیکون", "basic", settings=[_f("icon", "آیکون"), _f("title", "عنوان"), _f("text", "متن", "textarea"), _f("url", "پیوند", "url")]),
    _element("icon-list", "فهرست آیکون", "basic", settings=[_f("text", "آیتم‌ها، هر خط یکی", "textarea")]),
    _element("image-box", "جعبه تصویر", "basic", settings=[_f("src", "مسیر تصویر"), _f("title", "عنوان"), _f("text", "متن", "textarea"), _f("url", "پیوند", "url")]),
    _element("star-rating", "امتیاز ستاره", "basic", settings=[_f("value", "امتیاز", "select", options=["1", "2", "3", "4", "5"]), _f("label", "برچسب")]),
    _element("alert", "هشدار", "basic", settings=[_f("text", "متن", "textarea"), _f("tone", "لحن", "select", options=["info", "success", "warning", "danger"])]),
    _element("html", "HTML سفارشی", "basic", settings=[_f("html", "HTML", "textarea")]),
    _element("blockquote", "نقل‌قول", "basic", settings=[_f("text", "متن", "textarea"), _f("cite", "منبع")]),
    _element("menu-anchor", "لنگر منو", "basic", settings=[_f("anchor", "شناسه لنگر")]),
    _element("gallery", "گالری", "media", settings=[_f("title", "عنوان"), _f("images", "مسیر تصویرها، هر خط یکی", "textarea")]),
    _element("image-carousel", "اسلایدر تصویر", "media", settings=[_f("title", "عنوان"), _f("images", "مسیر تصویرها، هر خط یکی", "textarea")]),
    _element("video-playlist", "فهرست ویدیو", "media", settings=[_f("title", "عنوان"), _f("urls", "نشانی‌ها، هر خط یکی", "textarea")]),
    _element("lottie", "انیمیشن", "media", settings=[_f("src", "مسیر فایل انیمیشن"), _f("label", "برچسب")]),
    _element("google-maps", "نقشه", "media", settings=[_f("query", "نشانی یا مختصات"), _f("zoom", "بزرگ‌نمایی", "select", options=["12", "14", "16"])]),
    _element("accordion", "آکاردئون", "interactive", accepts_children=True, settings=[_f("title", "عنوان"), _f("items", "پرسش و پاسخ، هر بلوک با یک خط خالی", "textarea")]),
    _element("tabs", "زبانه‌ها", "interactive", accepts_children=True, settings=[_f("title", "عنوان"), _f("tabs", "عنوان زبانه‌ها، هر خط یکی", "textarea")]),
    _element("toggle", "سوییچ", "interactive", settings=[_f("title", "عنوان"), _f("text", "متن", "textarea")]),
    _element("counter", "شمارنده", "interactive", settings=[_f("value", "عدد"), _f("label", "برچسب"), _f("text", "شرح")]),
    _element("progress", "نوار پیشرفت", "interactive", settings=[_f("value", "درصد"), _f("label", "برچسب")]),
    _element("countdown", "شمارش معکوس", "interactive", settings=[_f("until", "زمان پایان"), _f("label", "برچسب")]),
    _element("form", "فرم", "interactive", accepts_children=True, settings=[_f("title", "عنوان"), _f("submit", "متن دکمه")]),
    _element("search-form", "فرم جستجو", "interactive", settings=[_f("placeholder", "متن راهنما"), _f("button", "متن دکمه")]),
    _element("social-icons", "آیکون شبکه", "interactive", settings=[_f("links", "نام|نشانی در هر خط", "textarea")]),
    _element("share-buttons", "دکمه‌های اشتراک", "interactive", settings=[_f("label", "برچسب"), _f("networks", "شبکه‌ها، هر خط یکی", "textarea")]),
    _element("hero", "قهرمان", "marketing", accepts_children=True, settings=[_f("eyebrow", "برچسب کوچک"), _f("title", "عنوان"), _f("subtitle", "زیرعنوان", "textarea"), _f("button_label", "متن دکمه"), _f("button_url", "پیوند دکمه", "url")]),
    _element("call-to-action", "فراخوان", "marketing", accepts_children=True, settings=[_f("title", "عنوان"), _f("text", "متن", "textarea"), _f("button_label", "متن دکمه"), _f("button_url", "پیوند دکمه", "url")]),
    _element("testimonial", "نظر مشتری", "marketing", settings=[_f("quote", "متن نظر", "textarea"), _f("name", "نام"), _f("role", "سمت")]),
    _element("testimonials-carousel", "اسلایدر نظرات", "marketing", settings=[_f("title", "عنوان"), _f("items", "نظرها، هر بلوک با یک خط خالی", "textarea")]),
    _element("price-table", "جدول قیمت", "marketing", settings=[_f("title", "نام طرح"), _f("price", "قیمت"), _f("features", "ویژگی‌ها، هر خط یکی", "textarea"), _f("button_label", "متن دکمه"), _f("button_url", "پیوند", "url")]),
    _element("price-list", "فهرست قیمت", "marketing", settings=[_f("title", "عنوان"), _f("items", "نام|قیمت در هر خط", "textarea")]),
    _element("flip-box", "جعبه چرخشی", "marketing", settings=[_f("front", "روی جعبه"), _f("back", "پشت جعبه", "textarea"), _f("url", "پیوند", "url")]),
    _element("slides", "اسلایدها", "marketing", accepts_children=True, settings=[_f("title", "عنوان")]),
    _element("nav-menu", "منوی ناوبری", "marketing", accepts_children=True, settings=[_f("label", "برچسب دسترس‌پذیری")]),
    _element("logo", "لوگو", "marketing", settings=[_f("text", "متن لوگو"), _f("src", "مسیر تصویر لوگو"), _f("url", "پیوند", "url")]),
    _element("site-title", "عنوان سایت", "marketing", settings=[_f("text", "عنوان")]),
    _element("footer", "پاصفحه", "marketing", accepts_children=True, settings=[_f("text", "متن پاصفحه", "textarea")]),
    _element("contact-form", "فرم تماس", "marketing", accepts_children=True, settings=[_f("title", "عنوان"), _f("submit", "متن دکمه ارسال")]),
    _element("product-grid", "شبکه محصولات", "marketing", accepts_children=True, settings=[_f("title", "عنوان"), _f("source", "کلید داده", "select", options=["products", "phones", "items"])]),
    _element("posts-grid", "شبکه نوشته‌ها", "marketing", accepts_children=True, settings=[_f("title", "عنوان"), _f("source", "کلید داده")]),
]

GROUPS = [
    ("layout", "سازه"),
    ("basic", "پایه"),
    ("media", "رسانه"),
    ("interactive", "تعاملی"),
    ("marketing", "بازاریابی و سایت"),
]

BY_ID = {item["id"]: item for item in ELEMENTS}

assert len(ELEMENTS) == 50, len(ELEMENTS)
assert len(BY_ID) == 50
