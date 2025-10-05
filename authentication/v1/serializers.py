from rest_framework import serializers
from authentication.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phonenumber",
            "first_name",
            "last_name",
            "is_artist",
            "profile_pic_url",
            "bio",
            "last_login",
            "date_joined",
            "is_active",
        ]
        read_only_fields = [
            "last_login",
            "date_joined",
            "is_active",
        ]
