class AuditableMixin:
    """
    Add to any Model to enable automatic audit logging via signals.
    The signals module reads _audit_tracked_fields to produce field diffs.
    Leave empty to track all fields; list specific field names to limit scope.
    """
    _audit_tracked_fields: list[str] = []
