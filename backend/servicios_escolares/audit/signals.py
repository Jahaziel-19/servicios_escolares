from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict
from django.contrib.contenttypes.models import ContentType

from .models import AuditLog
from .context import get_request_context
from datetime import datetime, date
from decimal import Decimal

EXCLUDE_FIELDS = {'password', 'last_login'}


def _json_safe(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        try:
            return float(v)
        except Exception:
            return str(v)
    return v


def diff_dict(old, new):
    changes = {}
    for k in new.keys():
        if k in EXCLUDE_FIELDS:
            continue
        if old.get(k) != new.get(k):
            changes[k] = {
                'old': _json_safe(old.get(k)),
                'new': _json_safe(new.get(k)),
            }
    return changes


def safe_model_dict(instance):
    d = model_to_dict(instance)
    # Normaliza FKs a ID y añade repr legible
    for f in instance._meta.get_fields():
        if getattr(f, 'many_to_one', False) and hasattr(instance, f.name):
            # Usa el valor del FK id (attname) cuando exista
            attname = getattr(f, 'attname', None)
            if attname and hasattr(instance, attname):
                d[f.name] = getattr(instance, attname)
    return d


def set_original(instance):
    try:
        original = instance.__class__.objects.get(pk=instance.pk)
        instance.__original_dict = safe_model_dict(original)
    except instance.__class__.DoesNotExist:
        instance.__original_dict = {}


@receiver(pre_save)
def capture_original(sender, instance, **kwargs):
    if not hasattr(sender, '_meta') or sender._meta.abstract:
        return
    # Evita registrar cambios del propio AuditLog
    if sender is AuditLog:
        return
    set_original(instance)


@receiver(post_save)
def audit_save(sender, instance, created, **kwargs):
    if not hasattr(sender, '_meta') or sender._meta.abstract:
        return
    if sender is AuditLog:
        return
    ct = ContentType.objects.get_for_model(sender)
    old = getattr(instance, '__original_dict', {}) or {}
    new = safe_model_dict(instance)
    changes = {} if created else diff_dict(old, new)
    user, ip, request_id, source = get_request_context()
    AuditLog.objects.create(
        action='create' if created else 'update',
        content_type=ct,
        object_id=str(instance.pk),
        app_label=ct.app_label,
        model_name=ct.model,
        changes=changes or None,
        actor_id=getattr(user, 'id', None),
        actor_username=getattr(user, 'username', None),
        ip=ip,
        request_id=request_id,
        source=source,
    )


@receiver(post_delete)
def audit_delete(sender, instance, **kwargs):
    if not hasattr(sender, '_meta') or sender._meta.abstract:
        return
    if sender is AuditLog:
        return
    ct = ContentType.objects.get_for_model(sender)
    user, ip, request_id, source = get_request_context()
    AuditLog.objects.create(
        action='delete',
        content_type=ct,
        object_id=str(instance.pk),
        app_label=ct.app_label,
        model_name=ct.model,
        changes=None,
        actor_id=getattr(user, 'id', None),
        actor_username=getattr(user, 'username', None),
        ip=ip,
        request_id=request_id,
        source=source,
    )