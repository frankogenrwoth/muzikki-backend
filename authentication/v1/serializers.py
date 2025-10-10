from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _

User = get_user_model()


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


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "phonenumber",
            "first_name",
            "last_name",
            "is_artist",
        ]

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.is_active = False
        user.save()
        # Send activation email
        try:
            from services.email import send_email

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            # Use FRONTEND_URL if provided to build a link the frontend can consume
            import os

            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            activation_link = f"{frontend_url}/auth/activate?uid={uid}&token={token}"
            subject = "Activate your account"
            body = (
                "Welcome to Muzikki!\n\n"
                "Please activate your account using the link below:\n"
                f"{activation_link}\n\n"
                "If you did not sign up, you can ignore this email."
            )
            send_email(to=user.email, subject=subject, body=body)
        except Exception:
            # In dev we don't want signup to fail due to email issues
            pass
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_new_password(self, value: str) -> str:
        validate_password(value)
        return value


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "phonenumber",
            "first_name",
            "last_name",
            "is_artist",
            "profile_pic_url",
            "bio",
        ]


from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Allow login even if user.is_active is False and support email or username.

    Fields accepted:
    - email + password, or
    - username + password
    """

    # Add optional email field; keep username for backward compatibility
    email = serializers.EmailField(required=False)

    def validate(self, attrs):
        # Prefer email if provided
        email = attrs.get("email")
        username = attrs.get(self.username_field)
        password = attrs.get("password")

        user = None
        if email:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                pass
        if user is None and username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                pass

        if user is None or not user.check_password(password):
            raise serializers.ValidationError(
                {"detail": "No active account found with the given credentials"}
            )

        # Do NOT block inactive users; generate tokens regardless
        data = {}
        refresh = self.get_token(user)

        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        # Optionally include user payload for convenience
        data["user"] = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
        }

        return data
