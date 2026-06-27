from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib import messages
from .models import Profile

from .forms import (
    RegisterForm, ProfileUpdateForm,
    EmailChangeRequestForm, EmailChangeConfirmForm,
)
from .models import EmailChangeRequest
from .utils import send_email_change_code


def register_view(request):
    if request.user.is_authenticated:
        return redirect('smart_study:dashboard')
    form = RegisterForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Welcome, {user.username}!')
        return redirect('smart_study:dashboard')
    return render(request, 'accounts/auth.html', {'form': form, 'mode': 'register'})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('smart_study:dashboard')
    form = AuthenticationForm(request, data=request.POST or None)
    if form.is_valid():
        login(request, form.get_user())
        return redirect(request.GET.get('next', 'smart_study:dashboard'))
    return render(request, 'accounts/auth.html', {'form': form, 'mode': 'login'})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    form = ProfileUpdateForm(
        request.POST or None,
        request.FILES or None,
        instance=profile,
        user=request.user,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated.')
        return redirect('profile')
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def email_change_request_view(request):
    """Step 1: collect new email, send verification code."""
    form = EmailChangeRequestForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        new_email = form.cleaned_data['new_email']
        change_request = EmailChangeRequest.create_for(request.user, new_email)
        send_email_change_code(request.user, new_email, change_request.code)
        request.session['pending_email_change_id'] = change_request.id
        messages.info(request, f'We sent a verification code to {new_email}.')
        return redirect('email_change_confirm')
    return render(request, 'accounts/email_change_request.html', {'form': form})


@login_required
def email_change_confirm_view(request):
    """Step 2: verify the code, then actually update User.email."""
    change_id = request.session.get('pending_email_change_id')
    change_request = None
    if change_id:
        change_request = EmailChangeRequest.objects.filter(
            id=change_id, user=request.user
        ).first()

    if not change_request or not change_request.is_valid():
        messages.error(request, 'No pending email change, or your code expired. Please start again.')
        return redirect('email_change_request')

    form = EmailChangeConfirmForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        entered_code = form.cleaned_data['code']
        if entered_code == change_request.code:
            request.user.email = change_request.new_email
            request.user.save(update_fields=['email'])
            change_request.is_used = True
            change_request.save(update_fields=['is_used'])
            request.session.pop('pending_email_change_id', None)
            messages.success(request, 'Your email address has been updated.')
            return redirect('profile')
        else:
            form.add_error('code', 'Incorrect code, please try again.')

    return render(request, 'accounts/email_change_confirm.html', {
        'form': form,
        'new_email': change_request.new_email,
    })


@login_required
def password_change_view(request):
    form = PasswordChangeForm(user=request.user, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user) 
        messages.success(request, 'Your password was changed successfully.')
        return redirect('profile')
    return render(request, 'accounts/password_change.html', {'form': form})