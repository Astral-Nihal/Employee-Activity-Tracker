from django.db import models
from django.contrib.auth.models import AbstractUser


# 1. User Authentication Module (Role-based access)
class User(AbstractUser):
    ROLE_CHOICES = (
        ('EMPLOYEE', 'Employee'),
        ('HR', 'HR Professional'),
        ('ADMIN', 'System Admin'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='EMPLOYEE')

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


# 2. Work Session Tracking
class WorkSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    date = models.DateField(auto_now_add=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.date}"


# 3. Activity Tracking Module (App, Web, Idle)
class ActivityLog(models.Model):
    ACTIVITY_TYPES = (
        ('APP', 'Application'),
        ('WEB', 'Website'),
        ('IDLE', 'Idle Time'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session = models.ForeignKey(WorkSession, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=4, choices=ACTIVITY_TYPES)
    activity_name = models.CharField(max_length=255)  # e.g., "Google Chrome", "facebook.com"
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)

    # AI Module will update these fields later
    is_productive = models.BooleanField(null=True, blank=True)
    category = models.CharField(max_length=50, null=True, blank=True)  # e.g., "Work", "Social Media"

    def __str__(self):
        return f"{self.user.username} - {self.activity_name} ({self.duration_seconds}s)"


# 4. Smart Reporting & Productivity Evaluation
class DailySummary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    total_working_hours = models.FloatField(default=0.0)
    productive_hours = models.FloatField(default=0.0)
    idle_hours = models.FloatField(default=0.0)

    # AI Engine Outputs
    productivity_score = models.FloatField(default=0.0)
    burnout_risk = models.CharField(max_length=20, default='LOW')  # LOW, MEDIUM, HIGH
    focus_pattern_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.date} - Score: {self.productivity_score}"


# 5. Task 1: Web-Triggered Tracking State
class TrackingStatus(models.Model):
    """
    One-to-one record per user that tracks whether the desktop agent
    should be actively logging windows or sleeping.

    The agent polls /api/tracking-status/ and checks `is_tracking`.
    The employee flips this flag via the Start/Stop button on their dashboard.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='tracking_status')
    is_tracking = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        status = "TRACKING" if self.is_tracking else "IDLE"
        return f"{self.user.username} — {status}"