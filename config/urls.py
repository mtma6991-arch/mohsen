from django.conf import settings
from django.urls import include, path, re_path

from apps.sites import public_views

web_pass = settings.WEB_PASS.strip().strip("/")

urlpatterns = [
    path(f"{web_pass}/", include("apps.core.urls")),
    path("_mohsen/healthz", public_views.healthz),
    path("_preview/<str:domain>/", public_views.preview),
    path("_preview/<str:domain>/<path:rest>", public_views.preview),
    re_path(r"^(?P<rest>.*)$", public_views.front),
]

handler404 = "apps.sites.public_views.page_not_found"
handler500 = "apps.sites.public_views.server_error"
