from django.contrib import admin

from .models import Song, SongCollaboration, Interaction

class SongCollaborationInline(admin.TabularInline):
    model = SongCollaboration
    extra = 1

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    inlines = [SongCollaborationInline]

@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    pass
