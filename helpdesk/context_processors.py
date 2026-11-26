"""
Context processors for adding data to all templates.
"""

from .models import Notification


def notification_count(request):
    """Add unread notification count to all templates."""
    if request.user.is_authenticated:
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        return {'unread_notification_count': count}
    return {'unread_notification_count': 0}