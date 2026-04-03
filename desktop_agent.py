"""
WorkAnalytics OS — Desktop Tracking Agent (v2 — Web-Triggered Mode)
====================================================================
Task 1/2: The agent now runs as a SILENT background process without CLI prompts.
- Starts in a DORMANT state, listening on localhost:9443.
- When the user logs in via the web, the JS sends a ping to `/agent/start` with an auth token.
- Agent wakes up, establishes a WorkSession, and polls the tracking toggle.
- When the user logs out, the JS sends a ping to `/agent/stop`, agent sleeps again.
"""

import time
import requests
import pygetwindow as gw
import ctypes
import threading
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
BASE_URL            = "http://127.0.0.1:8000/api/"
API_URL_SESSIONS    = f"{BASE_URL}sessions/"
API_URL_ACTIVITIES  = f"{BASE_URL}activities/"
API_URL_LOGOUT      = f"{BASE_URL}agent-logout/"
API_URL_ANALYZE     = f"{BASE_URL}analyze/"
API_URL_STATUS      = f"{BASE_URL}tracking-status/"

POLL_INTERVAL           = 7    # seconds between status polls / window checks
IDLE_THRESHOLD_SECONDS  = 60   # mark as Idle after 60 s of no input

# Runtime state (populated by web dashboard handshake)
USER_ID    = None
AUTH_TOKEN = None
SESSION_ID = None


# ---------------------------------------------------------------------------
# WINDOWS IDLE TIME DETECTION
# ---------------------------------------------------------------------------
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_idle_time_seconds():
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        return (ctypes.windll.kernel32.GetTickCount() - lii.dwTime) / 1000.0
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
# API HELPERS
# ---------------------------------------------------------------------------
def _headers():
    return {"Authorization": f"Token {AUTH_TOKEN}"}


def create_work_session():
    global SESSION_ID
    try:
        resp = requests.post(
            API_URL_SESSIONS,
            json={"user": USER_ID},
            headers=_headers(),
            timeout=5,
        )
        if resp.status_code == 201:
            SESSION_ID = resp.json()['id']
            print(f"  🟢 Work session opened (ID: {SESSION_ID})")
            return SESSION_ID
        else:
            print(f"  ⚠️  Session error: {resp.text}")
    except requests.exceptions.RequestException:
        print("  ❌ Server offline — session creation failed.")
    return None


def close_session_and_logout():
    global SESSION_ID, USER_ID, AUTH_TOKEN
    
    if not AUTH_TOKEN or not SESSION_ID:
        return

    print("\n  🔌 Intercepted STOP signal. Putting agent to sleep...")
    try:
        requests.post(
            API_URL_LOGOUT,
            json={"token": AUTH_TOKEN, "session_id": SESSION_ID},
            headers=_headers(),
            timeout=5,
        )
    except Exception:
        print("  ⚠️  Could not reach server to close session.")

    try:
        res = requests.post(
            API_URL_ANALYZE,
            json={"user_id": USER_ID},
            headers=_headers(),
            timeout=10,
        )
        if res.ok:
            print("  📊 AI analysis triggered.")
    except Exception:
        pass

    SESSION_ID = None
    USER_ID = None
    AUTH_TOKEN = None
    print("  💤 Agent is dormant. Waiting for next web login...")


def send_activity_log(session_id, activity_name, start_time, end_time):
    if not session_id:
        return  # Guard: no session open yet
    duration = int((end_time - start_time).total_seconds())
    if duration < 1:
        return

    activity_type = 'APP'
    if activity_name == "Idle":
        activity_type = 'IDLE'
    elif any(kw in activity_name.lower() for kw in ['chrome', 'edge', 'firefox', 'brave', 'mozilla']):
        activity_type = 'WEB'

    try:
        requests.post(
            API_URL_ACTIVITIES,
            json={
                "user": USER_ID,
                "session": session_id,
                "activity_type": activity_type,
                "activity_name": activity_name[:255],
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
            },
            headers=_headers(),
            timeout=5,
        )
    except Exception:
        pass   # Silent — background agent shouldn't spam the terminal


def is_tracking_active():
    """Polls the server using the injected web dashboard auth token"""
    try:
        resp = requests.get(API_URL_STATUS, headers=_headers(), timeout=5)
        if resp.status_code == 200:
            return resp.json().get('is_tracking', False)
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# LOCAL HTTP DAEMON (Wakeup / Sleep Listener)
# ---------------------------------------------------------------------------
class AgentRequestHandler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self.send_cors_headers()

    def do_POST(self):
        global USER_ID, AUTH_TOKEN
        
        path = self.path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        
        try:
            data = json.loads(body.decode('utf-8'))
        except:
            data = {}

        if path == '/agent/start':
            # Receive login token directly from user's browser
            USER_ID = data.get('user_id')
            AUTH_TOKEN = data.get('token')
            if USER_ID and AUTH_TOKEN:
                print(f"\n  ✅ Agent WOKEN UP by web browser. Employee ID: {USER_ID}")
                create_work_session()
            self.send_cors_headers()
            self.wfile.write(b'{"status": "started"}')
            
        elif path == '/agent/stop':
            # Put to sleep when browser logs out
            close_session_and_logout()
            self.send_cors_headers()
            self.wfile.write(b'{"status": "stopped"}')
            
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Keep the background listener completely silent
        pass


def start_local_server():
    server = HTTPServer(('127.0.0.1', 9443), AgentRequestHandler)
    print("  🌐 Background listener running on port 9443...")
    server.serve_forever()


# ---------------------------------------------------------------------------
# MAIN POLLING LOOP
# ---------------------------------------------------------------------------
def main():
    print("=" * 55)
    print("   WorkAnalytics OS — Tracking Agent v2 (Web-Triggered)")
    print("=" * 55)
    print("  💤 Starting in DORMANT state.")
    print("  💡 Awaiting login from the web dashboard to wake up...")
    print("=" * 55 + "\n")

    # Start the local listener in the background
    t = threading.Thread(target=start_local_server, daemon=True)
    t.start()

    current_state   = None
    start_time      = None
    tracking_active = False

    try:
        while True:
            # Task 1: DORMANT STATE (Fast Sleep)
            if AUTH_TOKEN is None:
                time.sleep(1)
                continue

            # Task 2/3: AGENT IS AWAKE (Normal polling cycle)
            new_tracking = is_tracking_active()

            # ── Tracking just turned ON ──────────────────────────────────
            if new_tracking and not tracking_active:
                print("  ▶️  Tracking STARTED (enabled via dashboard)")
                current_state = get_active_window_title()
                start_time    = datetime.now(timezone.utc)
                tracking_active = True

            # ── Tracking just turned OFF ─────────────────────────────────
            elif not new_tracking and tracking_active:
                print("  ⏹️  Tracking PAUSED (disabled via dashboard)")
                if current_state and current_state != "Unknown" and start_time:
                    send_activity_log(
                        SESSION_ID, current_state,
                        start_time, datetime.now(timezone.utc)
                    )
                current_state   = None
                start_time      = None
                tracking_active = False

            # ── Currently tracking — monitor window changes ───────────────
            elif tracking_active:
                idle_sec  = get_idle_time_seconds()
                new_state = "Idle" if idle_sec >= IDLE_THRESHOLD_SECONDS else get_active_window_title()
                now       = datetime.now(timezone.utc)

                if new_state != current_state:
                    if current_state and current_state != "Unknown":
                        send_activity_log(SESSION_ID, current_state, start_time, now)
                    current_state = new_state
                    start_time    = now

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        if tracking_active and current_state and current_state != "Unknown":
            send_activity_log(
                SESSION_ID, current_state,
                start_time, datetime.now(timezone.utc)
            )
        close_session_and_logout()
        print("\n  ❌ Process terminated.")


if __name__ == "__main__":
    main()