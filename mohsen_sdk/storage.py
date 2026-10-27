def _storage_model():
    from apps.plugins.models import PluginStorage

    return PluginStorage


def plugin_get(website, slug, key, default=None):
    PluginStorage = _storage_model()
    row = PluginStorage.objects.filter(website=website, plugin_slug=slug, key=key).first()
    if row is None:
        return default
    return row.value


def plugin_set(website, slug, key, value):
    PluginStorage = _storage_model()
    PluginStorage.objects.update_or_create(
        website=website,
        plugin_slug=slug,
        key=key,
        defaults={"value": value},
    )


def category_plugin_settings(category, slug):
    from apps.plugins.models import CategoryPlugin

    row = (
        CategoryPlugin.objects.filter(category=category, plugin__slug=slug, enabled=True)
        .select_related("plugin")
        .first()
    )
    if row is None:
        return {}
    return dict(row.settings or {})


def merged_plugin_settings(website, slug):
    base = category_plugin_settings(website.category, slug)
    override = plugin_get(website, slug, "settings", {}) or {}
    if not isinstance(override, dict):
        override = {}
    merged = dict(base)
    for key, value in override.items():
        if value not in ("", None):
            merged[key] = value
    return merged
