# Employee Activity Tracker: Module Implementation Details

This document maps the architectural modules mentioned in the system overview to the specific libraries, methods, and source code files used in the implementation.

---

### 1. User Authentication Module
**Description**: Handles secure login/logout and manages role-based access for Employees, Admins, and HR personnel.

*   **Libraries & Frameworks**:
    *   `Django Auth`: Built-in authentication system.
    *   `django.contrib.auth`: For user management and permissions.
*   **Key Components/Methods**:
    *   `LoginView`, `LogoutView`: For handling session starts and ends.
    *   `User` Model: Custom or standard Django user for role assignment.
    *   `request.user`: Used in templates to verify identity and role (Admin/HR).
*   **Source Files**:
    *   `tracker/templates/tracker/login.html`
    *   `monitoringsystem/settings.py` (Authentication middle-ware and backends)

---

### 2. Activity Tracking Module
**Description**: Responsible for continuous monitoring of software application usage, web browsing, active working time, and idle duration.

*   **Libraries & Frameworks**:
    *   `pygetwindow`: To capture the title of the currently focused window on the desktop.
    *   `ctypes` (Win32 API): To monitor system-wide idle time via `GetLastInputInfo`.
    *   `requests`: To transmit activity logs from the desktop agent to the central server.
*   **Key Components/Methods**:
    *   `get_active_window_title()`: Captures application context.
    *   `get_idle_time_seconds()`: Detects inactivity when the user is away from the keyboard/mouse.
    *   `send_activity_log()`: Formats and sends data to the `/api/activities/` endpoint.
*   **Source Files**:
    *   `desktop_agent.py` (The main client-side agent)

---

### 3. AI Analysis Module
**Description**: The intelligent core that classifies tasks (productive vs. non-productive), computes productivity scores, identifies focus trends, and detects potential burnout risks.

*   **Libraries & Frameworks**:
    *   `Django ORM`: For querying historical activity logs.
    *   `django.utils.timezone`: For time-aware data processing.
*   **Key Components/Methods**:
    *   `classify_activity(activity_name)`: A core logic function that uses an extensive keyword dictionary (including AI, Development, and Office tools) to categorize work.
    *   `run_daily_analysis(user_id)`: The primary engine that processes raw logs into actionable intelligence.
    *   **Burnout Detection Logic**: Implemented within the analysis engine to flag high-risk patterns (e.g., >10 hours of work or low productivity over long periods).
*   **Source Files**:
    *   `tracker/backend_engine.py`

---

### 4. Productivity Evaluation Module
**Description**: Analyzes daily performance and calculates work efficiency, plotting weekly and monthly trends.

*   **Libraries & Frameworks**:
    *   `Django ORM`: Aggregates hourly and daily data points.
*   **Key Components/Methods**:
    *   **Productivity Score Calculation**: Logic: `(Productive Seconds / Total Seconds) * 100`.
    *   `productive_hours`: Aggregated sum of duration for logs classified as 'PRODUCTIVE'.
*   **Source Files**:
    *   `tracker/backend_engine.py`
    *   `tracker/models.py` (Storing pre-computed `DailySummary` metrics)

---

### 5. Smart Reporting Module
**Description**: Automatically generates summarized daily reports, employee-specific breakdowns, and percentage-based productivity metrics.

*   **Libraries & Frameworks**:
    *   `Django REST Framework (DRF)`: Provides JSON endpoints for dashboards.
*   **Key Components/Methods**:
    *   `DailySummary` Model: Stores calculated metrics (Total hours, Score, Burnout Risk).
    *   `API Views`: Serves processed data for real-time reporting.
*   **Source Files**:
    *   `tracker/models.py`
    *   `tracker/serializers.py`
    *   `tracker/views.py`

---

### 6. Visualization & Dashboard Module
**Description**: Renders the analyzed data into a real-time graphical interface with charts and performance analytics views.

*   **Libraries & Frameworks**:
    *   `Chart.js`: Used for rendering interactive bar and doughnut charts.
    *   `Bootstrap 5`: For responsive layout and dashboard components (Cards, Tables).
    *   `Bootstrap Icons`: For visual status indicators and navigation.
*   **Key Components/Methods**:
    *   `trendChart`: A Bar chart showing productivity trends over time.
    *   `distributionChart`: A Doughnut chart visualizing the split between Productive and Idle time.
    *   `WorkAnalytics OS`: The primary dashboard interface.
*   **Source Files**:
    *   `tracker/templates/tracker/dashboard.html`
    *   `tracker/templates/tracker/workforce_activity.html`
