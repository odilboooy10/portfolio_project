from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.apps import apps

from .mixins import AuditableMixin

# Thread-local storage to carry request user into signal handlers
import threading
_local = threading.local()


def set_current_user(user):
    _local.user = user


def get_current_user():
    return getattr(_local, 'user', None)


def _get_field_value(instance, field_name):
    try:
        value = getattr(instance, field_name)
        if hasattr(value, 'pk'):
            return str(value.pk)
        return str(value) if value is not None else None
    except Exception:
        return None


def _build_diff(old_instance, new_instance, tracked_fields):
    """Return {field: [old_value, new_value]} for changed fields."""
    if old_instance is None:
        return {}

    opts = new_instance._meta
    fields = (
        [f.name for f in opts.fields]
        if not tracked_fields
        else tracked_fields
    )

    diff = {}
    for field in fields:
        old_val = _get_field_value(old_instance, field)
        new_val = _get_field_value(new_instance, field)
        if old_val != new_val:
            diff[field] = [old_val, new_val]
    return diff


# Store pre-save snapshots keyed by (model, pk) so post_save can diff them
_pre_save_snapshots: dict = {}


def _connect_auditable_models():
    """Wire up pre_save + post_save + post_delete for every AuditableMixin model."""
    for model in apps.get_models():
        if isinstance(model(), AuditableMixin):
            pre_save.connect(_pre_save_handler, sender=model, weak=False)
            post_save.connect(_post_save_handler, sender=model, weak=False)
            post_delete.connect(_post_delete_handler, sender=model, weak=False)


def _pre_save_handler(sender, instance, **kwargs):
    if instance.pk:
        try:
            _pre_save_snapshots[(sender, instance.pk)] = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            pass


def _post_save_handler(sender, instance, created, **kwargs):
    from apps.audit.models import AuditLog

    tracked = getattr(instance, '_audit_tracked_fields', [])
    key = (sender, instance.pk)

    if created:
        action = AuditLog.Action.CREATE
        changes = {}
    else:
        action = AuditLog.Action.UPDATE
        old = _pre_save_snapshots.pop(key, None)
        changes = _build_diff(old, instance, tracked)
        if not changes:
            return  # nothing actually changed

    AuditLog.objects.create(
        user=get_current_user(),
        action=action,
        app_label=sender._meta.app_label,
        model_name=sender._meta.model_name,
        object_id=str(instance.pk),
        object_repr=str(instance)[:500],
        changes=changes,
    )


def _post_delete_handler(sender, instance, **kwargs):
    from apps.audit.models import AuditLog

    AuditLog.objects.create(
        user=get_current_user(),
        action=AuditLog.Action.DELETE,
        app_label=sender._meta.app_label,
        model_name=sender._meta.model_name,
        object_id=str(instance.pk),
        object_repr=str(instance)[:500],
        changes={},
    )
