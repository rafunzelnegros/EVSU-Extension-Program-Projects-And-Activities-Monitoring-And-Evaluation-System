from django.core.management.base import BaseCommand
from dashboard.models import ExtensionIndicator
INDICATORS=[
"Number of active partnerships with LGUs, industries, NGOs, NGAs, SMEs, and other stakeholders as a result of extension activities",
"Number of trainees weighted by the length of training",
"Number of extension programs organized and supported consistent with the SUCs mandated and priority programs.",
"Percentage of beneficiaries who rate the training courses and advisory services as satisfactory or higher in terms of quality and relevance.",
"Percentage of plantilla faculty involved in extension services",
"Percentage of plantilla staff involved in extension services",
"Percentage of students involved in extension services",
"Number of extension activities featured on the following modalities: print, radio, and online media",
"Number of technologies/innovations adopted and commercialized",
"Number of ordinance/resolutions passed and approved by the local government resulting from technology/innovation introduced by the SUC",
"Number of trained stakeholders on need-based training program",
"Number of MSMEs or partners engaged",
"Number of extension projects assessed",
"Number of awards or recognition of public service program received from government/international organizations",
"No. of LGUs with active, resource-sharing MOAs",
"Number of community enterprises established",
"Percentage of partner LGUs with approved, integrated local DRRM/CCA plans",
"Number of certified Community Resilience Advocates (CRAs) & technical trainers",
"No. of university-developed climate-smart technologies/livelihood models adopted",
"Number of partner communities with functional Early Warning System (EWS)",
"BOR Approved Extension Program/Agenda",
"Utilization rate of allocated funds for extension services (GAA)",
"Utilization rate of allocated funds for extension services (IGF)",
"Extension Outreach Activity",
]
class Command(BaseCommand):
    def handle(self,*args,**kwargs):
        for i,name in enumerate(INDICATORS,1):
            ExtensionIndicator.objects.update_or_create(order=i,defaults={"name":name,"is_percentage":name.lower().startswith("percentage")})
        self.stdout.write(self.style.SUCCESS("24 TAEP indicators seeded."))
