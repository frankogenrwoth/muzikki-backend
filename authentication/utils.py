from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework.exceptions import APIException


def _security_settings():
    cfg = getattr(settings, "LOGIN_SECURITY", {})
    return {
        "FAILED_WINDOW_MIN": int(cfg.get("FAILED_WINDOW_MIN", 10)),
        "COOLDOWN_AFTER": int(cfg.get("COOLDOWN_AFTER", 3)),
        "LOCK_AFTER": int(cfg.get("LOCK_AFTER", 5)),
        "LOCK_DURATION_MIN": int(cfg.get("LOCK_DURATION_MIN", 15)),
    }


def _attempts_key(identifier: str, ip: str) -> str:
    return f"login:attempts:{identifier}:{ip}"


def _lock_key(identifier: str) -> str:
    return f"login:lock:{identifier}"


def get_client_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        # Take the first IP in the list (closest to client)
        ip = xff.split(",")[0].strip()
        return ip
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def get_attempts(identifier: str, ip: str) -> int:
    return int(cache.get(_attempts_key(identifier, ip)) or 0)


def increment_attempts(identifier: str, ip: str) -> int:
    cfg = _security_settings()
    key = _attempts_key(identifier, ip)
    attempts = cache.get(key)
    if attempts is None:
        attempts = 0
    attempts = int(attempts) + 1
    # Set/refresh TTL to window
    cache.set(key, attempts, timeout=cfg["FAILED_WINDOW_MIN"] * 60)
    return attempts


def reset_attempts(identifier: str, ip: str) -> None:
    cache.delete(_attempts_key(identifier, ip))


def is_in_cooldown(identifier: str, ip: str) -> bool:
    cfg = _security_settings()
    attempts = get_attempts(identifier, ip)
    return attempts >= cfg["COOLDOWN_AFTER"] and not is_locked(identifier)


def is_locked(identifier: str) -> bool:
    return cache.get(_lock_key(identifier)) is not None


def lock_account(identifier: str) -> None:
    cfg = _security_settings()
    # value can be timestamp of unlock for debugging/visibility
    unlock_at = timezone.now() + timezone.timedelta(minutes=cfg["LOCK_DURATION_MIN"])
    cache.set(
        _lock_key(identifier), str(unlock_at), timeout=cfg["LOCK_DURATION_MIN"] * 60
    )


class CooldownError(APIException):
    status_code = 429
    default_detail = "Incorrect username or password. Please try again in a moment."
    default_code = "cooldown"


class AccountLockedError(APIException):
    status_code = 403
    default_detail = "Your account has been locked due to multiple failed sign-in attempts. Please try again later or reset your password."
    default_code = "account_locked"


class InvalidCredentialsError(APIException):
    status_code = 401
    default_detail = "Incorrect username or password."
    default_code = "invalid_credentials"
