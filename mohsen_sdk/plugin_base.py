class BasePlugin:
    """کلاس پایه هر افزونه.

    افزونه با امتیاز کاربر مدیر اجرا می‌شود (مشابه وردپرس).
    فقط کد مورد اعتماد را بارگذاری کنید.
    """

    slug = ""
    name = ""

    def site_context(self, website, request):
        """دیکشنری که در قالب سایت زیر plugins.<slug> در دسترس است."""
        return {}

    def head_html(self, website, request):
        return ""

    def on_form_submit(self, website, form_name, data):
        return None

    def admin_panel(self, request, website):
        """{'title': str, 'html': str} یا None."""
        return None

    def handle_admin_post(self, request, website):
        return None

    def category_admin_panel(self, request, category, assignment):
        return None

    def handle_category_post(self, request, category, assignment):
        return None
