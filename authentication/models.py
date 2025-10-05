from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


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
