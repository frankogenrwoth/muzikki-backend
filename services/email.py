from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_email(
    *, to: str, subject: str, body: str, from_email: Optional[str] = None
) -> None:
    """Lightweight helper to send a simple plain-text email.

    Uses Django's email system so it respects EMAIL_* settings.
    """
    actual_from = from_email or getattr(
        settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"
    )
    message = EmailMultiAlternatives(
        subject=subject, body=body, from_email=actual_from, to=[to]
    )
    message.send(fail_silently=not getattr(settings, "DEBUG", False))


class EmailBase:
    """Base class for application emails.

    Subclasses should define required context via `required_context_keys` and either:
    - Provide template names (`subject_template`, `text_template`, optional `html_template`), OR
    - Override `build_content(context)` to return a (subject, text_body, html_body) tuple.
    """

    # Context keys that must be provided by the caller
    required_context_keys: Sequence[str] = ()

    # Optional Django template paths (relative to template dirs)
    subject_template: Optional[str] = None
    text_template: Optional[str] = None
    html_template: Optional[str] = None

    # Optional default sender override for this email type
    default_from_email: Optional[str] = None

    def __init__(self) -> None:
        # Load commonly used configuration lazily from Django settings.
        self._from_email = self.default_from_email or getattr(
            settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"
        )

    def validate_context(self, context: Mapping[str, object]) -> None:
        missing: Tuple[str, ...] = tuple(
            key for key in self.required_context_keys if key not in context
        )
        if missing:
            raise ValueError(f"Missing required context keys: {', '.join(missing)}")

    def build_content(
        self, context: Mapping[str, object]
    ) -> Tuple[str, str, Optional[str]]:
        """Return (subject, text_body, html_body?).

        By default this renders from templates if provided. Subclasses can
        override to fully control construction.
        """
        if not self.subject_template or not self.html_template:
            raise NotImplementedError(
                "Either provide subject_template and html_template or override build_content()"
            )

        subject: str = render_to_string(self.subject_template, context).strip()
        html_body: str = render_to_string(self.html_template, context)
        # Derive plain-text body from HTML so content is sourced from HTML
        text_body: str = strip_tags(html_body)
        return subject, text_body, html_body

    def preview(self, context: Mapping[str, object]) -> Dict[str, Optional[str]]:
        self.validate_context(context)
        subject, text_body, html_body = self.build_content(context)
        return {
            "from": self._from_email,
            "subject": subject,
            "text": text_body,
            "html": html_body,
        }

    def send(
        self,
        *,
        to: Iterable[str] | str,
        context: Mapping[str, object],
        from_email: Optional[str] = None,
        cc: Optional[Iterable[str]] = None,
        bcc: Optional[Iterable[str]] = None,
        reply_to: Optional[Iterable[str]] = None,
    ) -> None:
        """Render and send the email using Django's email backend.

        Respects standard Django EMAIL_* settings. If DEBUG is False, failures
        will raise; if True, failures are silenced for local development.
        """
        self.validate_context(context)
        subject, text_body, html_body = self.build_content(context)

        recipients: Iterable[str] = [to] if isinstance(to, str) else list(to)
        actual_from = from_email or self._from_email

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=actual_from,
            to=list(recipients),
            cc=list(cc) if cc else None,
            bcc=list(bcc) if bcc else None,
            reply_to=list(reply_to) if reply_to else None,
        )
        if html_body:
            msg.attach_alternative(html_body, "text/html")

        msg.send(fail_silently=getattr(settings, "DEBUG", False))
