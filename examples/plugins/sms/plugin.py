import json
import urllib.error
import urllib.parse
import urllib.request
from html import escape

from mohsen_sdk import BasePlugin, merged_plugin_settings, plugin_get, plugin_set


class Plugin(BasePlugin):
    slug = "sms"
    name = "پیامک"

    def site_context(self, website, request):
        settings = merged_plugin_settings(website, self.slug)
        return {
            "enabled": True,
            "provider": settings.get("provider") or "log",
        }

    def on_form_submit(self, website, form_name, data):
        if form_name not in {"contact", "sms"}:
            return None
        settings = merged_plugin_settings(website, self.slug)
        text = (
            f"پیام از {website.domain}\n"
            f"{data.get('name') or ''} | {data.get('phone') or ''}\n"
            f"{(data.get('message') or '')[:240]}"
        )
        provider = (settings.get("provider") or "log").strip()
        result = {"provider": provider, "ok": False, "detail": ""}
        receptor = (settings.get("receptor") or "").strip()
        if provider == "kavenegar" and settings.get("api_key") and receptor:
            result = _kavenegar(
                api_key=settings.get("api_key"),
                sender=(settings.get("sender") or "").strip(),
                receptor=receptor,
                message=text,
            )
        else:
            result = {"provider": "log", "ok": True, "detail": "در حالت گزارش ذخیره شد"}
        _append_log(website, {"text": text, **result, "form": form_name})
        return result

    def admin_panel(self, request, website):
        current = plugin_get(website, self.slug, "settings", {}) or {}
        defaults = merged_plugin_settings(website, self.slug)
        logs = plugin_get(website, self.slug, "log", []) or []
        rows = []
        for item in list(logs)[-8:][::-1]:
            rows.append(
                "<li><strong>{provider}</strong> — {detail}<br><span>{text}</span></li>".format(
                    provider=escape(str(item.get("provider") or "")),
                    detail=escape(str(item.get("detail") or "")),
                    text=escape(str(item.get("text") or "")),
                )
            )
        html = f"""
        <form method="post" class="stack">
          <input type="hidden" name="csrfmiddlewaretoken" value="{escape(request.META.get('CSRF_COOKIE') or _csrf(request))}">
          <input type="hidden" name="_plugin" value="sms">
          <input type="hidden" name="action" value="save">
          <div class="grid-2">
            <label>حالت
              <select name="provider">
                <option value="log" {'selected' if (current.get('provider') or defaults.get('provider') or 'log') == 'log' else ''}>فقط گزارش</option>
                <option value="kavenegar" {'selected' if (current.get('provider') or defaults.get('provider')) == 'kavenegar' else ''}>کاوه‌نگار</option>
              </select>
            </label>
            <label>شماره گیرنده
              <input name="receptor" value="{escape(str(current.get('receptor') or ''))}" placeholder="{escape(str(defaults.get('receptor') or '09...'))}">
            </label>
            <label>خط ارسال
              <input name="sender" value="{escape(str(current.get('sender') or ''))}" placeholder="{escape(str(defaults.get('sender') or ''))}">
            </label>
            <label>کلید API (خالی = پیش‌فرض دسته)
              <input name="api_key" value="" placeholder="{'تنظیم شده' if (current.get('api_key') or defaults.get('api_key')) else 'خالی'}" autocomplete="off">
            </label>
          </div>
          <p class="hint">مقادیر این فرم فقط همین سایت را عوض می‌کند. پیش‌فرض دسته در صفحه افزونه تنظیم می‌شود.</p>
          <button class="btn" type="submit">ذخیره پیامک این سایت</button>
          <button class="btn ghost" type="submit" name="action" value="test">ارسال آزمایشی</button>
        </form>
        <h3>گزارش اخیر</h3>
        <ul class="log-list">{''.join(rows) or '<li>هنوز موردی نیست.</li>'}</ul>
        """
        return {"title": "پیامک", "html": html}

    def handle_admin_post(self, request, website):
        action = request.POST.get("action") or "save"
        current = dict(plugin_get(website, self.slug, "settings", {}) or {})
        if action == "test":
            self.on_form_submit(
                website,
                "contact",
                {"name": "آزمایش پنل", "phone": current.get("receptor") or "", "message": "پیام آزمایشی سایت‌ساز محسن"},
            )
            return
        current["provider"] = request.POST.get("provider") or "log"
        current["receptor"] = (request.POST.get("receptor") or "").strip()
        current["sender"] = (request.POST.get("sender") or "").strip()
        api_key = (request.POST.get("api_key") or "").strip()
        if api_key:
            current["api_key"] = api_key
        plugin_set(website, self.slug, "settings", current)

    def category_admin_panel(self, request, category, assignment):
        settings = dict(assignment.settings or {})
        token = escape(_csrf(request))
        html = f"""
        <form method="post" class="stack">
          <input type="hidden" name="csrfmiddlewaretoken" value="{token}">
          <input type="hidden" name="_plugin" value="sms">
          <input type="hidden" name="_category" value="{category.id}">
          <div class="grid-2">
            <label>حالت پیش‌فرض
              <select name="provider">
                <option value="log" {'selected' if settings.get('provider', 'log') == 'log' else ''}>فقط گزارش</option>
                <option value="kavenegar" {'selected' if settings.get('provider') == 'kavenegar' else ''}>کاوه‌نگار</option>
              </select>
            </label>
            <label>گیرنده پیش‌فرض<input name="receptor" value="{escape(str(settings.get('receptor') or ''))}"></label>
            <label>خط ارسال<input name="sender" value="{escape(str(settings.get('sender') or ''))}"></label>
            <label>کلید API<input name="api_key" value="" placeholder="{'ثبت شده' if settings.get('api_key') else 'خالی'}" autocomplete="off"></label>
          </div>
          <button class="btn" type="submit">ذخیره پیش‌فرض دسته {escape(category.name)}</button>
        </form>
        """
        return {"title": f"پیامک · {category.name}", "html": html}

    def handle_category_post(self, request, category, assignment):
        settings = dict(assignment.settings or {})
        settings["provider"] = request.POST.get("provider") or "log"
        settings["receptor"] = (request.POST.get("receptor") or "").strip()
        settings["sender"] = (request.POST.get("sender") or "").strip()
        api_key = (request.POST.get("api_key") or "").strip()
        if api_key:
            settings["api_key"] = api_key
        assignment.settings = settings
        assignment.save(update_fields=["settings"])


def _csrf(request):
    from django.middleware.csrf import get_token

    return get_token(request)


def _append_log(website, item):
    logs = list(plugin_get(website, "sms", "log", []) or [])
    logs.append(item)
    plugin_set(website, "sms", "log", logs[-30:])


def _kavenegar(api_key, sender, receptor, message):
    url = f"https://api.kavenegar.com/v1/{urllib.parse.quote(api_key)}/sms/send.json"
    payload = urllib.parse.urlencode({"receptor": receptor, "sender": sender, "message": message}).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = resp.read().decode("utf-8", "replace")[:400]
        parsed = {}
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {}
        ok = (parsed.get("return") or {}).get("status") == 200
        return {"provider": "kavenegar", "ok": ok, "detail": body}
    except urllib.error.URLError as exc:
        return {"provider": "kavenegar", "ok": False, "detail": str(exc)}
