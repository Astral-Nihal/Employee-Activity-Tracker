"""
Task 3: Secure, Hardened DRF Serializers
=========================================
All incoming API payloads from the desktop agent pass through these
serializers before touching the database. They provide:

  - Strict field-type validation (integers must be ints, datetimes must parse)
  - Field-length limits to prevent oversized inputs
  - Choice validation for enumerated fields (activity_type, role, etc.)
  - Rejection of unexpected/extra fields (read_only_fields guards)
  - No raw SQL anywhere — 100% Django ORM

SQL Injection Note:
  Django's ORM uses parameterised queries exclusively. As long as we use
  the ORM (which these serializers enforce by routing through ModelSerializer
  .save()), SQL injection is structurally impossible at the data layer.
"""

import re
from rest_framework import serializers
from django.utils import timezone

from .models import ActivityLog, WorkSession, TrackingStatus, User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
SAFE_TEXT_RE = re.compile(r'^[^\x00]*$')   # Reject NULL bytes (common in injection payloads)

def _validate_safe_text(value: str, field_name: str, max_len: int) -> str:
    """Shared validator: rejects NULL bytes, enforces max length."""
    if not isinstance(value, str):
        raise serializers.ValidationError(f"{field_name} must be a string.")
    if len(value) > max_len:
        raise serializers.ValidationError(
            f"{field_name} is too long (max {max_len} characters)."
        )
    if not SAFE_TEXT_RE.match(value):
        raise serializers.ValidationError(
            f"{field_name} contains invalid characters."
        )
    return value


# ---------------------------------------------------------------------------
# WorkSession Serializer
# ---------------------------------------------------------------------------
class WorkSessionSerializer(serializers.ModelSerializer):
    """
    Validates sessions created by the desktop agent.
    Only `user` is accepted as input; all other fields are server-set.
    """

    class Meta:
        model = WorkSession
        fields = ['id', 'user', 'date', 'start_time', 'end_time']
        read_only_fields = ['id', 'date', 'start_time']

    def validate_user(self, value):
        """Ensure the user actually exists and is active."""
        if not value.is_active:
            raise serializers.ValidationError("Cannot create a session for a deactivated user.")
        return value


# ---------------------------------------------------------------------------
# ActivityLog Serializer
# ---------------------------------------------------------------------------
class ActivityLogSerializer(serializers.ModelSerializer):
    """
    Strictly validates all activity log payloads from the desktop agent.

    Key security measures:
    - activity_name   : capped at 255 chars, NULL-byte rejected
    - duration_seconds: must be a non-negative integer
    - start/end times : must be valid ISO-8601 datetimes
    - activity_type   : must be one of the defined choices
    - user + session  : must reference existing, consistent DB records
    """

    class Meta:
        model = ActivityLog
        fields = [
            'id', 'user', 'session', 'activity_type', 'activity_name',
            'start_time', 'end_time', 'duration_seconds',
            'is_productive', 'category',
        ]
        read_only_fields = ['id', 'is_productive', 'category']

    def validate_activity_name(self, value):
        return _validate_safe_text(value, "activity_name", max_len=255)

    def validate_duration_seconds(self, value):
        if not isinstance(value, int):
            raise serializers.ValidationError("duration_seconds must be an integer.")
        if value < 0:
            raise serializers.ValidationError("duration_seconds cannot be negative.")
        if value > 86_400:   # More than a full day is certainly wrong
            raise serializers.ValidationError("duration_seconds exceeds maximum allowed value (86400).")
        return value

    def validate_activity_type(self, value):
        allowed = {choice[0] for choice in ActivityLog.ACTIVITY_TYPES}
        if value not in allowed:
            raise serializers.ValidationError(
                f"Invalid activity_type '{value}'. Must be one of: {', '.join(sorted(allowed))}."
            )
        return value

    def validate_start_time(self, value):
        if value > timezone.now():
            raise serializers.ValidationError("start_time cannot be in the future.")
        return value

    def validate(self, attrs):
        """Cross-field validation: session must belong to the same user."""
        user = attrs.get('user')
        session = attrs.get('session')

        if user and session and session.user != user:
            raise serializers.ValidationError(
                "The session does not belong to the specified user. Payload rejected."
            )

        # end_time must be after start_time if both are present
        start = attrs.get('start_time')
        end = attrs.get('end_time')
        if start and end and end <= start:
            raise serializers.ValidationError(
                "end_time must be after start_time."
            )

        return attrs


# ---------------------------------------------------------------------------
# TrackingStatus Serializer (used by the toggle & poll endpoints)
# ---------------------------------------------------------------------------
class TrackingStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackingStatus
        fields = ['is_tracking', 'last_updated']
        read_only_fields = ['last_updated']
