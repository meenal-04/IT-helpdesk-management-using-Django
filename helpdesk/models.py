"""
Models for IT Helpdesk Management System.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse


class UserProfile(models.Model):
    """Extended user profile with role information."""

    ROLE_CHOICES = [
        ('employee', 'Employee'),
        ('support', 'IT Support Staff'),
        ('admin', 'Administrator'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='employee'
    )
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_support(self):
        return self.role in ('support', 'admin')

    @property
    def is_employee(self):
        return self.role == 'employee'


class Category(models.Model):
    """Ticket categories such as Hardware, Software, Network, etc."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Ticket(models.Model):
    """Main support ticket model."""

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('waiting', 'Waiting for Employee'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    # Core fields
    subject = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='tickets'
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open'
    )

    # Relationships
    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_tickets'
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets'
    )

    # Resolution
    resolution_summary = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Ticket #{self.id} - {self.subject}"

    def get_absolute_url(self):
        return reverse('helpdesk:ticket_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        """Track resolved/closed timestamps automatically."""
        if self.status == 'resolved' and not self.resolved_at:
            self.resolved_at = timezone.now()
        if self.status == 'closed' and not self.closed_at:
            self.closed_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def status_badge_class(self):
        """Return Bootstrap badge class based on status."""
        return {
            'open': 'badge-status-open',
            'assigned': 'badge-status-assigned',
            'in_progress': 'badge-status-in-progress',
            'waiting': 'badge-status-waiting',
            'resolved': 'badge-status-resolved',
            'closed': 'badge-status-closed',
        }.get(self.status, 'bg-secondary')

    @property
    def priority_badge_class(self):
        """Return Bootstrap badge class based on priority."""
        return {
            'low': 'badge-priority-low',
            'medium': 'badge-priority-medium',
            'high': 'badge-priority-high',
            'critical': 'badge-priority-critical',
        }.get(self.priority, 'bg-secondary')


class TicketAttachment(models.Model):
    """File attachments uploaded with a ticket."""

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to='attachments/%Y/%m/')
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_attachments'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ticket Attachment'
        verbose_name_plural = 'Ticket Attachments'

    def __str__(self):
        return f"Attachment for Ticket #{self.ticket.id}"


class TicketReply(models.Model):
    """Public replies/conversation between employee and support staff."""

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='replies'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ticket_replies'
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ticket Reply'
        verbose_name_plural = 'Ticket Replies'
        ordering = ['created_at']

    def __str__(self):
        return f"Reply by {self.author.username} on Ticket #{self.ticket.id}"


class InternalNote(models.Model):
    """Internal notes visible ONLY to support staff and admins."""

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='internal_notes'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='internal_notes'
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Internal Note'
        verbose_name_plural = 'Internal Notes'
        ordering = ['-created_at']

    def __str__(self):
        return f"Internal note by {self.author.username} on Ticket #{self.ticket.id}"


class Notification(models.Model):
    """User notifications for ticket events."""

    NOTIFICATION_TYPES = [
        ('ticket_created', 'Ticket Created'),
        ('new_ticket', 'New Ticket for Support'),
        ('ticket_assigned', 'Ticket Assigned'),
        ('status_changed', 'Status Changed'),
        ('reply', 'New Reply'),
        ('resolved', 'Ticket Resolved'),
        ('closed', 'Ticket Closed'),
        ('reopened', 'Ticket Reopened'),
        ('feedback', 'Feedback Received'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True
    )
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    message = models.CharField(max_length=500, default='')
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
        default='status_changed'
    )
    is_read = models.BooleanField(default=False)
    # created_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:50]}"


class Feedback(models.Model):
    """Employee feedback submitted after ticket resolution."""

    RATING_CHOICES = [
        (1, '1 - Very Poor'),
        (2, '2 - Poor'),
        (3, '3 - Average'),
        (4, '4 - Good'),
        (5, '5 - Excellent'),
    ]

    ticket = models.OneToOneField(
        Ticket,
        on_delete=models.CASCADE,
        related_name='feedback'
    )
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedback'

    def __str__(self):
        return f"Feedback for Ticket #{self.ticket.id} - {self.rating} stars"