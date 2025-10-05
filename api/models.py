from django.db import models
from django.db.models import TextChoices
from django.contrib.auth import get_user_model

User = get_user_model()


class Song(models.Model):
    artists = models.ManyToManyField(
        User, related_name="songs", blank=True, through="SongCollaboration"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    genre = models.CharField(max_length=100, blank=True, null=True)
    audio_url = models.URLField()
    video_url = models.URLField(blank=True, null=True)
    cover_url = models.URLField(blank=True, null=True)
    duration = models.PositiveIntegerField(
        help_text="Duration in seconds", null=True, blank=True
    )
    release_date = models.DateField(blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)

    play_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    share_count = models.PositiveIntegerField(default=0)
    visit_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class SongCollaboration(models.Model):
    song = models.ForeignKey(
        Song, on_delete=models.CASCADE, related_name="collaborations"
    )
    artist = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="collaborations"
    )
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Interaction(models.Model):
    class InteractionType(TextChoices):
        PLAY = "play", "Play"
        DOWNLOAD = "download", "Download"
        LIKE = "like", "Like"
        SHARE = "share", "Share"
        VISIT = "visit", "Visit"

    song = models.ForeignKey(
        Song, on_delete=models.CASCADE, related_name="interactions"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="interactions"
    )
    interaction_type = models.CharField(max_length=20, choices=InteractionType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} {self.interaction_type} {self.song.title}"
