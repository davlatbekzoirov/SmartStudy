from django.conf import settings
from django.db import models
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta


def profile_photo_path(instance, filename):
    ext = filename.split('.')[-1]
    return f'profile_photos/user_{instance.user_id}.{ext}'


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    photo = models.ImageField(upload_to=profile_photo_path, blank=True, null=True)

    def __str__(self):
        return f'Profile of {self.user.username}'


class EmailChangeRequest(models.Model):
    """Holds a pending email change until the user verifies it with a code."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_change_requests')
    new_email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    CODE_TTL_MINUTES = 15

    @classmethod
    def create_for(cls, user, new_email):
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        code = get_random_string(6, allowed_chars='0123456789')
        return cls.objects.create(user=user, new_email=new_email, code=code)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=self.CODE_TTL_MINUTES)

    def is_valid(self):
        return not self.is_used and not self.is_expired()