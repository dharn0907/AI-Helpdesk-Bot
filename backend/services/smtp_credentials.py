import os
import smtplib
import ssl

from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()


def get_fernet():
    key = os.getenv("SMTP_CREDENTIAL_ENCRYPTION_KEY")

    if not key:
        raise RuntimeError("SMTP encryption key is not configured.")

    return Fernet(key.encode())


def encrypt_password(password):
    return get_fernet().encrypt(password.encode()).decode()


def decrypt_password(encrypted_password):
    return get_fernet().decrypt(encrypted_password.encode()).decode()


def open_smtp_connection(config):
    host = config["host"]
    port = int(config["port"])
    security = config.get("security", "starttls").lower()

    if security == "ssl":
        server = smtplib.SMTP_SSL(
            host,
            port,
            timeout=20,
            context=ssl.create_default_context()
        )
    elif security == "starttls":
        server = smtplib.SMTP(host, port, timeout=20)
        server.starttls(context=ssl.create_default_context())
    else:
        raise ValueError("Unsupported SMTP security setting.")

    try:
        server.login(
            config["username"],
            decrypt_password(config["password_encrypted"])
        )
        return server
    except Exception:
        server.quit()
        raise


def test_company_smtp(config):
    try:
        with open_smtp_connection(config) as server:
            server.noop()

        return True, "SMTP connection successful."

    except Exception as error:
        print(f"Company SMTP test failed: {error}")
        return False, "SMTP connection failed. Check host, port, security and credentials."


def send_company_ticket_reply(
    config,
    support_email,
    customer_email,
    ticket_id,
    customer_message,
    agent_reply
):
    from email.message import EmailMessage

    if not support_email:
        return False, "Verified company support email is missing."

    if not customer_email:
        return False, "Customer email address is not available."

    email = EmailMessage()
    email["Subject"] = f"Support Update - {ticket_id}"
    email["From"] = support_email
    email["To"] = customer_email
    email["Reply-To"] = support_email

    email.set_content(f"""Hello,

Our support team has responded to your support ticket.

Ticket ID: {ticket_id}

Your original complaint:
{customer_message or "Not available"}

Agent's response:
{agent_reply}

Thank you for contacting our support team.
""")

    try:
        with open_smtp_connection(config) as server:
            server.send_message(email)

        return True, "Company ticket reply email sent successfully."

    except Exception as error:
        print(f"Company SMTP email failed for {ticket_id}: {error}")
        return False, "Reply was saved, but company email delivery failed."
