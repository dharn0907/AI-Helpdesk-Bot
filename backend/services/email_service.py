
"""Email services for company ticket replies and platform verification emails."""

import os
import smtplib
import ssl
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()


def _send_smtp_message(
    email,
    smtp_host,
    smtp_port,
    smtp_username,
    smtp_password,
    smtp_security="starttls",
):
    """Send an email using the supplied SMTP server credentials."""

    if not all([smtp_host, smtp_port, smtp_username, smtp_password]):
        raise ValueError("SMTP configuration is incomplete.")

    smtp_port = int(smtp_port)
    smtp_security = (smtp_security or "starttls").lower()

    if smtp_security == "ssl":
        with smtplib.SMTP_SSL(
            smtp_host,
            smtp_port,
            timeout=20,
            context=ssl.create_default_context(),
        ) as server:
            server.login(smtp_username, smtp_password)
            server.send_message(email)

    elif smtp_security == "starttls":
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(smtp_username, smtp_password)
            server.send_message(email)

    elif smtp_security == "none":
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.login(smtp_username, smtp_password)
            server.send_message(email)

    else:
        raise ValueError("Unsupported SMTP security setting.")


def send_ticket_reply(
    customer_email,
    ticket_id,
    customer_message,
    agent_reply,
    support_email=None,
    smtp_host=None,
    smtp_port=587,
    smtp_username=None,
    smtp_password=None,
    smtp_security="starttls",
):
    """Send a ticket reply using the company's own SMTP account."""

    if not customer_email:
        return False, "Customer email address is not available."

    if not support_email:
        return False, "Verified company support email is not available."

    if not all([smtp_host, smtp_username, smtp_password]):
        return False, "Company SMTP credentials are not configured."

    email = EmailMessage()
    email["Subject"] = f"Support Update - {ticket_id}"
    email["From"] = support_email
    email["To"] = customer_email
    email["Reply-To"] = support_email

    email.set_content(
        f"""Hello,

Our support team has responded to your support ticket.

Ticket ID: {ticket_id}

Your original complaint:
{customer_message or "Not available"}

Agent's response:
{agent_reply}

Thank you for contacting our support team.
"""
    )

    try:
        _send_smtp_message(
            email=email,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            smtp_security=smtp_security,
        )

        return True, "Reply email sent successfully."

    except Exception as error:
        print(f"Company SMTP email failed for {ticket_id}: {error}")
        return False, "Reply was saved, but company email delivery failed."


def send_verification_email(recipient_email, verification_url):
    """Send a company email-verification link using platform SMTP."""

    sender_email = os.getenv("SMTP_EMAIL")
    app_password = os.getenv("SMTP_APP_PASSWORD")

    if not sender_email or not app_password:
        return False, "SMTP credentials are not configured."

    email = EmailMessage()
    email["Subject"] = "Verify your company email"
    email["From"] = sender_email
    email["To"] = recipient_email

    email.set_content(
        f"""Hello,

Please verify your company email address by opening this link:

{verification_url}

This link expires in 24 hours. If you did not request this, ignore this email.

Thank you.
"""
    )

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(email)

        return True, "Verification email sent."

    except Exception as error:
        print(f"Verification email failed: {error}")
        return False, "Could not send verification email."


def send_company_otp(recipient_email, otp):
    """Send a company account verification code using platform SMTP."""

    sender_email = os.getenv("SMTP_EMAIL")
    app_password = os.getenv("SMTP_APP_PASSWORD")

    if not sender_email or not app_password:
        return False, "SMTP credentials are not configured."

    email = EmailMessage()
    email["Subject"] = "Your company account verification code"
    email["From"] = sender_email
    email["To"] = recipient_email

    email.set_content(
        f"Your verification code is: {otp}\n\n"
        "This code expires in 10 minutes. Do not share it with anyone."
    )

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(email)

        return True, "OTP email sent."

    except Exception as error:
        print(f"Company OTP email failed: {error}")
        return False, "Could not send verification code."
