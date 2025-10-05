# Django Style Guide

This document outlines Django-specific coding standards for the muzikki-backend project.

## Project Structure

```
muzikki-backend/
├── manage.py
├── config/                 # Project configuration
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── apps/                   # Django applications
│   ├── users/
│   ├── api/
│   └── ...
├── static/
├── media/
├── templates/
└── docs/
```

## App Organization

Each Django app should follow this structure:

```
app_name/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── views.py
├── serializers.py
├── urls.py
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_views.py
│   └── test_serializers.py
└── migrations/
```

## Models

- Model names should be singular (e.g., `User`, not `Users`)
- Use `verbose_name` and `verbose_name_plural` for clarity
- Define `__str__` method for all models
- Use `Meta` class for model options
- Order fields logically (e.g., required first, then optional)

Example:
```python
from django.db import models

class Artist(models.Model):
    name = models.CharField(max_length=200)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Artist"
        verbose_name_plural = "Artists"
        ordering = ["-created_at"]
    
    def __str__(self):
        return self.name
```

## Views

- Use class-based views (CBVs) when appropriate
- For APIs, prefer Django REST Framework's generic views
- Keep business logic in models or service layers, not views

Example:
```python
from rest_framework import generics
from .models import Artist
from .serializers import ArtistSerializer

class ArtistListView(generics.ListCreateAPIView):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer
```

## URLs

- Use descriptive URL names
- Use namespaces for app URLs
- Prefer path() over url() in Django 2.0+

Example:
```python
from django.urls import path
from . import views

app_name = "artists"

urlpatterns = [
    path("", views.ArtistListView.as_view(), name="list"),
    path("<int:pk>/", views.ArtistDetailView.as_view(), name="detail"),
]
```

## Settings

- Split settings into multiple files (base, development, production)
- Never commit sensitive information (use environment variables)
- Use `django-environ` or similar for environment variable management

## Migrations

- Always review migrations before committing
- Use descriptive migration names when possible
- Never modify existing migrations that have been deployed

## Testing

- Write tests for all models, views, and serializers
- Use Django's `TestCase` or `TransactionTestCase`
- For API tests, use Django REST Framework's `APITestCase`
- Aim for high test coverage (>80%)

Example:
```python
from django.test import TestCase
from .models import Artist

class ArtistModelTest(TestCase):
    def setUp(self):
        self.artist = Artist.objects.create(name="Test Artist")
    
    def test_str_representation(self):
        self.assertEqual(str(self.artist), "Test Artist")
```

## Admin

- Register all models in admin.py
- Customize admin classes for better usability
- Use list_display, list_filter, and search_fields

Example:
```python
from django.contrib import admin
from .models import Artist

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name"]
```
