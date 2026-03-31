"""
Task 2: Single Device / Single Active Login Enforcement Middleware.

When a user logs into the web dashboard, this handler fires on the
`user_logged_in` signal and invalidates all previously active sessions
for that specific user in the `django_session` table.

This ensures that if an employee logs in on Device B, they are
automatically logged out of Device A.
"""
from importlib import import_module

from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.contrib.sessions.models import Session
from django.dispatch import receiver
from django.utils import timezone


@receiver(user_logged_in)
def enforce_single_session(sender, request, user, **kwargs):
    """
    Called every time a user successfully logs in via the web dashboard
    (via Django's session-based authentication).

    Iterates through all existing, non-expired sessions and deletes any
    session that belongs to this user — except the brand-new one that
    was just created for this login.
    """
    # The session key that was just created for this new login
    current_session_key = request.session.session_key

    # Load the session engine (default: django.contrib.sessions.backends.db)
    engine = import_module(settings.SESSION_ENGINE)

    # Fetch all sessions that have not expired yet
    active_sessions = Session.objects.filter(expire_date__gt=timezone.now())

    for session in active_sessions:
        # Skip the current session we just created
        if session.session_key == current_session_key:
            continue

        try:
            # Decode the session data to inspect the authenticated user id
            session_data = session.get_decoded()
            session_user_id = session_data.get('_auth_user_id')
            if session_user_id and int(session_user_id) == user.pk:
                # This session belongs to our user on another device — destroy it
                session.delete()
        except Exception:
            # Corrupted/unreadable session; skip gracefully
            continue


class SingleSessionMiddleware:
    """
    A passthrough middleware required to register the app in MIDDLEWARE
    so that the `user_logged_in` signal receiver above is imported and
    connected at startup.

    The actual session enforcement happens via the signal, not process_request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)
