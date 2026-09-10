from .models import TaepReport, QparReport, Notification, UNITS


def global_context(request):
    pending = 0
    unread = 0
    current_role = ''
    current_unit = ''
    current_identity = ''

    if request.user.is_authenticated:
        if request.user.is_superuser:
            current_role = 'DIRECTOR'
            current_identity = 'Director'
        else:
            try:
                profile = request.user.profile
                current_role = profile.role
                current_unit = profile.unit
                current_identity = profile.identity_label
            except Exception:
                pass

        if current_role in ('DIRECTOR', 'ADMIN'):
            pending = (
                TaepReport.objects.filter(status='PENDING').exclude(owner=request.user).count()
                + QparReport.objects.filter(status='PENDING').exclude(owner=request.user).count()
            )
        unread = Notification.objects.filter(user=request.user, is_read=False).count()

    return {
        'pending_reports_count': pending,
        'unread_notifications_count': unread,
        'current_role': current_role,
        'current_unit': current_unit,
        'current_identity': current_identity,
        'unit_labels': dict(UNITS),
    }
