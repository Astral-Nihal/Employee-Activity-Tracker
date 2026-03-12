# Employee Activity Tracker

## Overview
The **Employee Activity Tracker** is a comprehensive Django-based system designed to monitor, track, and analyze employee productivity. It logs work sessions, application usage, web browsing, and idle time.

The system utilizes an AI engine to classify activities, generate daily productivity scores, evaluate burnout risks, and provide actionable insights for both employees and HR/Admin personnel.

### Key Features
* **Role-Based Access Control:** Distinct portals for Employees, HR Professionals, and System Admins.
* **Work Session & Activity Tracking:** Monitors exact start/end times and categorizes activities as Application (APP), Website (WEB), or Idle Time (IDLE).
* **AI-Powered Productivity Analysis:** Automatically classifies activities as productive or unproductive, calculates a daily productivity score, and assesses burnout risk.
* **Comprehensive Dashboards:** 
  * **Employee Dashboard:** View personal productivity trends and daily scores.
  * **HR/Admin Dashboard:** Enterprise-wide analytics, time distribution breakdowns, and advanced reporting.
* **Desktop Agent:** A standalone desktop application (`desktop_agent.py`) that captures and syncs activity logs to the main server via REST API endpoints.
* **Exportable Reports:** One-click CSV exports for individual or global organizational activity.

## Prerequisites
* Python 3.8+
* Virtual Environment setup capability

## Installation and Setup

### 1. Clone the Repository
Open your terminal or command prompt and clone the repository, then navigate into the directory:
```bash
git clone https://github.com/Astral-Nihal/Employee-Activity-Tracker.git
cd "Employee Activity Tracker"
```

### 2. Create and Activate the Virtual Environment
Create a new virtual environment to manage dependencies:
```bash
python -m venv venv
```

To activate the virtual environment:

**On Windows:**
```bash
venv\Scripts\activate
```

**On macOS / Linux** (if re-created):
```bash
source venv/bin/activate
```

### 3. Install Dependencies
Install all necessary packages, including `django`, `djangorestframework`, and other requirements by running:
```bash
pip install -r requirements.txt
```

### 4. Database Setup
Apply the Django database migrations to set up the necessary tables for Users, WorkSessions, and ActivityLogs:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create a Superuser
To access the HR dashboard and Django Admin panel, you must create an administrator account:
```bash
python manage.py createsuperuser
```
Follow the prompts to configure your username, email, and password.

### 6. Run the Server
Launch the Django development web server:
```bash
python manage.py runserver
```
Navigate to `http://127.0.0.1:8000/` in your web browser. Log in using the superuser credentials. 

*(From the Django Admin panel at `http://127.0.0.1:8000/admin/`, you can manage users and define their roles as `EMPLOYEE` or `HR`.)*

### 7. Run the Desktop Agent
The included `desktop_agent.py` script captures the user's active window/web traffic and sends the info to the tracker server. Open a separate terminal, activate the virtual environment, and run:
```bash
python desktop_agent.py
```
*(Note: A `desktop_agent.spec` file is also provided if you wish to build the agent into a standalone executable via PyInstaller.)*

## Architecture Overview
* **tracker/**: Main application containing views, models, AI engine (`ai_engine.py`), and serializers.
* **monitoringsystem/**: Core Django project settings and routing configurations.
* **desktop_agent.py**: Client-side tracker script syncing data remotely.
