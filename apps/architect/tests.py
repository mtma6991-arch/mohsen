import io
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

from apps.architect.catalog import BY_ID, ELEMENTS
from apps.architect.document import validate_architect
from apps.core.access import build_login_urls
from apps.core.bootstrap_data import ensure_categories, ensure_examples
from apps.core.zipsafe import ZipRejected
from apps.sites.models import Website


class ArchitectCatalogTests(SimpleTestCase):
    def test_catalog_has_fifty_stable_ids(self):
        self.assertEqual(len(ELEMENTS), 50)
        self.assertEqual(len(BY_ID), 50)
        for item in ELEMENTS:
            self.assertEqual(item["id"], item["id"].lower())
            self.assertNotIn(" ", item["id"])

    def test_login_urls_are_real_browser_addresses(self):
        urls = build_login_urls(
            ["203.0.113.10"],
            "8787",
            "secret-pass",
            [{"domain": "panel.example.com", "https": True}, {"domain": "panel.example.net", "https": False}],
        )
        self.assertEqual(urls[0], "http://203.0.113.10:8787/secret-pass/")
        self.assertIn("http://203.0.113.10/secret-pass/", urls)
        self.assertIn("https://panel.example.com/secret-pass/", urls)
        self.assertIn("http://panel.example.net/secret-pass/", urls)
        self.assertIn("http://panel.example.net:8787/secret-pass/", urls)
        blob = " ".join(urls)
        self.assertNotIn("SERVER", blob)
        self.assertNotIn("IP-SERVER", blob)

    def test_login_urls_skip_placeholder_hosts(self):
        self.assertEqual(build_login_urls(["127.0.0.1", "SERVER", ""], "8787", "panel", []), [])

    def test_docs_name_every_element_id(self):
        guide = Path(settings.BASE_DIR, "docs", "template-zip-guide.md").read_text(encoding="utf-8")
        for item in ELEMENTS:
            self.assertIn(item["id"], guide)
        self.assertIn("architect.json", guide)
        self.assertIn("memar(", guide)

    def test_sample_templates_match_architect_rules(self):
        samples = {
            "jewelry-atelier": ["home", "collection", "about", "contact"],
            "silver-phones": ["home", "phones", "about", "contact"],
        }
        for slug, pages in samples.items():
            root = Path(settings.BASE_DIR) / "examples" / "templates" / slug
            files = {page: f"pages/{page}.html" for page in pages}
            document = validate_architect(root, pages, files)
            self.assertEqual(document["builder"], "memar")
            self.assertGreaterEqual(len(document["nodes"]), 10)

    def test_rejects_unknown_element(self):
        with tempfile.TemporaryDirectory() as tmp:
            bare = Path(tmp)
            (bare / "pages").mkdir()
            (bare / "pages" / "home.html").write_text("<h1>سلام</h1>", encoding="utf-8")
            with self.assertRaises(ZipRejected):
                validate_architect(bare, ["home"], {"home": "pages/home.html"})
            (bare / "architect.json").write_text(
                json.dumps(
                    {
                        "builder": "memar",
                        "version": "1.0",
                        "nodes": [{"uid": "home-title", "id": "not-a-widget", "page": "home", "settings": {}}],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ZipRejected) as caught:
                validate_architect(bare, ["home"], {"home": "pages/home.html"})
            self.assertIn("ناشناخته", str(caught.exception))


class ArchitectZipBytesTests(SimpleTestCase):
    def test_sample_zips_keep_architect_file(self):
        root = Path(settings.BASE_DIR) / "examples" / "templates" / "silver-phones"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            for path in root.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(root).as_posix())
        buf.seek(0)
        with zipfile.ZipFile(buf) as archive:
            self.assertIn("architect.json", set(archive.namelist()))


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="mohsen-memar-"))
class ArchitectRenderTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        ensure_categories()
        notes = ensure_examples()
        self.notes = notes
        get_user_model().objects.create_superuser("admin", "admin@example.com", "pass12345")

    def test_customer_edit_changes_live_text(self):
        self.assertFalse(any("نامعتبر" in note or "architect" in note for note in self.notes), self.notes)
        site = Website.objects.get(domain="zarrin.local")
        site.settings = {"memar": {"home-title": {"text": "عنوان ویرایش‌شده معمار"}}}
        site.save(update_fields=["settings"])
        response = self.client.get("/", HTTP_HOST="zarrin.local")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "عنوان ویرایش‌شده معمار")
        self.assertContains(response, 'data-memar-id="heading"')
        self.assertContains(response, 'data-memar-uid="home-title"')

    def test_panel_editor_and_guide(self):
        self.client.login(username="admin", password="pass12345")
        site = Website.objects.get(domain="hamrah.local")
        response = self.client.get(f"/panel/sites/{site.pk}/memar/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "معمار")
        self.assertContains(response, "home-title")
        self.assertContains(response, "heading")
        guide = self.client.get("/panel/guide/template/")
        self.assertContains(guide, "architect.json")
        self.assertContains(guide, "product-grid")
        self.assertContains(guide, "contact-form")
