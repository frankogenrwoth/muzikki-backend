from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.conf import settings
from django.utils import timezone


class UserQuerySet(models.QuerySet):
    def artists(self):
        return self.filter(is_artist=True)

    def with_phone(self):
        return self.exclude(phonenumber__isnull=True).exclude(phonenumber="")

    def active(self):
        return self.filter(is_active=True)


class UserManager(DjangoUserManager.from_queryset(UserQuerySet)):
    pass


class User(AbstractUser):
    """
    Custom user model that supports both listeners and artists.
    Extends Django's AbstractUser for built-in auth features.
    """

    email = models.EmailField(unique=True)
    phonenumber = PhoneNumberField(blank=True, null=True, unique=True)
    is_artist = models.BooleanField(
        default=False, help_text="True if user is an artist"
    )

    profile_pic_url = models.URLField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    objects = UserManager()

    def become_artist(self, bio=None):
        """Promote a listener to artist."""
        self.is_artist = True
        if bio:
            self.bio = bio
        self.save()

    @property
    def profile_picture(self):
        return self.profile_pic_url

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.username


class AuthEvent(models.Model):
    """Security event for authentication activities.

    Stores minimal, non-sensitive metadata for monitoring failed logins and lockouts.
    """

    TYPE_FAILED_LOGIN = "failed_login"
    TYPE_LOCKOUT = "lockout"

    EVENT_TYPES = (
        (TYPE_FAILED_LOGIN, "Failed Login"),
        (TYPE_LOCKOUT, "Lockout"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    identifier = models.CharField(max_length=255, help_text="email or username used")
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    event_type = models.CharField(max_length=32, choices=EVENT_TYPES)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["identifier", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.event_type} {self.identifier} {self.ip} {self.created_at.isoformat()}"
