import secrets
from html import escape

from markupsafe import Markup

from mohsen_sdk import BasePlugin, plugin_get, plugin_set

TYPES = [
    ("hero", "قهرمان"),
    ("features", "ویژگی‌ها"),
    ("text", "متن"),
    ("faq", "پرسش‌ها"),
    ("cta", "فراخوان"),
    ("gallery", "گالری"),
]


class Plugin(BasePlugin):
    slug = "page-builder"
    name = "صفحه‌ساز"

    def site_context(self, website, request):
        document = _document(website)
        sections = document.get("sections") or []
        html = render_sections(sections) if sections else ""
        return {
            "enabled": True,
            "active": bool(sections),
            "html": Markup(html),
            "count": len(sections),
        }

    def admin_panel(self, request, website):
        document = _document(website)
        sections = document.get("sections") or []
        token = escape(_csrf(request))
        blocks = []
        for index, section in enumerate(sections):
            blocks.append(_editor(section, index, len(sections), token))
        options = "".join(f'<option value="{key}">{label}</option>' for key, label in TYPES)
        html = f"""
        <p class="hint">اگر بخشی بسازید، در قالبی که <code dir="ltr">plugins.page_builder.html</code> را چاپ می‌کند جایگزین محتوای پیش‌فرض همان ناحیه می‌شود.</p>
        <form method="post" class="inline">
          <input type="hidden" name="csrfmiddlewaretoken" value="{token}">
          <input type="hidden" name="_plugin" value="page-builder">
          <input type="hidden" name="action" value="add">
          <select name="type">{options}</select>
          <button class="btn" type="submit">افزودن بخش</button>
        </form>
        <div class="pb-admin">{''.join(blocks) or '<p class="hint">هنوز بخشی نیست. قالب، طرح پیش‌فرض خودش را نشان می‌دهد.</p>'}</div>
        """
        return {"title": "صفحه‌ساز", "html": html}

    def handle_admin_post(self, request, website):
        document = _document(website)
        sections = list(document.get("sections") or [])
        action = request.POST.get("action") or ""
        sid = request.POST.get("id") or ""
        if action == "add":
            kind = request.POST.get("type") or "text"
            if kind not in {key for key, _label in TYPES}:
                kind = "text"
            sections.append(_blank(kind))
        elif action == "delete":
            sections = [item for item in sections if item.get("id") != sid]
        elif action == "move":
            direction = request.POST.get("dir")
            index = next((i for i, item in enumerate(sections) if item.get("id") == sid), None)
            if index is not None:
                swap = index - 1 if direction == "up" else index + 1
                if 0 <= swap < len(sections):
                    sections[index], sections[swap] = sections[swap], sections[index]
        elif action == "save":
            for item in sections:
                if item.get("id") == sid:
                    _apply(item, request.POST)
                    break
        elif action == "clear":
            sections = []
        document["sections"] = sections
        plugin_set(website, self.slug, "document", document)


def _document(website):
    value = plugin_get(website, "page-builder", "document", {}) or {}
    if not isinstance(value, dict):
        value = {}
    value.setdefault("sections", [])
    return value


def _blank(kind):
    return {
        "id": secrets.token_hex(4),
        "type": kind,
        "eyebrow": "",
        "title": "",
        "subtitle": "",
        "body": "",
        "button_label": "",
        "button_url": "",
        "items": [{"title": "", "text": ""} for _ in range(3)],
        "faqs": [{"q": "", "a": ""} for _ in range(3)],
        "caps": ["", "", ""],
    }


def _apply(item, post):
    for key in ("eyebrow", "title", "subtitle", "body", "button_label", "button_url"):
        if key in post:
            item[key] = (post.get(key) or "")[:800]
    item["body"] = (post.get("body") or item.get("body") or "")[:4000]
    items = []
    for index in range(3):
        items.append({
            "title": (post.get(f"item_title_{index}") or "")[:120],
            "text": (post.get(f"item_text_{index}") or "")[:400],
        })
    item["items"] = items
    faqs = []
    for index in range(3):
        faqs.append({
            "q": (post.get(f"faq_q_{index}") or "")[:180],
            "a": (post.get(f"faq_a_{index}") or "")[:600],
        })
    item["faqs"] = faqs
    item["caps"] = [(post.get(f"cap_{index}") or "")[:80] for index in range(3)]


def _editor(section, index, total, token):
    sid = escape(str(section.get("id") or ""))
    kind = section.get("type") or "text"
    label = dict(TYPES).get(kind, kind)
    fields = [
        _input("eyebrow", "برچسب کوچک", section.get("eyebrow") or ""),
        _input("title", "عنوان", section.get("title") or ""),
        _input("subtitle", "زیرعنوان", section.get("subtitle") or ""),
    ]
    if kind in {"text", "hero"}:
        fields.append(_area("body", "متن", section.get("body") or ""))
    if kind in {"hero", "cta"}:
        fields.append(_input("button_label", "متن دکمه", section.get("button_label") or ""))
        fields.append(_input("button_url", "پیوند دکمه", section.get("button_url") or ""))
    if kind == "features":
        for i, item in enumerate((section.get("items") or [{}, {}, {}])[:3]):
            fields.append(_input(f"item_title_{i}", f"ویژگی {i+1}", item.get("title") or ""))
            fields.append(_input(f"item_text_{i}", "توضیح", item.get("text") or ""))
    if kind == "faq":
        for i, item in enumerate((section.get("faqs") or [{}, {}, {}])[:3]):
            fields.append(_input(f"faq_q_{i}", f"پرسش {i+1}", item.get("q") or ""))
            fields.append(_area(f"faq_a_{i}", "پاسخ", item.get("a") or ""))
    if kind == "gallery":
        for i, cap in enumerate((section.get("caps") or ["", "", ""])[:3]):
            fields.append(_input(f"cap_{i}", f"عنوان قاب {i+1}", cap))
    up = "" if index == 0 else f'<button class="btn ghost" name="action" value="move" onclick="this.form.dir.value=\'up\'">بالا</button>'
    down = "" if index == total - 1 else f'<button class="btn ghost" name="action" value="move" onclick="this.form.dir.value=\'down\'">پایین</button>'
    return f"""
    <form method="post" class="pb-block">
      <input type="hidden" name="csrfmiddlewaretoken" value="{token}">
      <input type="hidden" name="_plugin" value="page-builder">
      <input type="hidden" name="id" value="{sid}">
      <input type="hidden" name="dir" value="up">
      <header><strong>{index + 1}. {escape(label)}</strong><span dir="ltr">{escape(kind)}</span></header>
      {''.join(fields)}
      <div class="row-actions">
        <button class="btn" name="action" value="save">ذخیره بخش</button>
        {up}{down}
        <button class="btn danger" name="action" value="delete">حذف</button>
      </div>
    </form>
    """


def _input(name, label, value):
    return f'<label>{escape(label)}<input name="{escape(name)}" value="{escape(str(value))}"></label>'


def _area(name, label, value):
    return f'<label>{escape(label)}<textarea name="{escape(name)}" rows="3">{escape(str(value))}</textarea></label>'


def _csrf(request):
    from django.middleware.csrf import get_token

    return get_token(request)


def render_sections(sections):
    chunks = ['<div class="pb-root">', _STYLE]
    for section in sections:
        kind = section.get("type")
        renderer = {
            "hero": _hero,
            "features": _features,
            "text": _text,
            "faq": _faq,
            "cta": _cta,
            "gallery": _gallery,
        }.get(kind)
        if renderer:
            chunks.append(renderer(section))
    chunks.append("</div>")
    return "".join(chunks)


def e(value):
    return escape(str(value or ""))


def _hero(s):
    button = ""
    if s.get("button_label"):
        button = f'<a class="pb-btn" href="{e(s.get("button_url") or "#")}">{e(s.get("button_label"))}</a>'
    body = f'<p>{e(s.get("body"))}</p>' if s.get("body") else ""
    eyebrow = f'<p class="pb-kicker">{e(s.get("eyebrow"))}</p>' if s.get("eyebrow") else ""
    return f'<section class="pb-hero">{eyebrow}<h2>{e(s.get("title"))}</h2><p>{e(s.get("subtitle"))}</p>{body}{button}</section>'


def _features(s):
    cards = []
    for item in s.get("items") or []:
        if not (item.get("title") or item.get("text")):
            continue
        cards.append(f'<article><h3>{e(item.get("title"))}</h3><p>{e(item.get("text"))}</p></article>')
    return f'<section class="pb-features"><h2>{e(s.get("title"))}</h2><div>{"".join(cards)}</div></section>'


def _text(s):
    return f'<section class="pb-text"><h2>{e(s.get("title"))}</h2><p>{e(s.get("body") or s.get("subtitle"))}</p></section>'


def _faq(s):
    rows = []
    for item in s.get("faqs") or []:
        if not item.get("q"):
            continue
        rows.append(f'<details><summary>{e(item.get("q"))}</summary><p>{e(item.get("a"))}</p></details>')
    return f'<section class="pb-faq"><h2>{e(s.get("title"))}</h2>{"".join(rows)}</section>'


def _cta(s):
    button = ""
    if s.get("button_label"):
        button = f'<a class="pb-btn" href="{e(s.get("button_url") or "#")}">{e(s.get("button_label"))}</a>'
    return f'<section class="pb-cta"><h2>{e(s.get("title"))}</h2><p>{e(s.get("subtitle"))}</p>{button}</section>'


def _gallery(s):
    frames = []
    for cap in s.get("caps") or []:
        frames.append(f'<figure><span></span><figcaption>{e(cap)}</figcaption></figure>')
    return f'<section class="pb-gallery"><h2>{e(s.get("title"))}</h2><div>{"".join(frames)}</div></section>'


_STYLE = """
<style>
.pb-root{display:grid;gap:1.2rem;margin:1rem 0}
.pb-root h2{margin:0 0 .4rem;font-size:1.7rem}
.pb-root p{margin:0;line-height:1.9}
.pb-hero,.pb-cta{padding:1.6rem;border:1px solid rgba(182,137,74,.45);background:linear-gradient(160deg,rgba(182,137,74,.16),transparent)}
.pb-kicker{letter-spacing:.18em;font-size:.78rem;opacity:.75}
.pb-btn{display:inline-block;margin-top:.8rem;padding:.65rem 1rem;background:#1b1a17;color:#f6f1e7;text-decoration:none}
.pb-features>div{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:.8rem}
.pb-features article{padding:1rem;border:1px solid rgba(0,0,0,.08);background:rgba(255,255,255,.35)}
.pb-faq details{padding:.7rem 0;border-bottom:1px solid rgba(0,0,0,.1)}
.pb-gallery>div{display:grid;grid-template-columns:repeat(3,1fr);gap:.6rem}
.pb-gallery figure{margin:0}
.pb-gallery span{display:block;height:120px;background:repeating-linear-gradient(135deg,#d9d3c7,#d9d3c7 8px,#cfc6b6 8px,#cfc6b6 16px)}
.pb-gallery figcaption{font-size:.85rem;padding-top:.35rem}
</style>
"""
