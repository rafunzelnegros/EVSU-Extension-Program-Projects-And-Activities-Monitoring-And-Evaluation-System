from django.contrib import admin
from .models import *
for model in [Unit,UserProfile,PPA,SustainableDevelopmentGoal,Activity,ImpactAssessment,ExtensionIndicator,QparSubmission,QparIndicatorValue,QuarterlyMonitoringReport,FieldVisitLog,FieldVisitEntry,ActivityLog]:
    admin.site.register(model)
