from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.contrib.auth import views as auth_views

from .views import (
    # Existing viewsets & API
    ActivityLogViewSet, WorkSessionViewSet, trigger_ai_analysis,
    # Task 1: Agent auth endpoints
    agent_login, agent_logout,
    # Existing HR dashboards
    hr_dashboard, workforce_activity, time_distribution, advanced_reports,
    # Task 3: Employee Management CRUD
    employee_management, employee_create, employee_edit, employee_deactivate,
    # Existing employee dashboard & exports
    employee_dashboard, export_my_report, export_global_report,
    # Auth helpers
    dashboard_redirect, custom_logout,
)

router = DefaultRouter()
router.register(r'sessions', WorkSessionViewSet)
router.register(r'activities', ActivityLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('analyze/', trigger_ai_analysis, name='trigger-analysis'),

    # ----- Task 1: Desktop Agent Auth -----
    path('agent-login/', agent_login, name='agent-login'),
    path('agent-logout/', agent_logout, name='agent-logout'),

    # ----- HR Dashboards -----
    path('dashboard/route/', dashboard_redirect, name='dashboard-route'),
    path('dashboard/hr/', hr_dashboard, name='hr-dashboard'),
    path('dashboard/hr/workforce/', workforce_activity, name='workforce-activity'),
    path('dashboard/hr/time-distribution/', time_distribution, name='time-distribution'),
    path('dashboard/hr/reports/', advanced_reports, name='advanced-reports'),
    path('dashboard/hr/export-global/', export_global_report, name='export-global-report'),

    # ----- Task 3: Employee Management -----
    path('dashboard/hr/employees/', employee_management, name='employee-management'),
    path('dashboard/hr/employees/create/', employee_create, name='employee-create'),
    path('dashboard/hr/employees/<int:pk>/edit/', employee_edit, name='employee-edit'),
    path('dashboard/hr/employees/<int:pk>/deactivate/', employee_deactivate, name='employee-deactivate'),

    # ----- Employee Dashboard -----
    path('dashboard/my-stats/', employee_dashboard, name='employee-dashboard'),
    path('dashboard/export/', export_my_report, name='export-my-report'),

    # ----- Auth -----
    path('login/', auth_views.LoginView.as_view(template_name='tracker/login.html'), name='login'),
    path('logout/', custom_logout, name='logout'),
]