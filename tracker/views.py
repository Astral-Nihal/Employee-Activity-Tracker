from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
import json
import csv
from django.http import HttpResponse

from .models import ActivityLog, WorkSession, DailySummary
from .serializers import ActivityLogSerializer, WorkSessionSerializer
from .ai_engine import run_daily_analysis

# ViewSet for Work Sessions
class WorkSessionViewSet(viewsets.ModelViewSet):
    queryset = WorkSession.objects.all()
    serializer_class = WorkSessionSerializer

# ViewSet for Activity Logs (App, Web, Idle tracking)
class ActivityLogViewSet(viewsets.ModelViewSet):
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer

@api_view(['POST'])
def trigger_ai_analysis(request):
    """
    API endpoint to manually trigger the AI Analysis for a user.
    Expects JSON: {"user_id": 1}
    """
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

# --- NEW SECURITY CHECK ---
def is_hr_or_admin(user):
    # Checks if the user is authorized to view HR pages
    return user.role in ['HR', 'ADMIN']

@login_required
@user_passes_test(is_hr_or_admin, login_url='/api/dashboard/my-stats/')
def hr_dashboard(request):
    """
    Renders the web dashboard for HR and Managers to view employee stats.
    Includes data preparation for Chart.js
    """
    # Fetch the latest summaries, ordered by date (newest first)
    summaries = DailySummary.objects.all().order_by('-date')
    
    # Prepare data for the Bar Chart (Recent 10 Productivity Scores)
    chart_labels = []
    chart_scores = []
    
    for summary in summaries[:10]: # Grab the 10 most recent entries
        # Create a label like "Username (YYYY-MM-DD)"
        label = f"{summary.user.username} ({summary.date})"
        chart_labels.append(label)
        chart_scores.append(summary.productivity_score)
        
    context = {
        'summaries': summaries,
        'chart_labels': json.dumps(chart_labels),
        'chart_scores': json.dumps(chart_scores)
    }
    return render(request, 'tracker/dashboard.html', context)


@login_required
def employee_dashboard(request):
    """
    Renders the web dashboard for a single Employee to view their own stats.
    """
    # Fetch ONLY the logged-in user's summaries
    summaries = DailySummary.objects.filter(user=request.user).order_by('-date')
    
    # Prepare data for the Bar Chart (Last 7 Days)
    chart_labels = []
    chart_scores = []
    
    for summary in summaries[:7]: 
        chart_labels.append(str(summary.date))
        chart_scores.append(summary.productivity_score)
        
    # Reverse to show chronological order left-to-right on the chart
    chart_labels.reverse()
    chart_scores.reverse()
        
    context = {
        'summaries': summaries,
        'chart_labels': json.dumps(chart_labels),
        'chart_scores': json.dumps(chart_scores)
    }
    return render(request, 'tracker/employee_dashboard.html', context)

# --- NEW CSV EXPORT VIEW ---
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