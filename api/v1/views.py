from rest_framework.decorators import api_view
from rest_framework.response import Response
from api.models import Song, Interaction


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


@api_view(["GET"])
def cron(request):
    """cron run every 5 minutes to update static fields"""
    # update play_count, download_count, like_count, share_count, visit_count
    songs = Song.objects.all()
    for song in songs:
        try:
            interactions = Interaction.objects.filter(song=song).prefetch_related(
                "user"
            )

            song.play_count = interactions.filter(interaction_type="play").count()
            song.download_count = interactions.filter(
                interaction_type="download"
            ).count()
            song.like_count = interactions.filter(interaction_type="like").count()
            song.share_count = interactions.filter(interaction_type="share").count()
            song.visit_count = interactions.filter(interaction_type="visit").count()
            song.save()
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=500)

    return Response({"status": "ok"})
