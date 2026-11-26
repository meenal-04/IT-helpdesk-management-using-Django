"""
Views for IT Helpdesk Management System.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Count, Q, Avg, F, ExpressionWrapper, DurationField
from django.utils import timezone
from datetime import timedelta

from .models import (
    Ticket, UserProfile, Notification, Category,
    TicketAttachment, TicketReply, InternalNote, Feedback
)
from .forms import (
    RegistrationForm, ProfileForm, TicketCreateForm,
    TicketReplyForm, InternalNoteForm, FeedbackForm
)
from .ai_services import get_ai_assistance
from .decorators import role_required, support_required, employee_required


# ===================================================================
# AUTHENTICATION
# ===================================================================

def home_redirect(request):
    if request.user.is_authenticated:
        return redirect('helpdesk:dashboard')
    return redirect('helpdesk:login')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('helpdesk:dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            return redirect('helpdesk:dashboard')
        messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('helpdesk:dashboard')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            role_label = dict(RegistrationForm.ROLE_CHOICES).get(form.cleaned_data['role'], 'Employee')
            messages.success(request, f"Account created successfully as {role_label}! Please log in.")
            return redirect('helpdesk:login')
        messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('helpdesk:login')


# ===================================================================
# DASHBOARD ROUTING
# ===================================================================

@login_required
def dashboard_redirect(request):
    try:
        profile = request.user.profile
        if profile.role in ('support', 'admin'):
            return redirect('helpdesk:support_dashboard')
        return redirect('helpdesk:employee_dashboard')
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=request.user, role='employee')
        return redirect('helpdesk:employee_dashboard')


# ===================================================================
# EMPLOYEE DASHBOARD
# ===================================================================

@login_required
def employee_dashboard(request):
    my_tickets = Ticket.objects.filter(employee=request.user)
    context = {
        'total_tickets': my_tickets.count(),
        'open_count': my_tickets.filter(status='open').count(),
        'in_progress_count': my_tickets.filter(status__in=['assigned', 'in_progress']).count(),
        'waiting_count': my_tickets.filter(status='waiting').count(),
        'resolved_count': my_tickets.filter(status='resolved').count(),
        'closed_count': my_tickets.filter(status='closed').count(),
        'recent_tickets': my_tickets.select_related('category', 'assigned_to').order_by('-created_at')[:5],
    }
    return render(request, 'helpdesk/employee_dashboard.html', context)


# ===================================================================
# SUPPORT DASHBOARD
# ===================================================================

@login_required
def support_dashboard(request):
    try:
        if request.user.profile.role not in ('support', 'admin'):
            messages.warning(request, "You don't have access to the support dashboard.")
            return redirect('helpdesk:employee_dashboard')
    except UserProfile.DoesNotExist:
        return redirect('helpdesk:employee_dashboard')

    all_tickets = Ticket.objects.all()
    avg_rating = Feedback.objects.aggregate(avg=Avg('rating'))['avg'] or 0

    context = {
        'total_tickets': all_tickets.count(),
        'open_count': all_tickets.filter(status='open').count(),
        'assigned_count': all_tickets.filter(status='assigned').count(),
        'in_progress_count': all_tickets.filter(status='in_progress').count(),
        'waiting_count': all_tickets.filter(status='waiting').count(),
        'resolved_count': all_tickets.filter(status='resolved').count(),
        'closed_count': all_tickets.filter(status='closed').count(),
        'critical_count': all_tickets.filter(priority='critical').exclude(status__in=['closed', 'resolved']).count(),
        'unassigned_count': all_tickets.filter(assigned_to__isnull=True).exclude(status__in=['closed', 'resolved']).count(),
        'avg_rating': round(avg_rating, 2),
        'recent_tickets': all_tickets.select_related('employee', 'assigned_to', 'category').order_by('-created_at')[:10],
        'my_tickets': all_tickets.filter(assigned_to=request.user).exclude(status__in=['closed']).order_by('-priority', '-created_at')[:5],
    }
    return render(request, 'helpdesk/support_dashboard.html', context)


# ===================================================================
# TICKET VIEWS
# ===================================================================

@login_required
def ticket_create(request):
    try:
        role = request.user.profile.role
    except UserProfile.DoesNotExist:
        role = 'employee'

    if role != 'employee':
        messages.warning(request, "Only employees can create tickets. As support/admin, you can reply to and manage existing tickets.")
        return redirect('helpdesk:dashboard')

    if request.method == 'POST':
        form = TicketCreateForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.employee = request.user
            ticket.status = 'open'
            ticket.save()
            attachment_file = form.cleaned_data.get('attachment')
            if attachment_file:
                TicketAttachment.objects.create(ticket=ticket, file=attachment_file, uploaded_by=request.user)
            messages.success(request, f"Ticket #{ticket.id} has been created successfully. Our IT support team will respond shortly.")
            return redirect('helpdesk:ticket_detail', pk=ticket.id)
        messages.error(request, "Please correct the errors below.")
    else:
        form = TicketCreateForm()
    return render(request, 'helpdesk/ticket_create.html', {'form': form})


@login_required
def ticket_list(request):
    try:
        role = request.user.profile.role
    except UserProfile.DoesNotExist:
        role = 'employee'

    is_support_view = role in ('support', 'admin')

    if is_support_view:
        tickets = Ticket.objects.select_related('employee', 'assigned_to', 'category').all()
        template = 'helpdesk/ticket_list_support.html'
        page_title = 'All Tickets'
    else:
        tickets = Ticket.objects.filter(employee=request.user).select_related('category', 'assigned_to')
        template = 'helpdesk/ticket_list_employee.html'
        page_title = 'My Tickets'

    status_filter = request.GET.get('status', '').strip()
    priority_filter = request.GET.get('priority', '').strip()
    category_filter = request.GET.get('category', '').strip()
    assigned_filter = request.GET.get('assigned', '').strip()
    search_query = request.GET.get('q', '').strip()

    if status_filter: tickets = tickets.filter(status=status_filter)
    if priority_filter: tickets = tickets.filter(priority=priority_filter)
    if category_filter: tickets = tickets.filter(category_id=category_filter)
    if assigned_filter:
        if assigned_filter == 'unassigned':
            tickets = tickets.filter(assigned_to__isnull=True)
        elif assigned_filter == 'mine':
            tickets = tickets.filter(assigned_to=request.user)
        else:
            tickets = tickets.filter(assigned_to_id=assigned_filter)
    if search_query:
        tickets = tickets.filter(
            Q(id__icontains=search_query) | Q(subject__icontains=search_query) |
            Q(employee__username__icontains=search_query) |
            Q(employee__first_name__icontains=search_query) |
            Q(employee__last_name__icontains=search_query)
        )

    context = {
        'tickets': tickets,
        'page_title': page_title,
        'categories': Category.objects.filter(is_active=True),
        'support_users': User.objects.filter(profile__role__in=['support', 'admin']),
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'category_filter': category_filter,
        'assigned_filter': assigned_filter,
        'search_query': search_query,
        'is_support_view': is_support_view,
    }
    return render(request, template, context)


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(
        Ticket.objects.select_related('employee', 'assigned_to', 'category'), pk=pk
    )

    try:
        role = request.user.profile.role
    except UserProfile.DoesNotExist:
        role = 'employee'

    is_support = role in ('support', 'admin')
    is_owner = ticket.employee == request.user

    if not (is_support or is_owner):
        messages.error(request, "You don't have permission to view that ticket.")
        return redirect('helpdesk:dashboard')

    # Determine if employee can reply (only if ticket not closed)
    can_reply = ticket.status not in ('closed',)
    can_reopen = is_owner and ticket.status in ('resolved', 'closed') and not hasattr(ticket, 'feedback')

    # Replies (public)
    replies = ticket.replies.select_related('author').order_by('created_at')
    # Internal notes (support only)
    internal_notes = ticket.internal_notes.select_related('author').order_by('-created_at') if is_support else []

    # Forms
    reply_form = TicketReplyForm()
    note_form = InternalNoteForm() if is_support else None
    feedback_form = None
    if is_owner and ticket.status == 'resolved' and not hasattr(ticket, 'feedback'):
        feedback_form = FeedbackForm()

    # Support users for assignment dropdown
    support_users = User.objects.filter(profile__role__in=['support', 'admin']) if is_support else []

    # AI assistance cached in session?
    ai_response = request.session.pop(f'ai_response_{ticket.id}', None)

    context = {
        'ticket': ticket,
        'is_support': is_support,
        'is_owner': is_owner,
        'can_reply': can_reply,
        'can_reopen': can_reopen,
        'attachments': ticket.attachments.select_related('uploaded_by'),
        'replies': replies,
        'internal_notes': internal_notes,
        'reply_form': reply_form,
        'note_form': note_form,
        'feedback_form': feedback_form,
        'support_users': support_users,
        'ai_response': ai_response,
    }
    return render(request, 'helpdesk/ticket_detail.html', context)


@login_required
def ticket_reply(request, pk):
    """Add a public reply to a ticket."""
    ticket = get_object_or_404(Ticket, pk=pk)

    try:
        role = request.user.profile.role
    except UserProfile.DoesNotExist:
        role = 'employee'

    is_support = role in ('support', 'admin')
    is_owner = ticket.employee == request.user

    if not (is_support or is_owner):
        messages.error(request, "You don't have permission to reply to that ticket.")
        return redirect('helpdesk:dashboard')

    if ticket.status == 'closed':
        messages.warning(request, "Cannot reply to a closed ticket. Please reopen it first.")
        return redirect('helpdesk:ticket_detail', pk=ticket.id)

    if request.method == 'POST':
        form = TicketReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.ticket = ticket
            reply.author = request.user
            reply.save()

            # Auto status change: if employee replies to a waiting ticket, move to in_progress
            if is_owner and ticket.status == 'waiting':
                ticket.status = 'in_progress'
                ticket.save()
                Notification.objects.create(
                    user=ticket.assigned_to if ticket.assigned_to else ticket.employee,
                    ticket=ticket,
                    message=f"Ticket #{ticket.id} — employee replied. Status moved to In Progress.",
                    notification_type='status_changed'
                )
            messages.success(request, "Your reply has been added.")
        else:
            messages.error(request, "Please correct the errors below.")
    return redirect('helpdesk:ticket_detail', pk=ticket.id)


@login_required
@support_required
def ticket_add_note(request, pk):
    """Add an internal note (support only)."""
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method == 'POST':
        form = InternalNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.ticket = ticket
            note.author = request.user
            note.save()
            messages.success(request, "Internal note added.")
        else:
            messages.error(request, "Please correct the errors below.")
    return redirect('helpdesk:ticket_detail', pk=ticket.id)


@login_required
@support_required
def ticket_assign(request, pk):
    """Assign a ticket to a support user."""
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method == 'POST':
        user_id = request.POST.get('assigned_to', '').strip()
        if user_id:
            try:
                assignee = User.objects.get(pk=user_id, profile__role__in=['support', 'admin'])
                ticket.assigned_to = assignee
                if ticket.status == 'open':
                    ticket.status = 'assigned'
                ticket.save()

                # Notify employee
                Notification.objects.create(
                    user=ticket.employee, ticket=ticket,
                    message=f"Your ticket #{ticket.id} has been assigned to "
                            f"{assignee.get_full_name() or assignee.username}.",
                    notification_type='ticket_assigned'
                )
                # Notify assignee
                Notification.objects.create(
                    user=assignee, ticket=ticket,
                    message=f"Ticket #{ticket.id} has been assigned to you.",
                    notification_type='ticket_assigned'
                )
                messages.success(request, f"Ticket #{ticket.id} assigned to {assignee.get_full_name() or assignee.username}.")
            except User.DoesNotExist:
                messages.error(request, "Selected support user was not found.")
        else:
            messages.warning(request, "Please select a support user.")
    return redirect('helpdesk:ticket_detail', pk=ticket.id)


@login_required
@support_required
def ticket_update_status(request, pk):
    """Change ticket status and/or priority."""
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status', '').strip()
        new_priority = request.POST.get('priority', '').strip()
        old_status = ticket.status

        changed = []
        if new_status and new_status != ticket.status:
            ticket.status = new_status
            changed.append(f"status to {ticket.get_status_display()}")
        if new_priority and new_priority != ticket.priority:
            ticket.priority = new_priority
            changed.append(f"priority to {ticket.get_priority_display()}")

        if changed:
            ticket.save()
            # Notify employee
            Notification.objects.create(
                user=ticket.employee, ticket=ticket,
                message=f"Ticket #{ticket.id} — {', '.join(changed)}.",
                notification_type='status_changed'
            )
            messages.success(request, f"Updated {', '.join(changed)}.")
        else:
            messages.info(request, "No changes made.")
    return redirect('helpdesk:ticket_detail', pk=ticket.id)


@login_required
@support_required
def ticket_resolve(request, pk):
    """Mark a ticket as resolved with a resolution summary."""
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method == 'POST':
        summary = request.POST.get('resolution_summary', '').strip()
        if not summary:
            messages.error(request, "Resolution summary is required.")
            return redirect('helpdesk:ticket_detail', pk=ticket.id)

        ticket.resolution_summary = summary
        ticket.status = 'resolved'
        ticket.resolved_at = timezone.now()
        ticket.save()

        Notification.objects.create(
            user=ticket.employee, ticket=ticket,
            message=f"Your ticket #{ticket.id} has been marked as Resolved. Please confirm or reopen if needed.",
            notification_type='resolved'
        )
        messages.success(request, f"Ticket #{ticket.id} marked as resolved.")
    return redirect('helpdesk:ticket_detail', pk=ticket.id)


@login_required
def ticket_reopen(request, pk):
    """Employee reopens a resolved ticket."""
    ticket = get_object_or_404(Ticket, pk=pk)

    if ticket.employee != request.user:
        messages.error(request, "You can only reopen your own tickets.")
        return redirect('helpdesk:dashboard')

    if ticket.status not in ('resolved', 'closed'):
        messages.warning(request, "Only resolved or closed tickets can be reopened.")
        return redirect('helpdesk:ticket_detail', pk=ticket.id)

    if hasattr(ticket, 'feedback'):
        messages.info(request, "This ticket already has feedback and cannot be reopened.")
        return redirect('helpdesk:ticket_detail', pk=ticket.id)

    ticket.status = 'in_progress'
    ticket.resolved_at = None
    ticket.closed_at = None
    ticket.save()

    Notification.objects.create(
        user=ticket.assigned_to if ticket.assigned_to else ticket.employee,
        ticket=ticket,
        message=f"Ticket #{ticket.id} has been reopened by the employee.",
        notification_type='reopened'
    )
    messages.success(request, f"Ticket #{ticket.id} has been reopened.")
    return redirect('helpdesk:ticket_detail', pk=ticket.id)


@login_required
def ticket_close(request, pk):
    """Employee confirms resolution — closes the ticket."""
    ticket = get_object_or_404(Ticket, pk=pk)

    if ticket.employee != request.user:
        messages.error(request, "You can only close your own tickets.")
        return redirect('helpdesk:dashboard')

    if ticket.status != 'resolved':
        messages.warning(request, "Only resolved tickets can be closed.")
        return redirect('helpdesk:ticket_detail', pk=ticket.id)

    ticket.status = 'closed'
    ticket.closed_at = timezone.now()
    ticket.save()

    Notification.objects.create(
        user=ticket.assigned_to if ticket.assigned_to else ticket.employee,
        ticket=ticket,
        message=f"Ticket #{ticket.id} has been closed by the employee.",
        notification_type='closed'
    )
    messages.success(request, f"Ticket #{ticket.id} has been closed. Thank you for your feedback!")
    return redirect('helpdesk:ticket_detail', pk=ticket.id)


@login_required
def ticket_feedback(request, pk):
    """Employee submits feedback after resolution."""
    ticket = get_object_or_404(Ticket, pk=pk)

    if ticket.employee != request.user:
        messages.error(request, "You can only provide feedback for your own tickets.")
        return redirect('helpdesk:dashboard')

    if ticket.status != 'resolved':
        messages.warning(request, "Feedback can only be given for resolved tickets.")
        return redirect('helpdesk:ticket_detail', pk=ticket.id)

    if hasattr(ticket, 'feedback'):
        messages.info(request, "You have already provided feedback for this ticket.")
        return redirect('helpdesk:ticket_detail', pk=ticket.id)

    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.ticket = ticket
            feedback.save()
            # Auto-close on feedback submission
            ticket.status = 'closed'
            ticket.closed_at = timezone.now()
            ticket.save()

            Notification.objects.create(
                user=ticket.assigned_to if ticket.assigned_to else ticket.employee,
                ticket=ticket,
                message=f"Ticket #{ticket.id} received a {feedback.rating}-star rating.",
                notification_type='feedback'
            )
            messages.success(request, "Thank you! Your feedback has been recorded.")
        else:
            messages.error(request, "Please correct the errors below.")
    return redirect('helpdesk:ticket_detail', pk=ticket.id)


# ===================================================================
# AI ASSISTANCE
# ===================================================================

@login_required
@support_required
def ticket_ai_assistance(request, pk):
    """Get AI assistance for a ticket (support only)."""
    ticket = get_object_or_404(Ticket, pk=pk)

    if request.method != 'POST':
        return redirect('helpdesk:ticket_detail', pk=ticket.id)

    # Gather conversation for context
    conversation = list(ticket.replies.values_list('author__username', 'message'))
    result = get_ai_assistance(ticket, conversation=conversation)

    # Stash in session so the detail view can render it
    request.session[f'ai_response_{ticket.id}'] = result

    if result.get('error'):
        messages.warning(request, result['error'])
    else:
        messages.success(request, "AI assistance generated below.")
    return redirect('helpdesk:ticket_detail', pk=ticket.id)


# ===================================================================
# NOTIFICATIONS
# ===================================================================

@login_required
def notifications_list(request):
    notifications = request.user.notifications.select_related('ticket').order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'helpdesk/notifications.html', context)


@login_required
def notification_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    if notif.ticket:
        return redirect('helpdesk:ticket_detail', pk=notif.ticket.id)
    return redirect('helpdesk:notifications')


@login_required
def notifications_mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('helpdesk:notifications')


# ===================================================================
# REPORTS
# ===================================================================

@login_required
@support_required
def reports_view(request):
    all_tickets = Ticket.objects.all()
    resolved_tickets = all_tickets.filter(resolved_at__isnull=False)

    # Avg resolution time
    avg_resolution = resolved_tickets.annotate(
        duration=ExpressionWrapper(F('resolved_at') - F('created_at'), output_field=DurationField())
    ).aggregate(avg=Avg('duration'))['avg']

    if avg_resolution:
        total_seconds = avg_resolution.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        avg_resolution_display = f"{hours}h {minutes}m"
    else:
        avg_resolution_display = "N/A"

    # This month
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    resolved_this_month = resolved_tickets.filter(resolved_at__gte=month_start).count()

    avg_rating = Feedback.objects.aggregate(avg=Avg('rating'))['avg'] or 0

    # Charts data
    by_status = list(all_tickets.values('status').annotate(count=Count('id')).order_by('status'))
    by_priority = list(all_tickets.values('priority').annotate(count=Count('id')).order_by('priority'))
    by_category = list(all_tickets.values('category__name').annotate(count=Count('id')).order_by('-count'))

    context = {
        'total_tickets': all_tickets.count(),
        'open_now': all_tickets.exclude(status__in=['resolved', 'closed']).count(),
        'critical_open': all_tickets.filter(priority='critical').exclude(status__in=['resolved', 'closed']).count(),
        'resolved_this_month': resolved_this_month,
        'avg_resolution_display': avg_resolution_display,
        'avg_rating': round(avg_rating, 2),
        'by_status': by_status,
        'by_priority': by_priority,
        'by_category': by_category,
        # JSON-safe lists for Chart.js
        'by_status_labels': [dict(Ticket.STATUS_CHOICES).get(s['status'], s['status']) for s in by_status],
        'by_status_values': [s['count'] for s in by_status],
        'by_priority_labels': [dict(Ticket.PRIORITY_CHOICES).get(p['priority'], p['priority']) for p in by_priority],
        'by_priority_values': [p['count'] for p in by_priority],
        'by_category_labels': [c['category__name'] or 'Uncategorized' for c in by_category],
        'by_category_values': [c['count'] for c in by_category],
    }
    return render(request, 'helpdesk/reports.html', context)


# ===================================================================
# PROFILE
# ===================================================================

@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('helpdesk:dashboard')
        messages.error(request, "Please correct the errors below.")
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'helpdesk/profile.html', {'form': form})


@login_required
def password_change_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully.")
            return redirect('helpdesk:dashboard')
        messages.error(request, "Please correct the errors below.")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'helpdesk/password_change.html', {'form': form})


# ===================================================================
# ERROR HANDLERS
# ===================================================================

def custom_404(request, exception):
    return render(request, '404.html', status=404)


def custom_500(request):
    return render(request, '500.html', status=500)