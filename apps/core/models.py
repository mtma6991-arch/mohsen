from django.db import models


class ActivityLog(models.Model):
    username = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=80)
    object_repr = models.CharField(max_length=200, blank=True)
    message = models.CharField(max_length=500, blank=True)
    ip = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} {self.object_repr}"


class AdminDomain(models.Model):
    domain = models.CharField(max_length=253, unique=True)
    note = models.CharField(max_length=200, blank=True)
    https = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "domain"]

    def __str__(self):
        return self.domain
