from django.contrib import admin
from .models import (
    UserProfile, Notification, ExtensionIndicator, TaepReport, TaepQuarterEntry,
    TaepIndicatorMeta, QparReport, QparEntry, Partnership, ExtensionPPA, ActivityLog,
)

for model in [
    UserProfile, Notification, ExtensionIndicator, TaepReport, TaepQuarterEntry,
    TaepIndicatorMeta, QparReport, QparEntry, Partnership, ExtensionPPA, ActivityLog,
]:
    admin.site.register(model)
