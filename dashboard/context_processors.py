from .models import UserProfile


def app_context(request):
    role = ''
    unit = None
    display_name = ''
    role_label = ''
    if getattr(request, 'user', None) and request.user.is_authenticated:
        display_name = request.user.get_full_name().strip() or request.user.username
        try:
            p = request.user.evsu_profile
            role = p.role
            unit = p.unit
        except Exception:
            if request.user.is_superuser:
                role = UserProfile.ME_HEAD

        if role == UserProfile.COORDINATOR:
            if unit:
                if unit.unit_type == unit.CAMPUS:
                    role_label = f'{unit.name} Coordinator'
                else:
                    role_label = f'{unit.code} Coordinator'
            else:
                role_label = 'Coordinator'
        elif role == UserProfile.ME_HEAD:
            role_label = 'Monitoring & Evaluation Head'
        elif role == UserProfile.ADMIN_STAFF:
            role_label = 'Admin Staff'
        elif role == UserProfile.DIRECTOR:
            role_label = 'Director'
        else:
            role_label = 'User'

    return {
        'current_role': role,
        'current_unit': unit,
        'current_user_name': display_name,
        'current_role_label': role_label,
    }
