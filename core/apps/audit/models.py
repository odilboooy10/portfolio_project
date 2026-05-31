import uuid
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        = models.ForeignKey(
        'users.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='audit_logs'
    )
    action      = models.CharField(max_length=10, choices=Action.choices)
    app_label   = models.CharField(max_length=100)
    model_name  = models.CharField(max_length=100)
    object_id   = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=500)
    changes     = models.JSONField(default=dict)
    timestamp   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['app_label', 'model_name', 'object_id']),
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.action} {self.model_name} {self.object_id} by {self.user}"
