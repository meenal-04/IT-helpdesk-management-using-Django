"""
Forms for IT Helpdesk Management System.
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import (
    Ticket, 
    TicketReply, 
    InternalNote, 
    Feedback, 
    UserProfile,
    Category
)


class RegistrationForm(UserCreationForm):
    """Custom registration form with role selection and profile fields."""

    ROLE_CHOICES = [
        ('employee', 'Employee'),
        ('support', 'IT Support Staff'),
    ]

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@company.com'})
    )
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'})
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial='employee',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Finance, HR, Engineering'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'})
    )

    class Meta:
        model = User
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'password1', 'password2', 'role', 'department', 'phone'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Bootstrap classes to inherited fields
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            # Update the auto-created profile with role/department/phone
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = self.cleaned_data['role']
            profile.department = self.cleaned_data.get('department', '')
            profile.phone = self.cleaned_data.get('phone', '')
            profile.save()
        return user


class ProfileForm(forms.ModelForm):
    """Form for editing user profile info."""

    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = UserProfile
        fields = ('phone', 'department')
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate the initial values for the User fields
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile.save()
        return profile


class TicketCreateForm(forms.ModelForm):
    """Form for creating a new support ticket."""

    attachment = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx,.png,.jpg,.jpeg,.txt,.log'
        }),
        help_text="Optional. Max 5MB. Allowed: PDF, DOC, DOCX, PNG, JPG, TXT, LOG"
    )

    class Meta:
        model = Ticket
        fields = ('subject', 'category', 'priority', 'description')
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief summary of your issue (e.g., Laptop Wi-Fi not connecting)',
                'maxlength': 255,
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Describe your issue in detail. Include what you were doing, '
                               'any error messages, and steps you have already tried.'
            }),
        }
        labels = {
            'subject': 'Subject',
            'category': 'Category',
            'priority': 'Priority',
            'description': 'Description',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active categories
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
        self.fields['category'].empty_label = '-- Select a category --'

    def clean_attachment(self):
        """Validate attachment size (max 5MB)."""
        file = self.cleaned_data.get('attachment')
        if file:
            if file.size > 5 * 1024 * 1024:  # 5MB
                raise forms.ValidationError("File size must not exceed 5MB.")
        return file


class TicketReplyForm(forms.ModelForm):
    """Form for replying to a ticket (Phase 5)."""

    class Meta:
        model = TicketReply
        fields = ('message',)
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Type your reply...'
            }),
        }


class InternalNoteForm(forms.ModelForm):
    """Form for internal notes (Phase 5)."""

    class Meta:
        model = InternalNote
        fields = ('note',)
        widgets = {
            'note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Internal note (not visible to employee)...'
            }),
        }


class FeedbackForm(forms.ModelForm):
    """Form for employee feedback (Phase 9)."""

    class Meta:
        model = Feedback
        fields = ('rating', 'comment')
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Optional comments...'
            }),
        }