from .models import UserProfile

def app_context(request):
    role=''
    unit=None
    if getattr(request,'user',None) and request.user.is_authenticated:
        try:
            p=request.user.evsu_profile; role=p.role; unit=p.unit
        except Exception:
            if request.user.is_superuser: role=UserProfile.ME_HEAD
    return {'current_role':role,'current_unit':unit}
