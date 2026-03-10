from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Avg
import json
import csv
from django.http import HttpResponse
from django.contrib.auth import logout

from .models import ActivityLog, WorkSession, DailySummary
from .serializers import ActivityLogSerializer, WorkSessionSerializer
from .ai_engine import run_daily_analysis

# --- 1. API VIEWSETS (For Desktop Agent) ---
class WorkSessionViewSet(viewsets.ModelViewSet):
    queryset = WorkSession.objects.all()
    serializer_class = WorkSessionSerializer

class ActivityLogViewSet(viewsets.ModelViewSet):
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer

@api_view(['POST'])
def trigger_ai_analysis(request):
    """API endpoint to manually trigger the AI Analysis for a user."""
    user_id = request.data.get('user_id')
    if not user_id:
        return Response({"error": "user_id is required"}, status=400)
        
    summary = run_daily_analysis(user_id)
    
    if summary:
        return Response({
            "message": "AI Analysis complete",
            "date": summary.date,
            "total_hours": summary.total_working_hours,
            "productivity_score": summary.productivity_score,
            "burnout_risk": summary.burnout_risk
        })
    else:
        return Response({"error": "User not found or calculation failed"}, status=404)

# --- 2. SECURITY & ROUTING ---
def is_hr_or_admin(user):
    return user.role in ['HR', 'ADMIN']

@login_required
def dashboard_redirect(request):
    """Acts as a traffic cop. Redirects to the correct dashboard based on role."""
    if request.user.role in ['HR', 'ADMIN'] or request.user.is_superuser:
        return redirect('hr-dashboard')
    else:
        return redirect('employee-dashboard')

# --- 3. WEB DASHBOARDS ---
@login_required
@user_passes_test(is_hr_or_admin, login_url='/api/dashboard/my-stats/')
def hr_dashboard(request):
    """Renders the ProHance-style Enterprise web dashboard for HR and Managers."""
    summaries = DailySummary.objects.all().order_by('-date')
    
    # Calculate Global KPIs
    total_hours = summaries.aggregate(Sum('total_working_hours'))['total_working_hours__sum'] or 0
    total_prod_hours = summaries.aggregate(Sum('productive_hours'))['productive_hours__sum'] or 0
    avg_score = summaries.aggregate(Avg('productivity_score'))['productivity_score__avg'] or 0
    total_idle_hours = max(0, total_hours - total_prod_hours)

    # Prepare data for Chart
    chart_labels = []
    chart_scores = []
    for summary in summaries[:10]: 
        label = f"{summary.user.username} ({summary.date})"
        chart_labels.append(label)
        chart_scores.append(summary.productivity_score)
        
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
def employee_dashboard(request):
    """Renders the web dashboard for a single Employee to view their own stats."""
    summaries = DailySummary.objects.filter(user=request.user).order_by('-date')
    
    chart_labels = []
    chart_scores = []
    for summary in summaries[:7]: 
        chart_labels.append(str(summary.date))
        chart_scores.append(summary.productivity_score)
        
    chart_labels.reverse()
    chart_scores.reverse()
        
    context = {
        'summaries': summaries,
        'chart_labels': json.dumps(chart_labels),
        'chart_scores': json.dumps(chart_scores)
    }
    return render(request, 'tracker/employee_dashboard.html', context)

# --- 4. CSV EXPORT ---
@login_required
def export_my_report(request):
    """Generates a downloadable CSV file of the employee's productivity data."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{request.user.username}_productivity_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Total Hours', 'Productive Hours', 'AI Score', 'Burnout Risk', 'Notes'])

    summaries = DailySummary.objects.filter(user=request.user).order_by('-date')
    for summary in summaries:
        writer.writerow([
            summary.date,
            summary.total_working_hours,
            summary.productive_hours,
            summary.productivity_score,
            summary.burnout_risk,
            summary.focus_pattern_notes
        ])

    return response


def custom_logout(request):
    """
    Safely logs the user out and redirects to the login page.
    Fixes the Django 5.0+ GET request block for logout links.
    """
    logout(request)
    return redirect('login')