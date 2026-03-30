from django import template

register = template.Library()


@register.filter
def rating_color(value):
    """Return a CSS color class based on movie rating value (0-10 scale)."""
    try:
        rating = float(value)
    except (TypeError, ValueError):
        return "text-gray-400"

    if rating >= 7.5:
        return "text-green-400"
    elif rating >= 6.0:
        return "text-yellow-400"
    elif rating >= 4.0:
        return "text-orange-400"
    else:
        return "text-red-400"


@register.filter
def truncate_overview(value, length=150):
    """Truncate overview text to given length, appending ellipsis if needed."""
    if not value:
        return ""
    try:
        length = int(length)
    except (TypeError, ValueError):
        length = 150

    text = str(value)
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + "..."
