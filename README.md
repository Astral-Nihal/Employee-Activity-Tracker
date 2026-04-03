# WorkAnalytics OS — Employee Activity Tracker

A full-stack Django-based workforce intelligence platform that monitors employee productivity in real time. The system pairs a web dashboard with a background desktop tracking agent that automatically captures active window usage, web browsing, and idle time — then feeds it through an AI engine to generate daily productivity scores and burnout assessments.

---

## Key Features

| Feature | Description |
|---|---|
| **Role-Based Access Control** | Three roles: `EMPLOYEE`, `HR`, and `ADMIN`. Each role gets a dedicated portal. |
| **Web-Triggered Tracking** | Tracking starts/stops automatically when an employee logs in or out of the web dashboard — no manual agent interaction needed. |
| **Silent Desktop Agent** | Lightweight background process (Windows) that monitors the active window title and detects idle time (60s threshold). |
| **Productivity Classifier** | Classifies activity as `PRODUCTIVE`, `UNPRODUCTIVE`, or `NEUTRAL` using a massive dictionary including modern AI/Dev tools (Gemini, ChatGPT, VS Code). |
| **Burnout Risk Assessment** | Monitors work duration vs. efficiency to flag `LOW`, `MEDIUM`, or `HIGH` burnout risks (e.g., >10 hours active screen time). |
| **Interactive Dashboards** | Rich visualizations using **Chart.js**, featuring productivity trends, time distribution doughnuts, and workforce activity feeds. |
| **Employee Management** | Full CRUD capabilities for HR/Admins to create, edit, or deactivate employee accounts directly from the UI. |
| **Single-Device Login** | Middleware enforcement ensures a user cannot maintain multiple active sessions concurrently. |
| **Secure API layers** | Token-based authentication for the agent and strict data validation for all incoming activity logs. |

---

## Productivity Classifier & Burnout Logic

- **Classification:** Activities are classified using a modern dictionary. Terms like *chatgpt*, *gemini*, *github*, and *vscode* are marked as `PRODUCTIVE`. Social media and gaming titles are marked as `UNPRODUCTIVE`.
- **Burnout Detection:** 
    - `HIGH`: Total screen time > 10 hours.
    - `MEDIUM`: Screen time > 8 hours with small productivity scores (< 40%).
    - `LOW`: Normal operational limits.

---

## Tech Stack

- **Backend:** Django 5.x + Django REST Framework
- **Database:** MySQL (`mysqlclient` driver)
- **Auth:** Django session auth (browser) + DRF (Django Rest Framework) Token auth (desktop agent)
- **Desktop Agent:** Pure Python (`pygetwindow`, `ctypes`, `requests`, `http.server`)
- **Frontend:** Bootstrap 5.3, Chart.js, Bootstrap Icons (CDN)

---

## Prerequisites

- Python 3.8+
- A running MySQL server instance
- Windows OS (the desktop agent uses `ctypes.windll` for idle-time detection and `pygetwindow` for window title capture)

---

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Astral-Nihal/Employee-Activity-Tracker.git
cd "Employee Activity Tracker"
```

### 2. Create & Activate a Virtual Environment

```bash
python -m venv venv
```

**Windows:**
```bash
venv\Scripts\activate
```

**macOS / Linux:**
```bash
source venv/bin/activate
```

### 3. Database Setup

Create a MySQL database before running migrations:

```sql
CREATE DATABASE monitoring_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Then open `monitoringsystem/settings.py` and update the `DATABASES` block. Notice that the default project configuration often uses port **3307**:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'monitoring_db',
        'USER': '<your_mysql_user>',
        'PASSWORD': '<your_mysql_password>',
        'HOST': 'localhost',
        'PORT': '3307',   # Update to 3306 or 3307 as per your local MySQL setup
    }
}
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Apply Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create an Administrative Account

```bash
python manage.py createsuperuser
```

After creation, log in to the Django admin panel and ensure the user's **role** is set to `HR` or `ADMIN`.

---

## Running the Application

The recommended way to start everything is with the **Unified Launcher**:

```bash
python start_app.py
```

This single command:
1. Starts the Django development server on `http://127.0.0.1:8000`
2. Waits for the server to be ready
3. Launches the desktop tracking agent (listening on port **9443**)

**Optional flags:**

```bash
python start_app.py --server   # Django server only
python start_app.py --agent    # Agent only
```

Press `Ctrl+C` to gracefully shut down both processes.

---

## How Tracking Works

```
Employee logs in → Browser dashboard loads
        │
        ├─ Server sets is_tracking = True
        ├─ Browser pings local agent (localhost:9443)
        │       (passes auth token + user ID via /agent/start)
        │
        └─ Desktop Agent wakes up:
                ├─ Opens a WorkSession (POST /api/sessions/)
                └─ Polls /api/tracking-status/ every 7 s
                        └─ If is_tracking=True → captures window → POST /api/activities/

Employee clicks Sign Out → Confirmation Modal appears
        │
        ├─ User confirms → confirmSignOut() signal fires
        ├─ Sends /agent/stop to local agent
        ├─ Agent triggers run_daily_analysis() → Server computes final score
        └─ GET /api/logout/ (Django session cleared)
```

- The agent uses **Token authentication** for API calls, remaining authenticated even if the web session expires.
- Idle time (60+ seconds) is automatically detected and logged as `IDLE` time in the distribution charts.

---

## URL Reference

| URL | Access | Description |
|---|---|---|
| `/api/login/` | All | Gateway login page |
| `/api/dashboard/my-stats/` | Employee | Personal productivity & work log |
| `/api/dashboard/export/` | Employee | Download personal history (CSV) |
| `/api/dashboard/hr/` | Admin/HR | Executive Overview (KPIs & Trends) |
| `/api/dashboard/hr/workforce/` | Admin/HR | Live workforce activity feed |
| `/api/dashboard/hr/time-distribution/` | Admin/HR | App/Website time breakdown |
| `/api/dashboard/hr/employees/` | Admin/HR | Workforce CRM (Add/Edit/Remove) |
| `/api/dashboard/hr/export-global/` | Admin/HR | Executive Report (Global CSV) |


---

## Project Structure

```
Employee Activity Tracker/
├── start_app.py              # Unified system launcher
├── desktop_agent.py          # Background Windows tracking agent
├── requirements.txt          # Python dependencies
│
├── monitoringsystem/         # Project Settings & Routing
│   ├── settings.py           
│   └── urls.py               
│
└── tracker/                  
    ├── models.py             # User, WorkSession, ActivityLog, DailySummary
    ├── backend_engine.py     # Productivity Classifier & Burnout logic
    ├── middleware.py         # Single-session device enforcement
    ├── serializers.py        # API Payload validation
    └── templates/tracker/    # Professional Bootstrap 5 Dashboards
        ├── dashboard.html            # HR Executive Overview
        ├── workforce_activity.html   # Live workforce activity feed
        ├── employee_management.html  # Workforce CRM (Add/Edit/Remove)
        ├── employee_dashboard.html   # Employee personal productivity & work log
        ├── advanced_reports.html     # Advanced reports
        ├── time_distribution.html    # App/Website time breakdown
        └── login.html                # Login page
```

---

