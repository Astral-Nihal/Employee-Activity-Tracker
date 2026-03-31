"""
WorkAnalytics OS — Desktop Tracking Agent
==========================================
Task 1: Dynamic authentication — prompts for credentials on startup,
fetches USER_ID and TOKEN from /api/agent-login/, then tracks activity.
On graceful exit (Ctrl+C), sends a logout request to /api/agent-logout/
to close the WorkSession and trigger AI analysis.
"""

import time
import getpass
import requests
import pygetwindow as gw
import ctypes
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
BASE_URL = "http://127.0.0.1:8000/api/"
API_URL_SESSIONS   = f"{BASE_URL}sessions/"
API_URL_ACTIVITIES = f"{BASE_URL}activities/"
API_URL_LOGIN      = f"{BASE_URL}agent-login/"
API_URL_LOGOUT     = f"{BASE_URL}agent-logout/"
API_URL_ANALYZE    = f"{BASE_URL}analyze/"

# Runtime state (populated after login)
USER_ID    = None
AUTH_TOKEN = None

# Advanced Tracking Config
IDLE_THRESHOLD_SECONDS = 60   # Mark as "Idle" after 60 s of no mouse/keyboard input


# ---------------------------------------------------------------------------
# WINDOWS IDLE TIME DETECTION
# ---------------------------------------------------------------------------
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint),
                ("dwTime", ctypes.c_uint)]


def get_idle_time_seconds():
    """Returns seconds since the last mouse/keyboard input (Windows only)."""
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
    return 0


def get_active_window_title():
    try:
        window = gw.getActiveWindow()
        if window:
            return window.title
    except Exception:
        pass
    return "Unknown"


# ---------------------------------------------------------------------------
# TASK 1 — AUTHENTICATION
# ---------------------------------------------------------------------------
def agent_authenticate():
    """
    Prompts the employee for credentials and exchanges them for a user_id
    and auth token from the Django backend.
    Retries on failure until successful.
    """
    global USER_ID, AUTH_TOKEN

    print("=" * 52)
    print("   WorkAnalytics OS — Desktop Tracking Agent")
    print("=" * 52)
    print()

    while True:
        username = input("  Username : ").strip()
        password = getpass.getpass("  Password : ").strip()

        if not username or not password:
            print("  ⚠️  Username and password cannot be empty.\n")
            continue

        print()
        try:
            resp = requests.post(
                API_URL_LOGIN,
                json={"username": username, "password": password},
                timeout=10,
            )
        except requests.exceptions.ConnectionError:
            print("  ❌ Cannot reach server. Make sure Django is running.\n")
            retry = input("  Retry? (y/n): ").strip().lower()
            if retry != 'y':
                raise SystemExit(0)
            print()
            continue

        if resp.status_code == 200:
            data = resp.json()
            USER_ID    = data["user_id"]
            AUTH_TOKEN = data["token"]
            role       = data.get("role", "EMPLOYEE")
            print(f"  ✅ Logged in as: {username}  (Role: {role})")
            print(f"  🆔 User ID: {USER_ID}")
            print("=" * 52)
            print()
            return
        elif resp.status_code == 401:
            print("  ❌ Invalid credentials. Please try again.\n")
        elif resp.status_code == 403:
            print("  🚫 Your account is deactivated. Contact HR.\n")
            raise SystemExit(1)
        else:
            print(f"  ⚠️  Server error ({resp.status_code}): {resp.text}\n")


def _auth_headers():
    """Returns the Authorization header dict for all API calls."""
    return {"Authorization": f"Token {AUTH_TOKEN}"}


# ---------------------------------------------------------------------------
# WORK SESSION MANAGEMENT
# ---------------------------------------------------------------------------
def create_work_session():
    """Creates a new WorkSession on the server. Retries every 5 s if offline."""
    print(f"  Connecting to server for User ID: {USER_ID}...")
    data = {"user": USER_ID}

    while True:
        try:
            response = requests.post(
                API_URL_SESSIONS,
                json=data,
                headers=_auth_headers(),
                timeout=5,
            )
            if response.status_code == 201:
                session_id = response.json()['id']
                print(f"  🟢 Session started! Session ID: {session_id}")
                print(f"  📡 Tracking... (Press Ctrl+C to stop and log out)\n")
                return session_id
            else:
                print(f"  ⚠️  Server error ({response.status_code}): {response.text}")
        except requests.exceptions.RequestException:
            print("  ❌ Server offline. Retrying in 5 seconds...")

        time.sleep(5)


def agent_logout(session_id):
    """
    Graceful shutdown:
    1. Closes the WorkSession (stamps end_time).
    2. Triggers AI analysis.
    3. Invalidates the auth token on the server.
    """
    global AUTH_TOKEN

    print("\n  🔌 Logging out...")

    # Step 1 — Close the WorkSession via the logout endpoint
    try:
        resp = requests.post(
            API_URL_LOGOUT,
            json={"token": AUTH_TOKEN, "session_id": session_id},
            headers=_auth_headers(),
            timeout=5,
        )
        if resp.status_code == 200:
            print(f"  ✅ {resp.json().get('message', 'Session closed.')}")
        else:
            print(f"  ⚠️  Logout warning: {resp.text}")
    except Exception:
        print("  ⚠️  Could not reach server to close session.")

    # Step 2 — Trigger AI analysis for today's data
    try:
        print("  🤖 Triggering AI analysis...")
        res = requests.post(
            API_URL_ANALYZE,
            json={"user_id": USER_ID},
            headers=_auth_headers(),
            timeout=10,
        )
        if res.status_code == 200:
            print("  📊 Analysis complete. Check your dashboard for results.")
        else:
            print(f"  ⚠️  AI analysis failed: {res.text}")
    except Exception:
        print("  ⚠️  Could not trigger AI analysis (server may be offline).")

    print("  👋 Goodbye!\n")


# ---------------------------------------------------------------------------
# ACTIVITY LOGGING
# ---------------------------------------------------------------------------
def send_activity_log(session_id, activity_name, start_time, end_time):
    """Sends a single activity window log to the server."""
    duration = int((end_time - start_time).total_seconds())
    if duration < 1:
        return  # Skip sub-second accidental clicks

    activity_type = 'APP'
    if activity_name == "Idle":
        activity_type = 'IDLE'
    else:
        browser_keywords = ['chrome', 'edge', 'firefox', 'brave', 'mozilla']
        if any(kw in activity_name.lower() for kw in browser_keywords):
            activity_type = 'WEB'

    data = {
        "user": USER_ID,
        "session": session_id,
        "activity_type": activity_type,
        "activity_name": activity_name[:255],
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration,
    }

    try:
        response = requests.post(
            API_URL_ACTIVITIES,
            json=data,
            headers=_auth_headers(),
            timeout=5,
        )
        if response.status_code == 201:
            print(f"  📌 Logged [{activity_type}]: {activity_name[:45]}... ({duration}s)")
        else:
            print(f"  ⚠️  Failed to send log. Error: {response.text}")
    except Exception:
        print("  ⚠️  Failed to connect to server while sending activity log.")


# ---------------------------------------------------------------------------
# MAIN TRACKING LOOP
# ---------------------------------------------------------------------------
def main():
    # Step 1 — Authenticate and fetch USER_ID + TOKEN dynamically
    agent_authenticate()

    # Step 2 — Create a tracked WorkSession on the server
    session_id = create_work_session()

    # Step 3 — Begin monitoring loop
    current_state = get_active_window_title()
    start_time    = datetime.now(timezone.utc)

    try:
        while True:
            time.sleep(2)

            # Determine physical state: Idle vs Active Window
            idle_sec = get_idle_time_seconds()
            if idle_sec >= IDLE_THRESHOLD_SECONDS:
                new_state = "Idle"
            else:
                new_state = get_active_window_title()

            current_time = datetime.now(timezone.utc)

            # Log ONLY when the state changes (window switch or went Idle)
            if new_state != current_state:
                if current_state and current_state != "Unknown":
                    send_activity_log(session_id, current_state, start_time, current_time)

                current_state = new_state
                start_time    = current_time

    except KeyboardInterrupt:
        # Flush the final window state before logging out
        end_time = datetime.now(timezone.utc)
        if current_state and current_state != "Unknown":
            send_activity_log(session_id, current_state, start_time, end_time)

        # Step 4 — Graceful logout (closes session + triggers AI analysis)
        agent_logout(session_id)


if __name__ == "__main__":
    main()