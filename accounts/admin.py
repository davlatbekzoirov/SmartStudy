from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Profile, EmailChangeRequest

User = get_user_model()


class ProfileInline(admin.StackedInline):
    """Allows editing the user profile directly from the User admin page."""
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'



@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'photo')
    search_fields = ('user__username', 'user__email')


@admin.register(EmailChangeRequest)
class EmailChangeRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'new_email', 'code', 'created_at', 'is_used', 'status_display')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__username', 'user__email', 'new_email', 'code')
    readonly_fields = ('created_at', 'code')
    actions = ['mark_as_used']

    @admin.display(description='Status')
    def status_display(self, obj):
        """Displays a quick readable status of the request."""
        if obj.is_used:
            return "Used"
        if obj.is_expired():
            return "Expired"
        return "Active"

    @admin.action(description='Mark selected requests as used')
    def mark_as_used(self, request, queryset):
        queryset.update(is_used=True)



admin.site.unregister(User)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)