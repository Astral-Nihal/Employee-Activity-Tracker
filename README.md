# WorkAnalytics OS — Employee Activity Tracker

A full-stack Django-based workforce intelligence platform that monitors employee productivity in real time. The system pairs a web dashboard with a background desktop tracking agent that automatically captures active window usage, web browsing, and idle time — then feeds it through an AI engine to generate daily productivity scores and burnout assessments.

---

## Key Features

| Feature | Description |
|---|---|
| **Role-Based Access Control** | Three roles: `EMPLOYEE`, `HR`, and `ADMIN`. Each role gets a dedicated portal. |
| **Web-Triggered Tracking** | Tracking starts/stops automatically when an employee logs in or out of the web dashboard — no manual agent interaction needed. |
| **Desktop Tracking Agent** | Runs silently in the background, captures the active window title every 7 seconds, and posts `ActivityLog` records to the server. |
| **Token-Based Agent Auth** | The desktop agent authenticates with a persistent DRF token, separate from the browser session. |
| **Single-Device Login Enforcement** | Logging in on a new device automatically invalidates all previous sessions for that user. |
| **AI Productivity Engine** | Classifies each recorded activity as `PRODUCTIVE`, `UNPRODUCTIVE`, or `NEUTRAL` using a keyword dictionary. Calculates a daily productivity score (0–100%) and burnout risk (`LOW` / `MEDIUM` / `HIGH`). |
| **Employee Dashboard** | Personal productivity trend chart (last 7 days), detailed work log table, and CSV export. |
| **HR / Admin Dashboards** | Enterprise KPI overview, workforce activity feed, time distribution charts, advanced reports, and global CSV export. |
| **Employee Management (CRUD)** | HR/Admins can create, edit, deactivate, and reactivate employee accounts directly from the web UI. |
| **Secure Serializers** | All API payloads from the desktop agent are validated (field-length limits, NULL-byte rejection, cross-field consistency checks). |

---

## Tech Stack

- **Backend:** Django 5.x + Django REST Framework
- **Database:** MySQL (`mysqlclient` driver)
- **Auth:** Django session auth (browser) + DRF Token auth (desktop agent)
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

Then open `monitoringsystem/settings.py` and update the `DATABASES` block with your own MySQL credentials:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'monitoring_db',
        'USER': '<your_mysql_user>',
        'PASSWORD': '<your_mysql_password>',
        'HOST': 'localhost',
        'PORT': '<your_mysql_port>',   # default MySQL port is 3306
    }
}
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` includes: `Django`, `djangorestframework`, `requests`, `pygetwindow`, `mysqlclient`.

### 5. Apply Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create an HR / Admin Account

```bash
python manage.py createsuperuser
```

After creation, log in to the Django admin panel at `http://127.0.0.1:8000/admin/` and set the user's **role** to `HR` or `ADMIN` to grant access to the HR dashboards. Alternatively, use the Employee Management panel in the web UI once logged in as admin.

---

## Running the Application

The recommended way to start everything is with the **Unified Launcher**:

```bash
python start_app.py
```

This single command:
1. Starts the Django development server on `http://127.0.0.1:8000`
2. Waits for the server to be ready
3. Launches the desktop tracking agent in the background

**Optional flags:**

```bash
python start_app.py --server   # Django server only (no agent)
python start_app.py --agent    # Agent only (server already running)
```

Press `Ctrl+C` to gracefully shut down both processes.

> You can also run them separately:
> ```bash
> python manage.py runserver --noreload   # Terminal 1
> python desktop_agent.py                 # Terminal 2
> ```

---

## How Tracking Works

```
Employee logs in → Browser dashboard loads
        │
        ├─ Server sets is_tracking = True
        ├─ Browser contacts the local desktop agent
        │       (passes auth token + user ID)
        │
        └─ Desktop Agent wakes up:
                ├─ Opens a WorkSession (POST /api/sessions/)
                └─ Polls /api/tracking-status/ every 7 s
                        └─ If is_tracking=True → captures active window → POST /api/activities/

Employee clicks Sign Out → confirmSignOut() fires
        ├─ POST /api/toggle-tracking/  (sets is_tracking = False)
        ├─ Signals the local agent to sleep
        └─ GET /api/logout/ (Django session cleared)
```

- The agent uses **Token authentication** for all API calls so it remains authenticated even if the browser session expires.
- On sign-out, a background thread briefly waits before running `run_daily_analysis()` so the agent has time to flush its last activity window.

---

## URL Reference

| URL | Role | Description |
|---|---|---|
| `/api/login/` | All | Login page |
| `/api/logout/` | All | Logout |
| `/api/dashboard/route/` | All | Redirects to correct dashboard based on role |
| `/api/dashboard/my-stats/` | Employee | Personal productivity dashboard |
| `/api/dashboard/export/` | Employee | Download personal CSV report |
| `/api/dashboard/hr/` | HR/Admin | Executive KPI overview |
| `/api/dashboard/hr/workforce/` | HR/Admin | Live workforce activity feed |
| `/api/dashboard/hr/time-distribution/` | HR/Admin | App & category time breakdown |
| `/api/dashboard/hr/reports/` | HR/Admin | Advanced reports |
| `/api/dashboard/hr/employees/` | HR/Admin | Employee management (CRUD) |
| `/api/dashboard/hr/export-global/` | HR/Admin | Download global CSV report |
| `/admin/` | Superuser | Django admin panel |

---

## Project Structure

```
Employee Activity Tracker/
├── manage.py
├── start_app.py              # Unified launcher (Django + Agent)
├── desktop_agent.py          # Background tracking agent (Windows)
├── desktop_agent.spec        # PyInstaller spec (optional standalone build)
├── requirements.txt
│
├── monitoringsystem/         # Django project config
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
└── tracker/                  # Main application
    ├── models.py             # User, WorkSession, ActivityLog, DailySummary, TrackingStatus
    ├── views.py              # All views: dashboards, API endpoints, CRUD
    ├── urls.py               # URL routing for the tracker app
    ├── serializers.py        # DRF serializers with strict input validation
    ├── backend_engine.py     # AI classification & daily productivity analysis
    ├── middleware.py         # SingleSessionMiddleware (single-device login)
    ├── admin.py              # Django admin registrations
    ├── apps.py
    ├── templatetags/
    │   └── tracker_extras.py # Custom template filters (e.g. smart_hours)
    └── templates/tracker/
        ├── login.html
        ├── employee_dashboard.html
        ├── dashboard.html            # HR executive overview
        ├── workforce_activity.html
        ├── time_distribution.html
        ├── advanced_reports.html
        └── employee_management.html
```

---

## Data Models

| Model | Description |
|---|---|
| `User` | Extends `AbstractUser` with a `role` field (`EMPLOYEE`, `HR`, `ADMIN`) |
| `WorkSession` | One record per login session; stores `start_time` and `end_time` |
| `ActivityLog` | One record per window/idle window; stores `activity_name`, `activity_type`, `duration_seconds` |
| `DailySummary` | AI-computed daily rollup: `productivity_score`, `burnout_risk`, `focus_pattern_notes` |
| `TrackingStatus` | One-to-one with User; `is_tracking` flag read by the desktop agent on every poll |
