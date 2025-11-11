from django.contrib import admin

from .models import User, AuthEvent


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_active', 'date_joined')
    search_fields = ('username', 'email')
    list_filter = ('is_active', 'date_joined')

@admin.register(AuthEvent)
class AuthEventAdmin(admin.ModelAdmin):
    list_display = ('user', 'event_type', 'created_at', 'ip')
    search_fields = ('user__username', 'event_type', 'ip')
    list_filter = ('event_type', 'created_at')