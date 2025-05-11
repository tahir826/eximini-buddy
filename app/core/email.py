import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_email(email_to: str, subject: str, html_content: str):
    message = MIMEMultipart()
    message["From"] = settings.EMAIL_USER
    message["To"] = email_to
    message["Subject"] = subject
    
    message.attach(MIMEText(html_content, "html"))
    
    try:
        logger.info(f"Connecting to SMTP server: {settings.SMTP_SERVER}:{settings.SMTP_PORT}")
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            logger.info("Starting TLS")
            server.starttls()
            logger.info(f"Logging in with user: {settings.EMAIL_USER}")
            server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
            logger.info(f"Sending email to: {email_to}")
            server.send_message(message)
            logger.info("Email sent successfully")
        return {"status": "success", "message": "Email sent successfully"}
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return {"status": "error", "message": str(e)}