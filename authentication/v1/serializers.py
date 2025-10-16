from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from authentication.utils import (
    get_client_ip,
    get_attempts,
    increment_attempts,
    reset_attempts,
    is_in_cooldown,
    is_locked,
    lock_account,
)
from django.conf import settings
from django.utils import timezone

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

        # Request context for IP and user-agent
        request = self.context.get("request")

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

        # Build identifier for tracking (avoid revealing existence)
        identifier = (email or username or "unknown").lower()
        ip = get_client_ip(request) if request is not None else "0.0.0.0"
        user_agent = None
        if request is not None:
            user_agent = request.META.get("HTTP_USER_AGENT")

        # Lazy import to avoid circulars
        from authentication.models import AuthEvent

        # Check lock/cooldown first
        if is_locked(identifier):
            # Log lock state hit
            AuthEvent.objects.create(
                user=user if user and user.is_authenticated else None,
                identifier=identifier,
                ip=ip,
                user_agent=user_agent,
                event_type=AuthEvent.TYPE_LOCKOUT,
            )
            from authentication.utils import AccountLockedError

            raise AccountLockedError()
        if is_in_cooldown(identifier, ip):
            # Log failed attempt under cooldown
            AuthEvent.objects.create(
                user=user if user and user.is_authenticated else None,
                identifier=identifier,
                ip=ip,
                user_agent=user_agent,
                event_type=AuthEvent.TYPE_FAILED_LOGIN,
            )
            from authentication.utils import CooldownError

            raise CooldownError()

        # Constant-time password check path; if user missing, simulate check duration
        password_ok = False
        if user is not None:
            password_ok = user.check_password(password)
        else:
            # Dummy work to reduce timing side channel
            from django.contrib.auth.hashers import make_password

            make_password(password)

        if not password_ok:
            attempts = increment_attempts(identifier, ip)

            # Lockout if threshold reached
            from django.conf import settings as dj_settings

            cfg = getattr(dj_settings, "LOGIN_SECURITY", {})
            lock_after = int(cfg.get("LOCK_AFTER", 5))
            cooldown_after = int(cfg.get("COOLDOWN_AFTER", 3))

            # TODO: logging handled in view/model later

            if attempts >= lock_after:
                lock_account(identifier)

                # Log lockout
                AuthEvent.objects.create(
                    user=user if user else None,
                    identifier=identifier,
                    ip=ip,
                    user_agent=user_agent,
                    event_type=AuthEvent.TYPE_LOCKOUT,
                )

                # Send email notification if we know the user
                if user and user.email:
                    try:
                        from services.email import send_email

                        subject = "Unusual activity on your account"
                        body = (
                            "We noticed multiple unsuccessful login attempts to your account.\n\n"
                            "If this wasn't you, please reset your password."
                        )
                        send_email(to=user.email, subject=subject, body=body)
                    except Exception:
                        # Do not fail auth flow due to email errors
                        pass

                from authentication.utils import AccountLockedError

                # Neutral message but clear lockout
                raise AccountLockedError()
            if attempts >= cooldown_after:
                # Log failed under cooldown threshold
                AuthEvent.objects.create(
                    user=user if user else None,
                    identifier=identifier,
                    ip=ip,
                    user_agent=user_agent,
                    event_type=AuthEvent.TYPE_FAILED_LOGIN,
                )
                from authentication.utils import CooldownError

                raise CooldownError()

            # Log generic failed attempt
            AuthEvent.objects.create(
                user=user if user else None,
                identifier=identifier,
                ip=ip,
                user_agent=user_agent,
                event_type=AuthEvent.TYPE_FAILED_LOGIN,
            )
            from authentication.utils import InvalidCredentialsError

            raise InvalidCredentialsError()

        # Success: reset attempts and do NOT block inactive users; generate tokens regardless
        reset_attempts(identifier, ip)
        # Optionally log success? We skip to reduce noise
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
