from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with that email already exists.')
        return email


class ProfileUpdateForm(forms.ModelForm):
    """Edits username + full name (on User) and photo (on Profile) together."""
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150, required=False, label='First name')
    last_name = forms.CharField(max_length=150, required=False, label='Last name')

    class Meta:
        model = Profile
        fields = ['photo']

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['username'].initial = user.username
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name

    def clean_username(self):
        username = self.cleaned_data['username']
        qs = User.objects.filter(username__iexact=username).exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError('That username is already taken.')
        return username

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.username = self.cleaned_data['username']
        self.user.first_name = self.cleaned_data['first_name']
        self.user.last_name = self.cleaned_data['last_name']
        if commit:
            self.user.save()
            profile.save()
        return profile


class EmailChangeRequestForm(forms.Form):
    """Step 1: user enters the new email, we send them a code."""
    new_email = forms.EmailField(
        label='New email address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 
            'placeholder': 'name@example.com'
        })
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_email(self):
        email = self.cleaned_data['new_email']
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError('That email is already in use by another account.')
        if email.lower() == self.user.email.lower():
            raise forms.ValidationError('That is already your current email address.')
        return email


class EmailChangeConfirmForm(forms.Form):
    """Step 2: user enters the code we emailed them."""
    code = forms.CharField(
        max_length=6, 
        label='Verification code',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': '123456',
            'style': 'text-align: center; font-size: 20px; letter-spacing: 4px;'
        })
    )