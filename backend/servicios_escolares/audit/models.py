from django.db import models
from django.contrib.contenttypes.models import ContentType


class AuditLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=12)  # create|update|delete
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=64)
    app_label = models.CharField(max_length=64)
    model_name = models.CharField(max_length=64)
    changes = models.JSONField(null=True, blank=True)
    actor_id = models.IntegerField(null=True, blank=True)
    actor_username = models.CharField(max_length=150, null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    request_id = models.CharField(max_length=64, null=True, blank=True)
    source = models.CharField(max_length=24, null=True, blank=True)
    extra = models.JSONField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['content_type', 'object_id', 'created_at']),
            models.Index(fields=['app_label', 'model_name']),
            models.Index(fields=['actor_id']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.created_at}] {self.app_label}.{self.model_name}({self.object_id}) {self.action}"