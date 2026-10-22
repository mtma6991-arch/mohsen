import io
import shutil
import tempfile
import zipfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.categories.models import Category
from apps.core.bootstrap_data import ensure_categories, ensure_examples
from apps.core.zipsafe import ALLOWED_TEMPLATE_EXT, ZipRejected, inspect_zip
from apps.sites.forms import WebsiteForm
from apps.sites.models import ContactMessage, Website
from mohsen_sdk import plugin_set


class ZipSafetyTests(TestCase):
    def test_rejects_parent_traversal(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("../evil.txt", "nope")
        buf.seek(0)
        with zipfile.ZipFile(buf) as archive:
            with self.assertRaises(ZipRejected):
                inspect_zip(archive, ALLOWED_TEMPLATE_EXT)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="mohsen-test-"))
class PlatformTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        from django.conf import settings

        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        ensure_categories()
        ensure_examples()
        get_user_model().objects.create_superuser("admin", "admin@example.com", "pass12345")

    def test_panel_requires_staff(self):
        response = self.client.get("/panel/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/panel/login/", response["Location"])
        self.client.login(username="admin", password="pass12345")
        response = self.client.get("/panel/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "پیشخوان")
        self.assertEqual(self.client.get("/panel/guide/template/").status_code, 200)
        self.assertEqual(self.client.get("/panel/guide/plugin/").status_code, 200)
        self.assertEqual(self.client.get("/panel/templates/").status_code, 200)
        self.assertEqual(self.client.get("/panel/plugins/").status_code, 200)
        site = Website.objects.get(domain="zarrin.local")
        self.assertEqual(self.client.get(f"/panel/sites/{site.pk}/").status_code, 200)

    def test_gold_site_renders_and_silver_is_isolated(self):
        gold = self.client.get("/", HTTP_HOST="zarrin.local")
        self.assertEqual(gold.status_code, 200)
        self.assertContains(gold, "خانه زرین")
        silver = self.client.get("/", HTTP_HOST="hamrah.local")
        self.assertContains(silver, "همراه کالا")
        self.assertContains(silver, "لیست گوشی")

    def test_page_builder_escapes_html(self):
        site = Website.objects.get(domain="hamrah.local")
        plugin_set(
            site,
            "page-builder",
            "document",
            {
                "sections": [
                    {
                        "id": "a",
                        "type": "hero",
                        "title": "<script>alert(1)</script>",
                        "subtitle": "زیر",
                        "body": "",
                        "button_label": "",
                        "button_url": "",
                        "items": [],
                        "faqs": [],
                        "caps": [],
                    }
                ]
            },
        )
        response = self.client.get("/", HTTP_HOST="hamrah.local")
        body = response.content.decode()
        self.assertIn("&" + "lt;script&" + "gt;alert(1)", body)
        self.assertNotIn("<" + "script>alert(1)</" + "script>", body)

    def test_contact_form_notifies_sms_plugin_only_on_that_category(self):
        response = self.client.post(
            "/_mohsen/form/contact/",
            {"name": "علی", "phone": "09120000000", "message": "سلام از تست"},
            HTTP_HOST="zarrin.local",
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactMessage.objects.filter(website__domain="zarrin.local").count(), 1)
        from apps.plugins.models import PluginStorage

        log = PluginStorage.objects.get(website__domain="zarrin.local", plugin_slug="sms", key="log")
        self.assertTrue(log.value)
        self.assertFalse(
            PluginStorage.objects.filter(website__domain="hamrah.local", plugin_slug="sms").exists()
        )

    def test_template_must_match_category(self):
        gold = Category.objects.get(slug="gold")
        silver = Category.objects.get(slug="silver")
        phone = silver.templates.get(slug="silver-phones")
        form = WebsiteForm(
            data={
                "customer_name": "بد",
                "domain": "bad.example.com",
                "category": gold.pk,
                "template": phone.pk,
                "title": "بد",
                "status": "active",
                "content_json": "",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("template", form.errors)

    def test_preview_is_private(self):
        response = self.client.get("/_preview/zarrin.local/")
        self.assertEqual(response.status_code, 302)
        self.client.login(username="admin", password="pass12345")
        response = self.client.get("/_preview/zarrin.local/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "خانه زرین")

    def test_unknown_host_hides_panel_path(self):
        response = self.client.get("/", HTTP_HOST="unknown.example.com")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "/panel/")
        self.assertContains(response, "محسن")
