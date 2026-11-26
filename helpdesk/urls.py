from django.urls import path
from . import views

app_name = 'helpdesk'

urlpatterns = [
    # Auth
    path('', views.home_redirect, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboards
    path('dashboard/', views.dashboard_redirect, name='dashboard'),
    path('dashboard/employee/', views.employee_dashboard, name='employee_dashboard'),
    path('dashboard/support/', views.support_dashboard, name='support_dashboard'),

    # Tickets
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/create/', views.ticket_create, name='ticket_create'),
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<int:pk>/reply/', views.ticket_reply, name='ticket_reply'),
    path('tickets/<int:pk>/note/', views.ticket_add_note, name='ticket_add_note'),
    path('tickets/<int:pk>/assign/', views.ticket_assign, name='ticket_assign'),
    path('tickets/<int:pk>/update-status/', views.ticket_update_status, name='ticket_update_status'),
    path('tickets/<int:pk>/resolve/', views.ticket_resolve, name='ticket_resolve'),
    path('tickets/<int:pk>/reopen/', views.ticket_reopen, name='ticket_reopen'),
    path('tickets/<int:pk>/close/', views.ticket_close, name='ticket_close'),
    path('tickets/<int:pk>/feedback/', views.ticket_feedback, name='ticket_feedback'),
    path('tickets/<int:pk>/ai-assistance/', views.ticket_ai_assistance, name='ticket_ai_assistance'),

    # Notifications
    path('notifications/', views.notifications_list, name='notifications'),
    path('notifications/<int:pk>/read/', views.notification_read, name='notification_read'),
    path('notifications/read-all/', views.notifications_mark_all_read, name='notifications_mark_all_read'),

    # Reports
    path('reports/', views.reports_view, name='reports'),

    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/password/', views.password_change_view, name='password_change'),
]