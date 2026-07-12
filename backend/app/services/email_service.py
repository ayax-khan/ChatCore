import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_host = getattr(settings, "SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = getattr(settings, "SMTP_PORT", 587)
        self.smtp_user = getattr(settings, "SMTP_USER", None)
        self.smtp_password = getattr(settings, "SMTP_PASSWORD", None)
        self.from_email = getattr(settings, "FROM_EMAIL", "noreply@chatcore.dev")
        self.from_name = getattr(settings, "FROM_NAME", "ChatCore")

    def send(self, to: str, subject: str, body_text: str, body_html: Optional[str] = None) -> bool:
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP not configured. Email not sent.")
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to
            msg["Subject"] = subject

            msg.attach(MIMEText(body_text, "plain"))
            if body_html:
                msg.attach(MIMEText(body_html, "html"))

            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to, msg.as_string())

            logger.info(f"Email sent to {to}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            return False

    def send_welcome(self, to: str, business_name: str):
        subject = f"Welcome to ChatCore, {business_name}!"
        text = f"""
Hi {business_name},

Welcome to ChatCore! Your AI-powered chatbot is ready to help your website visitors.

Getting started:
1. Add your website URL in the dashboard
2. Customize the chat widget appearance
3. Embed the widget script on your site
4. Let the AI crawl and index your content

Need help? Check our documentation or reply to this email.

Best regards,
The ChatCore Team
"""
        html = f"""
<html><body>
<h2>Welcome to ChatCore!</h2>
<p>Your AI-powered chatbot is ready to help your website visitors.</p>
<h3>Getting Started:</h3>
<ol>
<li>Add your website URL in the dashboard</li>
<li>Customize the chat widget appearance</li>
<li>Embed the widget script on your site</li>
<li>Let the AI crawl and index your content</li>
</ol>
<p>Need help? Check our documentation or reply to this email.</p>
<p>Best regards,<br>The ChatCore Team</p>
</body></html>"""
        return self.send(to, subject, text, html)

    def send_crawl_notification(self, to: str, site_name: str, status: str, pages_count: int):
        subject = f"Crawl {status}: {site_name}"
        text = f"""
Site: {site_name}
Status: {status}
Pages indexed: {pages_count}

View details: https://app.chatcore.dev/dashboard/sites
"""
        return self.send(to, subject, text)

    def send_lead_notification(self, to: str, lead_email: str, lead_name: Optional[str], question: Optional[str]):
        subject = f"New Lead: {lead_email}"
        name = lead_name or "Unknown"
        q = question or "No question provided"
        text = f"""
New lead captured!

Name: {name}
Email: {lead_email}
Question: {q}

View in dashboard: https://app.chatcore.dev/dashboard/analytics
"""
        return self.send(to, subject, text)

    def send_daily_summary(self, to: str, stats: dict):
        subject = f"ChatCore Daily Summary - {stats.get('date', 'Today')}"
        text = f"""
Daily Summary for {stats.get('date', 'Today')}

Chats: {stats.get('chats', 0)}
Messages: {stats.get('messages', 0)}
New Leads: {stats.get('leads', 0)}
AI Cost: ${stats.get('cost', 0)}

View full analytics: https://app.chatcore.dev/dashboard/analytics
"""
        return self.send(to, subject, text)
