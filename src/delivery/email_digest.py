"""Email delivery module for daily digest."""
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from src.config import get_config

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"

def generate_html_digest(listings: List[dict], stats: dict) -> str:
    """Generate HTML email body from Jinja2 template."""
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("daily_digest.html")
    
    # Sort and take top 10
    top_deals = sorted(listings, key=lambda x: x.get("score", 0), reverse=True)[:10]
    
    html_content = template.render(
        date=datetime.now().strftime("%B %d, %Y"),
        total_scanned=stats.get("total_scanned", 0),
        avg_score=stats.get("avg_score", 0),
        num_1pct=sum(1 for d in listings if d.get("meets_1pct_rule")),
        deals=top_deals,
    )
    
    return html_content


def send_daily_digest(listings: List[dict], recipients: List[str], stats: dict) -> bool:
    """Send the daily digest via SendGrid."""
    config = get_config()
    api_key = config["delivery"].get("sendgrid_api_key")
    from_email = config["delivery"].get("from_email")
    subject_template = config["delivery"].get("digest_subject", "BPM Daily Deal Feed — {date}")
    
    if not api_key or api_key == "YOUR_SENDGRID_KEY":
        logger.warning("SendGrid API key not configured. Skipping email delivery.")
        return False
        
    if not recipients:
        logger.warning("No recipients provided for email digest.")
        return False
        
    html_content = generate_html_digest(listings, stats)
    subject = subject_template.format(date=datetime.now().strftime("%Y-%m-%d"))
    
    message = Mail(
        from_email=from_email,
        to_emails=recipients,
        subject=subject,
        html_content=html_content,
    )
    
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        logger.info(f"Email sent successfully. Status code: {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email digest: {e}")
        return False
