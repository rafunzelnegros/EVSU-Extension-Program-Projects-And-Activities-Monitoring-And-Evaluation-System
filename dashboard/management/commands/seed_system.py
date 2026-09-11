from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from dashboard.models import Unit,UserProfile,ExtensionIndicator
INDICATORS=[
'Number of active partnerships with LGUs, industries, NGOs, NGAs, SMEs, and other stakeholders as a result of extension activities',
'Number of trainees weighted by the length of training',
'Number of extension programs organized and supported consistent with the SUCs mandated and priority programs.',
'Percentage of beneficiaries who rate the training courses and advisory services as satisfactory or higher in terms of quality and relevance.',
'Percentage of plantilla faculty involved in extension services','Percentage of plantilla staff involved in extension services','Percentage of students involved in extension services',
'Number of extension activities featured on the following modalities: print, radio, and online media','Number of technologies/innovations adopted and commercialized','Number of ordinance/resolutions passed and approved by the local government resulting from technology/innovation introduced by the SUC','Number of trained stakeholders on need-based training program','Number of MSMEs or partners engaged','Number of extension projects assessed','Number of awards or recognition of public service program received from government/international organizations','No. of LGUs with active, resource-sharing MOAs','Number of community enterprises established','Percentage of partner LGUs with approved, integrated local DRRM/CCA plans','Number of certified Community Resilience Advocates (CRAs) & technical trainers','No. of university-developed climate-smart technologies/livelihood models adopted','Number of partner communities with functional Early Warning System (EWS)','BOR Approved Extension Program/Agenda','Utilization rate of allocated funds for extension services (GAA)','Utilization rate of allocated funds for extension services (IGF)','Extension Outreach Activity']
UNITS=[('SAAD','SAAD','SCHOOL','Main Campus'),('SAS','SAS','SCHOOL','Main Campus'),('SAME','SAME','SCHOOL','Main Campus'),('SOT','SOT','SCHOOL','Main Campus'),('SOE','SOE','SCHOOL','Main Campus'),('SOED','SOEd','SCHOOL','Main Campus'),('BURAUEN','Burauen Campus','CAMPUS','Burauen Campus'),('CARIGARA','Carigara Campus','CAMPUS','Carigara Campus'),('DULAG','Dulag Campus','CAMPUS','Dulag Campus'),('ORMOC','Ormoc City Campus','CAMPUS','Ormoc City Campus'),('TANAUAN','Tanauan Campus','CAMPUS','Tanauan Campus')]
class Command(BaseCommand):
    help='Seed EVSU units, 24 indicators, and optional placeholder role accounts.'
    def add_arguments(self,p): p.add_argument('--demo-users',action='store_true'); p.add_argument('--reset-users',action='store_true')
    def handle(self,*a,**o):
        for code,name,t,campus in UNITS: Unit.objects.update_or_create(code=code,defaults={'name':name,'unit_type':t,'campus_name':campus,'active':True})
        for i,name in enumerate(INDICATORS,1): ExtensionIndicator.objects.update_or_create(order=i,defaults={'name':name,'is_percentage':i in (4,5,6,7,17,22,23),'active':True})
        if o['reset_users']:
            User.objects.all().delete(); self.stdout.write(self.style.WARNING('All users cleared.'))
        if o['demo_users']:
            def mk(username,role,unit=None,superuser=False):
                u,_=User.objects.get_or_create(username=username,defaults={'is_active':True}); u.set_password('ChangeMe123!'); u.is_superuser=superuser; u.is_staff=superuser; u.save(); UserProfile.objects.update_or_create(user=u,defaults={'role':role,'unit':unit}); return u
            mk('me_head_1',UserProfile.ME_HEAD,superuser=True); mk('me_head_2',UserProfile.ME_HEAD,superuser=True); mk('admin_staff',UserProfile.ADMIN_STAFF); mk('director',UserProfile.DIRECTOR)
            for unit in Unit.objects.exclude(unit_type=Unit.OFFICE): mk('coord_'+unit.code.lower(),UserProfile.COORDINATOR,unit)
            self.stdout.write(self.style.WARNING('Demo password for seeded accounts: ChangeMe123! — change immediately.'))
        self.stdout.write(self.style.SUCCESS('EVSU master data seeded.'))
