from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.contrib.auth import views as auth_views

from .views import (
    ActivityLogViewSet, WorkSessionViewSet, trigger_ai_analysis, 
    hr_dashboard, workforce_activity, time_distribution, advanced_reports,
    employee_dashboard, export_my_report, export_global_report, 
    dashboard_redirect, custom_logout
)

router = DefaultRouter()
router.register(r'sessions', WorkSessionViewSet)
router.register(r'activities', ActivityLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('analyze/', trigger_ai_analysis, name='trigger-analysis'),
    
    # HR Dashboards
    path('dashboard/route/', dashboard_redirect, name='dashboard-route'),
    path('dashboard/hr/', hr_dashboard, name='hr-dashboard'),
    path('dashboard/hr/workforce/', workforce_activity, name='workforce-activity'),
    path('dashboard/hr/time-distribution/', time_distribution, name='time-distribution'),
    path('dashboard/hr/reports/', advanced_reports, name='advanced-reports'),
    path('dashboard/hr/export-global/', export_global_report, name='export-global-report'),
    
    # Employee Dashboard
    path('dashboard/my-stats/', employee_dashboard, name='employee-dashboard'),
    path('dashboard/export/', export_my_report, name='export-my-report'),
    
    # Auth
    path('login/', auth_views.LoginView.as_view(template_name='tracker/login.html'), name='login'),
    path('logout/', custom_logout, name='logout'),
]