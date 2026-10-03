import html
import logging
import smtplib
from email.message import EmailMessage

from src.core import config

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, text_body: str, html_body: str | None = None) -> None:
    message = EmailMessage()
    message["From"] = config.SMTP_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    smtp_cls = smtplib.SMTP_SSL if config.SMTP_SECURITY == "ssl" else smtplib.SMTP
    with smtp_cls(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as smtp:
        if config.SMTP_SECURITY == "starttls":
            smtp.starttls()
        if config.SMTP_USERNAME:
            smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
        smtp.send_message(message)


def send_email_safely(to: str, subject: str, text_body: str, html_body: str | None = None) -> None:
    """For background tasks: a failed send must not crash the worker."""
    try:
        send_email(to, subject, text_body, html_body)
    except Exception:
        logger.exception("Failed to send email to %s", to)


def send_otp_email(to: str, full_name: str, code: str, purpose_label: str) -> None:
    minutes = config.OTP_EXPIRE_MINUTES
    subject = f"[Beako] Mã OTP {purpose_label}"
    text_body = (
        f"Xin chào {full_name},\n\n"
        f"Mã OTP {purpose_label} của bạn là: {code}\n"
        f"Mã có hiệu lực trong {minutes} phút. Không chia sẻ mã này với bất kỳ ai.\n\n"
        "Nếu bạn không yêu cầu, hãy bỏ qua email này."
    )
    html_body = (
        f"<p>Xin chào {html.escape(full_name)},</p>"
        f"<p>Mã OTP {purpose_label} của bạn là:</p>"
        f'<p style="font-size:28px;font-weight:bold;letter-spacing:6px">{code}</p>'
        f"<p>Mã có hiệu lực trong {minutes} phút. Không chia sẻ mã này với bất kỳ ai.</p>"
        "<p>Nếu bạn không yêu cầu, hãy bỏ qua email này.</p>"
    )
    send_email_safely(to, subject, text_body, html_body)
