from rest_framework import serializers
from api.models import Song

class SongSerializer(serializers.ModelSerializer):
    class Meta:
        model = Song
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["artist"] = instance.artist.username
        return data
