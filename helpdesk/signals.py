"""
Signal handlers for automatic notification creation.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Ticket, TicketReply, Notification, UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile when a new User is created."""
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=Ticket)
def ticket_created_notification(sender, instance, created, **kwargs):
    """Create notification when a ticket is created."""
    if created:
        # Notify the employee who created the ticket
        Notification.objects.create(
            user=instance.employee,
            ticket=instance,
            message=f"Your ticket #{instance.id} has been created successfully.",
            notification_type='ticket_created'
        )

        # Notify all support staff about the new ticket
        support_users = User.objects.filter(profile__role__in=['support', 'admin'])
        for support_user in support_users:
            Notification.objects.create(
                user=support_user,
                ticket=instance,
                message=f"New ticket #{instance.id} requires attention: {instance.subject}",
                notification_type='new_ticket'
            )


@receiver(post_save, sender=TicketReply)
def reply_notification(sender, instance, created, **kwargs):
    """Create notification when someone replies to a ticket."""
    if created:
        ticket = instance.ticket

        # If the employee replied, notify assigned support staff
        if instance.author == ticket.employee:
            if ticket.assigned_to and ticket.assigned_to != instance.author:
                Notification.objects.create(
                    user=ticket.assigned_to,
                    ticket=ticket,
                    message=f"{instance.author.get_full_name() or instance.author.username} replied to ticket #{ticket.id}.",
                    notification_type='reply'
                )
        else:
            # Support replied, notify the employee
            if ticket.employee != instance.author:
                Notification.objects.create(
                    user=ticket.employee,
                    ticket=ticket,
                    message=f"IT Support replied to your ticket #{ticket.id}.",
                    notification_type='reply'
                )