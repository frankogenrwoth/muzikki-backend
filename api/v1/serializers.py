from rest_framework import serializers
from api.models import Song


class SongSerializer(serializers.ModelSerializer):
    artists = serializers.SerializerMethodField()

    class Meta:
        model = Song
        fields = [
            "id",
            "title",
            "description",
            "genre",
            "audio_url",
            "video_url",
            "cover_url",
            "play_count",
            "download_count",
            "like_count",
            "share_count",
            "visit_count",
            "duration",
            "release_date",
            "tags",
            "artists",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_artists(self, instance):
        return list(instance.artists.values("id", "username"))
