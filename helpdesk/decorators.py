"""
Custom decorators for role-based access control.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def role_required(*allowed_roles):
    """
    Decorator to restrict view access to specific roles.
    
    Usage:
        @role_required('employee')
        @role_required('support', 'admin')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            try:
                profile = request.user.profile
                if profile.role in allowed_roles or request.user.is_superuser:
                    return view_func(request, *args, **kwargs)
            except AttributeError:
                pass
            
            messages.error(request, "You don't have permission to access this page.")
            return redirect('helpdesk:dashboard')
        return wrapper
    return decorator


def employee_required(view_func):
    """Shortcut for employee-only views."""
    return role_required('employee')(view_func)


def support_required(view_func):
    """Shortcut for support staff and admin views."""
    return role_required('support', 'admin')(view_func)


def admin_required(view_func):
    """Shortcut for admin-only views."""
    return role_required('admin')(view_func)