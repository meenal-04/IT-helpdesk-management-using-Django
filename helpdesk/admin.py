"""
Admin configuration for IT Helpdesk.
"""

from django.contrib import admin
from .models import (
    UserProfile, Category, Ticket, TicketAttachment,
    TicketReply, InternalNote, Notification, Feedback
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'department', 'phone', 'created_at')
    list_filter = ('role', 'department')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    raw_id_fields = ('user',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


class TicketReplyInline(admin.TabularInline):
    model = TicketReply
    extra = 0
    readonly_fields = ('created_at',)


class InternalNoteInline(admin.TabularInline):
    model = InternalNote
    extra = 0
    readonly_fields = ('created_at',)


class TicketAttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 0
    readonly_fields = ('uploaded_at',)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'subject', 'employee', 'category',
        'priority', 'status', 'assigned_to', 'created_at'
    )
    list_filter = ('status', 'priority', 'category', 'created_at')
    search_fields = ('subject', 'description', 'employee__username', 'id')
    raw_id_fields = ('employee', 'assigned_to')
    readonly_fields = ('created_at', 'updated_at', 'resolved_at', 'closed_at')
    date_hierarchy = 'created_at'
    inlines = [TicketReplyInline, InternalNoteInline, TicketAttachmentInline]

    fieldsets = (
        ('Ticket Information', {
            'fields': ('subject', 'description', 'category', 'priority', 'status')
        }),
        ('Assignment', {
            'fields': ('employee', 'assigned_to')
        }),
        ('Resolution', {
            'fields': ('resolution_summary',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'resolved_at', 'closed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TicketReply)
class TicketReplyAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('message', 'author__username', 'ticket__subject')
    raw_id_fields = ('ticket', 'author')


@admin.register(InternalNote)
class InternalNoteAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('note', 'author__username', 'ticket__subject')
    raw_id_fields = ('ticket', 'author')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'notification_type', 'is_read', 'created_at')
    list_filter = ('is_read', 'notification_type', 'created_at')
    search_fields = ('message', 'user__username')
    raw_id_fields = ('user', 'ticket')


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('comment', 'ticket__subject')
    raw_id_fields = ('ticket',)