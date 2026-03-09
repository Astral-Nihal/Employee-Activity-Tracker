import time
import requests
import pygetwindow as gw
import ctypes
from datetime import datetime, timezone

# --- CONFIGURATION ---
BASE_URL = "http://127.0.0.1:8000/api/"
API_URL_SESSIONS = f"{BASE_URL}sessions/"
API_URL_ACTIVITIES = f"{BASE_URL}activities/"
USER_ID = 1  

# --- NEW: ADVANCED TRACKING CONFIG ---
IDLE_THRESHOLD_SECONDS = 60  # Mark as "Idle" after 60 seconds of no mouse/keyboard input

# Windows Structure for Idle Tracking
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint),
                ("dwTime", ctypes.c_uint)]

def get_idle_time_seconds():
    """Returns the number of seconds since the last mouse/keyboard input."""
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        # Calculate time since last input in milliseconds, then convert to seconds
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

def create_work_session():
    """Attempts to connect to the server. Retries every 5 seconds if offline."""
    print("Connecting to server...")
    data = {"user": USER_ID}
    
    while True:
        try:
            response = requests.post(API_URL_SESSIONS, json=data, timeout=5)
            if response.status_code == 201:
                session_id = response.json()['id']
                print(f"✅ Connection Established! Session ID: {session_id}")
                return session_id
            else:
                print(f"⚠️ Server error ({response.status_code}). Retrying...")
        except requests.exceptions.RequestException:
            print("❌ Server offline. Retrying in 5 seconds... (Please run 'python manage.py runserver')")
        
        time.sleep(5)

def send_activity_log(session_id, activity_name, start_time, end_time):
    duration = int((end_time - start_time).total_seconds())
    if duration < 1: return # Don't log accidental millisecond clicks

    # Determine the type of activity
    activity_type = 'APP'
    if activity_name == "Idle":
        activity_type = 'IDLE'
    else:
        browser_keywords = ['chrome', 'edge', 'firefox', 'brave', 'mozilla']
        if any(browser in activity_name.lower() for browser in browser_keywords):
            activity_type = 'WEB'
        
    data = {
        "user": USER_ID,
        "session": session_id,
        "activity_type": activity_type,
        "activity_name": activity_name[:255],
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration
    }
    
    try:
        requests.post(API_URL_ACTIVITIES, json=data, timeout=5)
        print(f"Logged: {activity_name[:40]}... ({duration}s)")
    except Exception:
        print(f"⚠️ Failed to send log. Check server connection.")

def main():
    print("--- AI Monitoring Agent (Press Ctrl+C to Exit) ---")
    
    session_id = create_work_session()

    current_state = get_active_window_title()
    start_time = datetime.now(timezone.utc)
    
    try:
        while True:
            time.sleep(2)
            
            # 1. Determine the user's current physical state (Idle vs Active)
            idle_sec = get_idle_time_seconds()
            if idle_sec >= IDLE_THRESHOLD_SECONDS:
                new_state = "Idle"
            else:
                new_state = get_active_window_title()
                
            current_time = datetime.now(timezone.utc)
            
            # 2. Trigger a log ONLY IF the state changed (Window switch or went Idle)
            if new_state != current_state:
                if current_state and current_state != "Unknown":
                    send_activity_log(session_id, current_state, start_time, current_time)
                
                # Reset trackers for the new state
                current_state = new_state
                start_time = current_time
                
    except KeyboardInterrupt:
        print("\nStopping tracker...")
        end_time = datetime.now(timezone.utc)
        if current_state and current_state != "Unknown":
            send_activity_log(session_id, current_state, start_time, end_time)
        
        # Trigger AI Analysis on exit
        try:
            print("Triggering AI Analysis...")
            requests.post(f"{BASE_URL}analyze/", json={"user_id": USER_ID}, timeout=5)
            print("📊 Analysis Complete. View dashboard for results.")
        except:
            pass

if __name__ == "__main__":
    main()