from django.urls import path

from apps.categories import views as category_views
from apps.core import views as core_views
from apps.plugins import views as plugin_views
from apps.sites import views as site_views
from apps.templates_engine import views as template_views

urlpatterns = [
    path("", core_views.dashboard, name="dashboard"),
    path("login/", core_views.login_view, name="login"),
    path("logout/", core_views.logout_view, name="logout"),
    path("settings/", core_views.settings_view, name="settings"),
    path("activity/", core_views.activity_view, name="activity"),
    path("password/", core_views.password_view, name="password"),
    path("guide/template/", core_views.guide_template, name="guide-template"),
    path("guide/plugin/", core_views.guide_plugin, name="guide-plugin"),
    path("categories/", category_views.category_list, name="category-list"),
    path("categories/new/", category_views.category_create, name="category-create"),
    path("categories/<int:pk>/", category_views.category_edit, name="category-edit"),
    path("categories/<int:pk>/delete/", category_views.category_delete, name="category-delete"),
    path("templates/", template_views.template_list, name="template-list"),
    path("templates/upload/", template_views.template_upload, name="template-upload"),
    path("templates/example/<str:name>/", template_views.example_download, name="template-example"),
    path("templates/<int:pk>/", template_views.template_detail, name="template-detail"),
    path("templates/<int:pk>/toggle/", template_views.template_toggle, name="template-toggle"),
    path("templates/<int:pk>/delete/", template_views.template_delete, name="template-delete"),
    path("templates/<int:pk>/download/", template_views.template_download, name="template-download"),
    path("plugins/", plugin_views.plugin_list, name="plugin-list"),
    path("plugins/upload/", plugin_views.plugin_upload, name="plugin-upload"),
    path("plugins/example/<str:name>/", plugin_views.example_plugin_download, name="plugin-example"),
    path("plugins/<int:pk>/", plugin_views.plugin_detail, name="plugin-detail"),
    path("plugins/<int:pk>/toggle/", plugin_views.plugin_toggle, name="plugin-toggle"),
    path("plugins/<int:pk>/delete/", plugin_views.plugin_delete, name="plugin-delete"),
    path("sites/", site_views.site_list, name="site-list"),
    path("sites/new/", site_views.site_create, name="site-create"),
    path("sites/<int:pk>/", site_views.site_edit, name="site-edit"),
    path("sites/<int:pk>/delete/", site_views.site_delete, name="site-delete"),
    path("messages/<int:pk>/delete/", site_views.message_delete, name="message-delete"),
]
