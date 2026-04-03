from django.contrib import admin
from .models import User, WorkSession, ActivityLog, DailySummary, TrackingStatus

admin.site.register(User)
admin.site.register(WorkSession)
admin.site.register(ActivityLog)
admin.site.register(DailySummary)
admin.site.register(TrackingStatus)