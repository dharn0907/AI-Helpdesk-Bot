
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
