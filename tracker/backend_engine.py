from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from .models import ActivityLog, DailySummary

User = get_user_model()

def classify_activity(activity_name):
    """
    Categorizes a window title based on a massive list of keywords.
    """
    activity_lower = activity_name.lower()

    # --- EXPANDED PRODUCTIVE KEYWORDS ---
    productive_keywords = [
        # AI, LLM & Agentic Tools
        'chatgpt', 'gemini', 'claude', 'copilot', 'openai', 'perplexity', 
        'midjourney', 'huggingface', 'anthropic', 'cursor', 'antigravity',
        'devin', 'auto-gpt', 'langchain', 'crewai', 'autogen', 'babyagi',
        
        # Development & IT Tools
        'code', 'vscode', 'visual studio', 'pycharm', 'intellij', 'eclipse', 
        'github', 'gitlab', 'bitbucket', 'postman', 'docker', 'terminal', 
        'powershell', 'cmd', 'stackoverflow', 'jira', 'confluence', 'sublime', 
        'notepad++', 'android studio', 'xcode', 'aws', 'azure', 'linux', 'ubuntu',
        
        # Office & Collaboration
        'word', 'excel', 'powerpoint', 'outlook', 'teams', 'slack', 'zoom', 
        'meet', 'docs', 'sheets', 'slides', 'notion', 'trello', 'asana', 
        'workspace', 'mail', 'calendar', 'drive', 'onedrive',
        
        # Design & Creative
        'figma', 'photoshop', 'illustrator', 'premiere', 'after effects', 
        'blender', 'canva', 'xd', 'lightroom', 'autocad', 'solidworks', 'unity', 'unreal'
    ]

    # --- EXPANDED UNPRODUCTIVE/DISTRACTING KEYWORDS ---
    unproductive_keywords = [
        # Entertainment & Streaming
        'youtube', 'netflix', 'prime video', 'hulu', 'twitch', 'disney+', 
        'hbo', 'spotify', 'apple music', 'movie', 'tv show',
        
        # Social Media & Chat
        'facebook', 'twitter', 'x.com', 'instagram', 'tiktok', 'reddit', 
        'snapchat', 'pinterest', 'whatsapp web', 'discord', 'telegram', 'messenger',
        
        # Gaming
        'steam', 'epic games', 'riot', 'valorant', 'minecraft', 'roblox', 
        'league of legends', 'cs:go', 'game', 'play', 'xbox', 'nintendo',
        
        # Shopping & Leisure
        'amazon', 'ebay', 'aliexpress', 'flipkart', 'myntra', 'zomato', 'swiggy'
    ]

    # Check which category it falls into
    if any(keyword in activity_lower for keyword in productive_keywords):
        return 'PRODUCTIVE'
    elif any(keyword in activity_lower for keyword in unproductive_keywords):
        return 'UNPRODUCTIVE'
    elif 'idle' in activity_lower:
        return 'NEUTRAL'
    else:
        return 'NEUTRAL'

def run_daily_analysis(user_id):
    """
    Analyzes today's logs for a user, calculates scores, and detects burnout risk.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None
    today = timezone.now().date()
    
    # Get all logs for today
    logs = ActivityLog.objects.filter(
        user=user, 
        start_time__date=today
    )
    
    if not logs.exists():
        return None

    total_seconds = 0
    productive_seconds = 0
    unproductive_seconds = 0

    for log in logs:
        # 1. First, classify the activity using our expanded dictionary
        classification = classify_activity(log.activity_name)
        
        # 2. Add up the time
        duration = log.duration_seconds
        total_seconds += duration
        
        if classification == 'PRODUCTIVE':
            productive_seconds += duration
        elif classification == 'UNPRODUCTIVE':
            unproductive_seconds += duration

    # 3. Calculate metrics
    total_hours = total_seconds / 3600
    productive_hours = productive_seconds / 3600
    
    if total_seconds > 0:
        productivity_score = (productive_seconds / total_seconds) * 100
    else:
        productivity_score = 0

    # 4. Burnout Detection Logic
    burnout_risk = 'LOW'
    notes = "Work patterns are within normal operational limits."

    if total_hours > 10:
        burnout_risk = 'HIGH'
        notes = "CRITICAL: Employee exceeded 10 hours of active screen time. High risk of burnout."
    elif total_hours > 8 and productivity_score < 40:
        burnout_risk = 'MEDIUM'
        notes = "WARNING: Long hours detected with low productivity. Potential fatigue."
    elif productivity_score > 85:
        notes = "Excellent focus and high productivity today."

    # 5. Save the summary to the database
    summary, created = DailySummary.objects.update_or_create(
        user=user,
        date=today,
        defaults={
            'total_working_hours': round(total_hours, 2),
            'productive_hours': round(productive_hours, 2),
            'productivity_score': round(productivity_score, 2),
            'burnout_risk': burnout_risk,
            'focus_pattern_notes': notes
        }
    )
    
    return summary