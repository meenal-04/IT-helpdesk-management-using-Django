"""
Management command: seed the database with demo users, categories, and tickets.

Usage:
    python manage.py create_test_data
    python manage.py create_test_data --reset   # deletes existing test data first
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from helpdesk.models import (
    Category, Ticket, UserProfile, TicketReply, InternalNote, Feedback, Notification
)


class Command(BaseCommand):
    help = "Populate the database with demo users and tickets."

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing test users and their tickets before seeding.',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING("Resetting demo data..."))
            demo_usernames = [
                'employee1', 'employee2', 'support1', 'support2'
            ]
            User.objects.filter(username__in=demo_usernames).delete()
            Ticket.objects.filter(subject__startswith='[DEMO]').delete()
            self.stdout.write(self.style.WARNING("  ✓ Demo data cleared"))

        self.stdout.write("Seeding demo data...\n")

        # ------------------------------------------------------------------
        # 1. Categories
        # ------------------------------------------------------------------
        categories = {
            'Hardware': 'Physical device issues (laptops, desktops, monitors)',
            'Software': 'Application and OS problems',
            'Network': 'Wi-Fi, VPN, internet connectivity',
            'Email': 'Outlook, mail sync, SMTP issues',
            'Account/Login': 'Password resets, account lockouts',
            'Printer': 'Printers and scanners',
            'Security': 'Phishing, malware, suspicious activity',
            'Other': 'Anything not covered above',
        }
        cat_map = {}
        for name, desc in categories.items():
            c, _ = Category.objects.get_or_create(name=name, defaults={'description': desc})
            cat_map[name] = c
        self.stdout.write(self.style.SUCCESS(f"  ✓ Categories ready ({len(categories)})"))

        # ------------------------------------------------------------------
        # 2. Users
        # ------------------------------------------------------------------
        def make_user(username, password, first, last, role,
                      department='', email=None, is_staff=False):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email or f'{username}@example.com',
                    'first_name': first,
                    'last_name': last,
                }
            )
            if created:
                user.set_password(password)
                user.is_staff = is_staff
                user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.department = department
            profile.save()
            return user

        employee1 = make_user('employee1', 'Employee123!', 'Alice', 'Employee',
                              'employee', department='Engineering')
        employee2 = make_user('employee2', 'Employee123!', 'Bob', 'Employee',
                              'employee', department='Finance')
        support1 = make_user('support1', 'Support123!', 'John', 'Support',
                             'support', department='IT Support', is_staff=True)
        support2 = make_user('support2', 'Support123!', 'Sarah', 'Support',
                             'support', department='IT Support', is_staff=True)

        self.stdout.write(self.style.SUCCESS("  ✓ 4 users ready"))
        self.stdout.write("      employee1 / Employee123!")
        self.stdout.write("      employee2 / Employee123!")
        self.stdout.write("      support1  / Support123!")
        self.stdout.write("      support2  / Support123!")

        # ------------------------------------------------------------------
        # 3. Demo Tickets
        # ------------------------------------------------------------------
        now = timezone.now()

        demos = [
            {
                'subject': '[DEMO] Laptop not connecting to Wi-Fi',
                'description': 'My laptop shows "connected" to office Wi-Fi but no websites load. '
                               'Other devices on the same network work fine.',
                'category': 'Network', 'priority': 'high', 'status': 'open',
                'employee': employee1, 'assigned_to': None,
            },
            {
                'subject': '[DEMO] Outlook not syncing emails',
                'description': 'Outlook stopped syncing since this morning. '
                               'No error message shown. Tried restarting Outlook — no luck.',
                'category': 'Email', 'priority': 'medium', 'status': 'assigned',
                'employee': employee1, 'assigned_to': support1,
            },
            {
                'subject': '[DEMO] Printer not responding',
                'description': 'The office printer on floor 3 shows offline. '
                               'Cannot print anything.',
                'category': 'Printer', 'priority': 'low', 'status': 'in_progress',
                'employee': employee2, 'assigned_to': support1,
            },
            {
                'subject': '[DEMO] Cannot access company VPN',
                'description': 'VPN client shows "authentication failed". '
                               'This is blocking all my remote work. Urgent.',
                'category': 'Network', 'priority': 'critical', 'status': 'assigned',
                'employee': employee2, 'assigned_to': support2,
            },
            {
                'subject': '[DEMO] Password reset link not working',
                'description': 'I requested a password reset but the emailed link says "expired". '
                               'Tried three times.',
                'category': 'Account/Login', 'priority': 'high', 'status': 'waiting',
                'employee': employee1, 'assigned_to': support1,
            },
        ]

        created_tickets = []
        for d in demos:
            t, created = Ticket.objects.get_or_create(
                subject=d['subject'],
                defaults={
                    'description': d['description'],
                    'category': cat_map[d['category']],
                    'priority': d['priority'],
                    'status': d['status'],
                    'employee': d['employee'],
                    'assigned_to': d['assigned_to'],
                }
            )
            if created:
                created_tickets.append(t)

        self.stdout.write(self.style.SUCCESS(f"  ✓ {len(created_tickets)} demo tickets created"))

        # ------------------------------------------------------------------
        # 4. Conversation on ticket #2
        # ------------------------------------------------------------------
        if len(created_tickets) >= 2:
            ticket2 = Ticket.objects.filter(subject__startswith='[DEMO] Outlook').first()
            if ticket2 and not ticket2.replies.exists():
                TicketReply.objects.create(
                    ticket=ticket2, author=employee1,
                    message="Still not working after restart. Can you take a look?"
                )
                TicketReply.objects.create(
                    ticket=ticket2, author=support1,
                    message="Thanks for reporting. I'll check your Outlook profile on the server. "
                            "Please keep Outlook closed for 10 minutes."
                )
                InternalNote.objects.create(
                    ticket=ticket2, author=support1,
                    note="Checked user's mailbox — 4.7 GB, close to quota. "
                         "Will request quota increase from Exchange admin."
                )
                self.stdout.write(self.style.SUCCESS("  ✓ Conversation + internal note added to ticket #2"))

        # ------------------------------------------------------------------
        # 5. A resolved + rated ticket (for reports)
        # ------------------------------------------------------------------
        resolved_exists = Ticket.objects.filter(
            subject__startswith='[DEMO] Resolved'
        ).exists()
        if not resolved_exists:
            resolved = Ticket.objects.create(
                subject='[DEMO] Resolved - Monitor flickering (historical)',
                description='Monitor flickering intermittently. Cable replaced.',
                category=cat_map['Hardware'],
                priority='medium',
                status='closed',
                employee=employee1,
                assigned_to=support1,
                resolution_summary='Display cable was loose/damaged. Replaced with new HDMI cable and tested — stable for 30 minutes.',
                created_at=now - timedelta(days=5),
                resolved_at=now - timedelta(days=4),
                closed_at=now - timedelta(days=3),
            )
            Feedback.objects.create(
                ticket=resolved, rating=5,
                comment='Fast and professional. Thank you!'
            )
            self.stdout.write(self.style.SUCCESS("  ✓ Historical resolved + rated ticket created"))

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS("Demo data seeding complete!"))
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(f"  Users       : {User.objects.count()}")
        self.stdout.write(f"  Categories  : {Category.objects.count()}")
        self.stdout.write(f"  Tickets     : {Ticket.objects.count()}")
        self.stdout.write(f"  Replies     : {TicketReply.objects.count()}")
        self.stdout.write(f"  Notifications: {Notification.objects.count()}")
        self.stdout.write("")
        self.stdout.write("Login credentials:")
        self.stdout.write("  Employee : employee1 / Employee123!")
        self.stdout.write("  Support  : support1  / Support123!")
        self.stdout.write("  Admin    : (your existing superuser)")
        self.stdout.write("")