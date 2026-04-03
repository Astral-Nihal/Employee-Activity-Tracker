from django import template

register = template.Library()


@register.filter(name='smart_hours')
def smart_hours(value):
    """
    Formats a decimal-hours value dynamically:

      value < 1  →  shows minutes  e.g. "45 mins", "1 min", "< 1 min"
      value >= 1 →  shows hours    e.g. "1h", "1.5h", "8.3h"

    Usage in templates:
        {{ summary.total_working_hours|smart_hours }}
        {{ summary.productive_hours|smart_hours }}
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value

    if value < 1:
        minutes = round(value * 60)
        if minutes == 0:
            return "< 1 min"
        elif minutes == 1:
            return "1 min"
        else:
            return f"{minutes} mins"
    else:
        # Show up to 1 decimal place; strip trailing ".0"
        rounded = round(value, 1)
        if rounded == int(rounded):
            return f"{int(rounded)}h"
        return f"{rounded}h"
