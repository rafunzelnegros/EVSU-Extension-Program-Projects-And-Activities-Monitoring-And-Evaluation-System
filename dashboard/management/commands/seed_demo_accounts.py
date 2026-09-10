from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from dashboard.models import UserProfile
ACCOUNTS=[('adminstaff','ADMIN',''),('saad.coordinator','SCHOOL','SAAD'),('sas.coordinator','SCHOOL','SAS'),('same.coordinator','SCHOOL','SAME'),('sot.coordinator','SCHOOL','SOT'),('soe.coordinator','SCHOOL','SOE'),('soed.coordinator','SCHOOL','SOED'),('burauen.head','CAMPUS','BURAUEN'),('carigara.head','CAMPUS','CARIGARA'),('dulag.head','CAMPUS','DULAG'),('ormoc.head','CAMPUS','ORMOC'),('tanauan.head','CAMPUS','TANAUAN')]
class Command(BaseCommand):
    def handle(self,*args,**kwargs):
        password='ChangeMe123!'
        for username,role,unit in ACCOUNTS:
            u,created=User.objects.get_or_create(username=username)
            if created:u.set_password(password);u.save()
            UserProfile.objects.update_or_create(user=u,defaults={'role':role,'unit':unit})
        self.stdout.write(self.style.SUCCESS('Demo accounts created. Temporary password: ChangeMe123!'))
