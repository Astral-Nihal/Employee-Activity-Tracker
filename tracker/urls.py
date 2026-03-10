from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.contrib.auth import views as auth_views

# Add custom_logout to your imports here:
from .views import ActivityLogViewSet, WorkSessionViewSet, trigger_ai_analysis, hr_dashboard, employee_dashboard, export_my_report, dashboard_redirect, custom_logout



# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'sessions', WorkSessionViewSet)
router.register(r'activities', ActivityLogViewSet)

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
    path('analyze/', trigger_ai_analysis, name='trigger-analysis'),
    
    # Dashboard URLs
    path('dashboard/route/', dashboard_redirect, name='dashboard-route'),
    path('dashboard/hr/', hr_dashboard, name='hr-dashboard'),
    path('dashboard/my-stats/', employee_dashboard, name='employee-dashboard'),
    path('dashboard/export/', export_my_report, name='export-my-report'),
    
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='tracker/login.html'), name='login'),
    
    # --- UPDATE THIS LINE ---
    path('logout/', custom_logout, name='logout'),
]