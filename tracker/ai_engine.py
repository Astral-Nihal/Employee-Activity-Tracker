from .models import ActivityLog, DailySummary, User
from django.utils import timezone
import datetime

def classify_activity(activity_name):
    """
    Simulates an AI/NLP classification model using keyword heuristics.
    Returns: (is_productive (Boolean), category (String))
    """
    name_lower = str(activity_name).lower()
    
    # NLP Keywords mapped to categories
    productive_keywords = ['code', 'visual studio', 'github', 'stackoverflow', 'excel', 'word', 'mail', 'meet', 'zoom', 'docs']
    unproductive_keywords = ['youtube', 'facebook', 'instagram', 'netflix', 'game', 'whatsapp', 'twitter', 'tiktok']
    
    if any(keyword in name_lower for keyword in productive_keywords):
        return True, 'Work/Productive'
    elif any(keyword in name_lower for keyword in unproductive_keywords):
        return False, 'Distraction/Social'
    
    return None, 'Neutral'

def run_daily_analysis(user_id, target_date=None):
    """
    Analyzes the user's activities for a specific day, calculates 
    productivity scores, and detects burnout risk.
    """
    if target_date is None:
        target_date = timezone.now().date()
        
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None

    # Fetch all logs for the given user and date
    logs = ActivityLog.objects.filter(user=user, start_time__date=target_date)
    
    total_seconds = 0
    productive_seconds = 0
    unproductive_seconds = 0
    
    # 1. Classify Data
    for log in logs:
        # If it hasn't been classified by AI yet
        if log.is_productive is None and log.activity_type != 'IDLE':
            is_prod, category = classify_activity(log.activity_name)
            log.is_productive = is_prod
            log.category = category
            log.save()
            
        # Tally times
        total_seconds += log.duration_seconds
        if log.is_productive is True:
            productive_seconds += log.duration_seconds
        elif log.is_productive is False:
            unproductive_seconds += log.duration_seconds

    # 2. Calculate Hours
    total_hours = total_seconds / 3600
    prod_hours = productive_seconds / 3600
    
    # 3. Calculate Productivity Score (0-100)
    score = 0.0
    if total_hours > 0:
        score = (prod_hours / total_hours) * 100
        
    # 4. Burnout Risk Detection (Simple Rule-based ML Simulation)
    # E.g., Working more than 9 hours with dropping productivity = HIGH
    burnout_risk = 'LOW'
    if total_hours > 10:
        burnout_risk = 'HIGH'
    elif total_hours > 8 and score < 50:
        burnout_risk = 'MEDIUM'
        
    # 5. Generate Smart Report Summary
    summary, created = DailySummary.objects.get_or_create(
        user=user, 
        date=target_date,
        defaults={'total_working_hours': 0, 'productive_hours': 0, 'productivity_score': 0}
    )
    
    summary.total_working_hours = round(total_hours, 2)
    summary.productive_hours = round(prod_hours, 2)
    summary.productivity_score = round(score, 2)
    summary.burnout_risk = burnout_risk
    
    if burnout_risk == 'HIGH':
        summary.focus_pattern_notes = "Warning: Employee is working excessive hours. High risk of burnout."
    else:
        summary.focus_pattern_notes = "Work patterns are within normal operational limits."
        
    summary.save()
    
    return summary