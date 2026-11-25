
"""Gmail SMTP service for sending helpdesk ticket replies."""

import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()


def send_ticket_reply(customer_email, ticket_id, customer_message, agent_reply):
    """Send an agent's ticket reply to the customer's email."""

    sender_email = os.getenv("SMTP_EMAIL")
    app_password = os.getenv("SMTP_APP_PASSWORD")

    if not sender_email or not app_password:
        return False, "SMTP credentials are not configured."

    if not customer_email:
        return False, "Customer email address is not available."

    email = EmailMessage()
    email["Subject"] = f"Support Update - {ticket_id}"
    email["From"] = sender_email
    email["To"] = customer_email

    email.set_content(
        f"""Hello,

Our support team has responded to your support ticket.

Ticket ID: {ticket_id}

Your original complaint:
{customer_message}

Agent's response:
{agent_reply}

Thank you for contacting our support team.
"""
    )

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(email)

        return True, "Reply email sent successfully."

    except Exception as error:
        print(f"Email sending failed for {ticket_id}: {error}")
        return False, "Reply was saved, but email delivery failed."


def send_verification_email(recipient_email, verification_url):
    """Send a company email-verification link."""

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
    """Send a short-lived company account verification code."""
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
