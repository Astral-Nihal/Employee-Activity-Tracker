from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Avg
from django.utils import timezone
import json
import csv
from django.http import HttpResponse
from django.contrib.auth import logout

from .models import ActivityLog, WorkSession, DailySummary
from .serializers import ActivityLogSerializer, WorkSessionSerializer
from .ai_engine import run_daily_analysis, classify_activity

# --- 1. API VIEWSETS (For Desktop Agent) ---
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
        return Response({"message": "AI Analysis complete", "date": summary.date})
    return Response({"error": "User not found or calculation failed"}, status=404)

# --- 2. SECURITY & ROUTING ---
def is_hr_or_admin(user):
    return user.role in ['HR', 'ADMIN']

@login_required
def dashboard_redirect(request):
    if request.user.role in ['HR', 'ADMIN'] or request.user.is_superuser:
        return redirect('hr-dashboard')
    return redirect('employee-dashboard')

# --- 3. WEB DASHBOARDS ---
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
        'chart_scores': json.dumps(chart_scores)
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
        'total_sessions': total_sessions
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
        'summaries': summaries, 'chart_labels': json.dumps(chart_labels), 'chart_scores': json.dumps(chart_scores)
    })

# --- 4. CSV EXPORTS & LOGOUT ---
@login_required
def export_my_report(request):
    """Export for a single employee."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{request.user.username}_productivity_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Total Hours', 'Productive Hours', 'AI Score', 'Burnout Risk', 'Notes'])
    for summary in DailySummary.objects.filter(user=request.user).order_by('-date'):
        writer.writerow([summary.date, summary.total_working_hours, summary.productive_hours, summary.productivity_score, summary.burnout_risk, summary.focus_pattern_notes])
    return response

@login_required
@user_passes_test(is_hr_or_admin, login_url='/api/dashboard/my-stats/')
def export_global_report(request):
    """Export for HR/Admins covering the whole organization."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Enterprise_Global_Report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Employee Username', 'Role', 'Total Hours', 'Productive Hours', 'AI Score', 'Burnout Risk', 'Notes'])
    
    summaries = DailySummary.objects.all().select_related('user').order_by('-date')
    for summary in summaries:
        writer.writerow([
            summary.date, summary.user.username, summary.user.role,
            summary.total_working_hours, summary.productive_hours,
            summary.productivity_score, summary.burnout_risk, summary.focus_pattern_notes
        ])
    return response

def custom_logout(request):
    logout(request)
    return redirect('login')