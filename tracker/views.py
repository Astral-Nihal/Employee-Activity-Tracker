from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, logout
from django.db.models import Sum, Avg
from django.utils import timezone
from django.contrib import messages
import json
import csv
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .models import ActivityLog, WorkSession, DailySummary, User
from .serializers import ActivityLogSerializer, WorkSessionSerializer
from .backend_engine import run_daily_analysis, classify_activity


# ===========================================================================
# 1. API VIEWSETS (For Desktop Agent)
# ===========================================================================
class WorkSessionViewSet(viewsets.ModelViewSet):
    queryset = WorkSession.objects.all()
    serializer_class = WorkSessionSerializer

class ActivityLogViewSet(viewsets.ModelViewSet):
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer

@api_view(['POST'])
def trigger_ai_analysis(request):
    user_id = request.data.get('user_id')
    if not user_id:
        return Response({"error": "user_id is required"}, status=400)
    summary = run_daily_analysis(user_id)
    if summary:
        return Response({"message": "AI Analysis complete", "date": str(summary.date)})
    return Response({"error": "User not found or calculation failed"}, status=404)


# ===========================================================================
# TASK 1: Desktop Agent Authentication Endpoints
# ===========================================================================

@csrf_exempt
@api_view(['POST'])
def agent_login(request):
    """
    Desktop agent calls this on startup.
    Accepts: { "username": "...", "password": "..." }
    Returns: { "user_id": 5, "token": "abc123...", "username": "john" }
    """
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()

    if not username or not password:
        return Response({"error": "Username and password are required."}, status=400)

    user = authenticate(request, username=username, password=password)

    if user is None:
        return Response({"error": "Invalid credentials. Please check your username and password."}, status=401)

    if not user.is_active:
        return Response({"error": "This account has been deactivated. Contact your HR administrator."}, status=403)

    # Get or create a persistent API token for this user
    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        "user_id": user.pk,
        "token": token.key,
        "username": user.username,
        "role": user.role,
    }, status=200)


@csrf_exempt
@api_view(['POST'])
def agent_logout(request):
    """
    Desktop agent calls this on graceful shutdown (Ctrl+C).
    Accepts: { "token": "abc123...", "session_id": 42 }
    Closes the active WorkSession and invalidates the token.
    """
    token_key = request.data.get('token', '').strip()
    session_id = request.data.get('session_id')

    if not token_key:
        return Response({"error": "Token is required."}, status=400)

    try:
        token_obj = Token.objects.get(key=token_key)
    except Token.DoesNotExist:
        return Response({"error": "Invalid token."}, status=401)

    # Close the open WorkSession (stamp end_time)
    if session_id:
        try:
            session = WorkSession.objects.get(pk=session_id, user=token_obj.user)
            session.end_time = timezone.now()
            session.save()
        except WorkSession.DoesNotExist:
            pass  # Session may have already been closed; not a fatal error

    return Response({"message": f"Agent for '{token_obj.user.username}' logged out successfully."}, status=200)


# ===========================================================================
# 2. SECURITY & ROUTING
# ===========================================================================

def is_hr_or_admin(user):
    return user.role in ['HR', 'ADMIN']

@login_required
def dashboard_redirect(request):
    if request.user.role in ['HR', 'ADMIN'] or request.user.is_superuser:
        return redirect('hr-dashboard')
    return redirect('employee-dashboard')


# ===========================================================================
# 3. WEB DASHBOARDS (UNCHANGED)
# ===========================================================================

@login_required
@user_passes_test(is_hr_or_admin, login_url='/api/dashboard/my-stats/')
def hr_dashboard(request):
    summaries = DailySummary.objects.all().order_by('-date')
    total_hours = summaries.aggregate(Sum('total_working_hours'))['total_working_hours__sum'] or 0
    total_prod_hours = summaries.aggregate(Sum('productive_hours'))['productive_hours__sum'] or 0
    avg_score = summaries.aggregate(Avg('productivity_score'))['productivity_score__avg'] or 0
    total_idle_hours = max(0, total_hours - total_prod_hours)

    chart_labels = [f"{s.user.username} ({s.date})" for s in summaries[:10]]
    chart_scores = [s.productivity_score for s in summaries[:10]]

    context = {
        'summaries': summaries,
        'kpi_total_hours': round(total_hours, 1),
        'kpi_avg_score': round(avg_score, 1),
        'kpi_prod_hours': round(total_prod_hours, 1),
        'kpi_idle_hours': round(total_idle_hours, 1),
        'chart_labels': json.dumps(chart_labels),
        'chart_scores': json.dumps(chart_scores),
    }
    return render(request, 'tracker/dashboard.html', context)

@login_required
@user_passes_test(is_hr_or_admin, login_url='/api/dashboard/my-stats/')
def workforce_activity(request):
    today = timezone.now().date()
    recent_logs = ActivityLog.objects.filter(start_time__date=today).order_by('-start_time')[:150]

    activity_data = []
    for log in recent_logs:
        activity_data.append({
            'user': log.user.username,
            'app': log.activity_name,
            'type': log.get_activity_type_display(),
            'start_time': log.start_time,
            'duration_mins': round(log.duration_seconds / 60, 1),
            'classification': classify_activity(log.activity_name)
        })
    return render(request, 'tracker/workforce_activity.html', {'activities': activity_data})

@login_required
@user_passes_test(is_hr_or_admin, login_url='/api/dashboard/my-stats/')
def time_distribution(request):
    today = timezone.now().date()
    logs = ActivityLog.objects.filter(start_time__date=today)

    category_totals = {'Productive': 0, 'Distracting': 0, 'Neutral / Idle': 0}
    app_totals = {}

    for log in logs:
        cat = classify_activity(log.activity_name)
        duration_hours = log.duration_seconds / 3600

        if cat == 'PRODUCTIVE': category_totals['Productive'] += duration_hours
        elif cat == 'UNPRODUCTIVE': category_totals['Distracting'] += duration_hours
        else: category_totals['Neutral / Idle'] += duration_hours

        app_name = log.activity_name
        if 'Google Chrome' in app_name: app_name = 'Google Chrome'
        elif 'Code' in app_name or 'Visual Studio' in app_name: app_name = 'VS Code'
        elif 'Idle' in app_name: app_name = 'Idle Time'
        elif len(app_name) > 40: app_name = app_name[:40] + '...'

        app_totals[app_name] = app_totals.get(app_name, 0) + duration_hours

    sorted_apps = sorted(app_totals.items(), key=lambda x: x[1], reverse=True)[:10]
    app_labels = [item[0] for item in sorted_apps]
    app_data = [round(item[1], 2) for item in sorted_apps]
    cat_labels = list(category_totals.keys())
    cat_data = [round(category_totals[k], 2) for k in cat_labels]

    context = {
        'cat_labels': json.dumps(cat_labels), 'cat_data': json.dumps(cat_data),
        'app_labels': json.dumps(app_labels), 'app_data': json.dumps(app_data),
        'app_breakdown': [{'app': k, 'hours': round(v, 2)} for k, v in sorted_apps]
    }
    return render(request, 'tracker/time_distribution.html', context)

@login_required
@user_passes_test(is_hr_or_admin, login_url='/api/dashboard/my-stats/')
def advanced_reports(request):
    """Renders the Advanced Reports page for HR."""
    summaries = DailySummary.objects.all().select_related('user').order_by('-date', 'user__username')
    total_logs = ActivityLog.objects.count()
    total_sessions = WorkSession.objects.count()

    context = {
        'summaries': summaries,
        'total_logs': total_logs,
        'total_sessions': total_sessions,
    }
    return render(request, 'tracker/advanced_reports.html', context)

@login_required
def employee_dashboard(request):
    summaries = DailySummary.objects.filter(user=request.user).order_by('-date')
    chart_labels = [str(s.date) for s in summaries[:7]]
    chart_scores = [s.productivity_score for s in summaries[:7]]
    chart_labels.reverse()
    chart_scores.reverse()
    return render(request, 'tracker/employee_dashboard.html', {
        'summaries': summaries,
        'chart_labels': json.dumps(chart_labels),
        'chart_scores': json.dumps(chart_scores),
    })


# ===========================================================================
# TASK 3: Admin Employee Management (CRUD)
# ===========================================================================

@login_required
@user_passes_test(is_hr_or_admin, login_url='/api/dashboard/my-stats/')
def employee_management(request):
    """List all users for the HR/Admin management panel."""
    employees = User.objects.all().order_by('is_active', 'username')
    context = {
        'employees': employees,
        'total_active': employees.filter(is_active=True).count(),
        'total_inactive': employees.filter(is_active=False).count(),
    }
    return render(request, 'tracker/employee_management.html', context)


@login_required
@user_passes_test(is_hr_or_admin, login_url='/api/dashboard/my-stats/')
def employee_create(request):
    """
    POST: Create a new employee account with a securely hashed password.
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'EMPLOYEE')
        password = request.POST.get('password', '').strip()

        if not username or not password:
            messages.error(request, 'Username and password are required.')
            return redirect('employee-management')

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' is already taken.")
            return redirect('employee-management')

        # create_user() automatically hashes the password
        User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email,
            role=role,
        )
        messages.success(request, f"Employee '{username}' created successfully.")
    return redirect('employee-management')


@login_required
@user_passes_test(is_hr_or_admin, login_url='/api/dashboard/my-stats/')
def employee_edit(request, pk):
    """
    POST: Edit an employee's name, username, role, or reset their password.
    """
    employee = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        employee.first_name = request.POST.get('first_name', employee.first_name).strip()
        employee.last_name = request.POST.get('last_name', employee.last_name).strip()
        employee.email = request.POST.get('email', employee.email).strip()
        new_username = request.POST.get('username', employee.username).strip()
        employee.role = request.POST.get('role', employee.role)

        # Check username uniqueness (exclude self)
        if new_username != employee.username and User.objects.filter(username=new_username).exists():
            messages.error(request, f"Username '{new_username}' is already taken.")
            return redirect('employee-management')
        employee.username = new_username

        # Only update password if a new one was provided
        new_password = request.POST.get('password', '').strip()
        if new_password:
            employee.set_password(new_password)

        employee.save()
        messages.success(request, f"Employee '{employee.username}' updated successfully.")

    return redirect('employee-management')


@login_required
@user_passes_test(is_hr_or_admin, login_url='/api/dashboard/my-stats/')
def employee_deactivate(request, pk):
    """
    POST: Soft-delete an employee (set is_active=False).
    Historical analytics data is preserved.
    """
    employee = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        # Prevent HR from accidentally deactivating themselves
        if employee.pk == request.user.pk:
            messages.error(request, "You cannot deactivate your own account.")
            return redirect('employee-management')

        action = request.POST.get('action', 'deactivate')
        if action == 'reactivate':
            employee.is_active = True
            employee.save()
            messages.success(request, f"Employee '{employee.username}' has been reactivated.")
        else:
            employee.is_active = False
            employee.save()
            messages.warning(request, f"Employee '{employee.username}' has been deactivated. All historical data is preserved.")

    return redirect('employee-management')


# ===========================================================================
# 4. CSV EXPORTS & LOGOUT
# ===========================================================================

@login_required
def export_my_report(request):
    """Export for a single employee."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{request.user.username}_productivity_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Total Hours', 'Productive Hours', 'AI Score', 'Burnout Risk', 'Notes'])
    for summary in DailySummary.objects.filter(user=request.user).order_by('-date'):
        writer.writerow([summary.date, summary.total_working_hours, summary.productive_hours,
                         summary.productivity_score, summary.burnout_risk, summary.focus_pattern_notes])
    return response

@login_required
@user_passes_test(is_hr_or_admin, login_url='/api/dashboard/my-stats/')
def export_global_report(request):
    """Export for HR/Admins covering the whole organisation."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Enterprise_Global_Report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Employee Username', 'Role', 'Total Hours', 'Productive Hours',
                     'AI Score', 'Burnout Risk', 'Notes'])

    summaries = DailySummary.objects.all().select_related('user').order_by('-date')
    for summary in summaries:
        writer.writerow([
            summary.date, summary.user.username, summary.user.role,
            summary.total_working_hours, summary.productive_hours,
            summary.productivity_score, summary.burnout_risk, summary.focus_pattern_notes,
        ])
    return response

def custom_logout(request):
    logout(request)
    return redirect('login')