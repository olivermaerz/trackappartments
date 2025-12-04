"""
Notification system for apartment tracker.

This module provides functionality to send notifications when new apartment
listings are found. It supports multiple notification methods:
- Email notifications (SMTP)
- Push notifications via ntfy.sh
- macOS system notifications with sound

The module automatically sends system notifications (macOS) for all new listings,
and additionally sends via the configured method (email or ntfy) based on
settings in config.py.

Example:
    >>> from notifications import send_notification
    >>> send_notification(
    ...     message="New apartment found!",
    ...     html_message="<h1>New apartment</h1>",
    ...     image_url="https://example.com/image.jpg"
    ... )
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import subprocess
import platform
import config


def send_email_notification(message, subject="New Apartment Listing", html_message=None, image_url=None):
    """
    Send email notification via SMTP.
    
    Sends an email with both plain text and HTML versions. The HTML version
    can include an image URL that will be displayed in the email. Email
    credentials are loaded from environment variables via config.py.
    
    Args:
        message (str): Plain text message body
        subject (str, optional): Email subject line. Defaults to
            "New Apartment Listing".
        html_message (str, optional): HTML version of the message.
            If provided, email will be sent as multipart/alternative.
            Defaults to None.
        image_url (str, optional): URL to apartment image. This will be
            included in the HTML message as an <img> tag. Defaults to None.
    
    Returns:
        bool: True if email was sent successfully, False otherwise.
    
    Note:
        - Requires EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_TO, EMAIL_SMTP_SERVER,
          and EMAIL_SMTP_PORT to be set in .env file
        - Uses STARTTLS for secure connection
        - Prints error messages but doesn't raise exceptions
    """
    if not config.EMAIL_USERNAME or not config.EMAIL_PASSWORD or not config.EMAIL_TO:
        print("⚠ Email credentials not configured")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = config.EMAIL_USERNAME
        msg['To'] = config.EMAIL_TO
        msg['Subject'] = subject
        
        # Add plain text version
        msg.attach(MIMEText(message, 'plain'))
        
        # Add HTML version if provided
        # Note: We use image URLs directly in HTML instead of attaching images
        # This is more compatible with email clients like Apple Mail
        if html_message:
            msg.attach(MIMEText(html_message, 'html'))
        
        server = smtplib.SMTP(config.EMAIL_SMTP_SERVER, config.EMAIL_SMTP_PORT)
        server.starttls()
        server.login(config.EMAIL_USERNAME, config.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print("✓ Email notification sent")
        return True
    except Exception as e:
        print(f"✗ Error sending email: {e}")
        return False


def send_ntfy_notification(message, title="New Apartment Listing"):
    """
    Send push notification via ntfy.sh service.
    
    Sends a push notification to the configured ntfy.sh topic. Recipients
    subscribed to the topic will receive the notification on their devices.
    
    Args:
        message (str): Notification message body
        title (str, optional): Notification title. Defaults to
            "New Apartment Listing".
    
    Returns:
        bool: True if notification was sent successfully, False otherwise.
    
    Note:
        - Requires NTFY_TOPIC to be set in config.py or .env
        - Uses high priority for notifications
        - Prints error messages but doesn't raise exceptions
        - See https://ntfy.sh for more information about the service
    """
    if not config.NTFY_TOPIC:
        print("⚠ NTFY topic not configured")
        return False
    
    try:
        url = f"https://ntfy.sh/{config.NTFY_TOPIC}"
        response = requests.post(
            url,
            data=message.encode('utf-8'),
            headers={
                "Title": title,
                "Priority": "high"
            }
        )
        response.raise_for_status()
        print("✓ NTFY notification sent")
        return True
    except Exception as e:
        print(f"✗ Error sending NTFY notification: {e}")
        return False


def send_system_notification(title="New Apartment Listing", message="New apartment found!", sound=True):
    """
    Send macOS system notification with optional sound.
    
    Displays a native macOS notification using AppleScript. This provides
    immediate visual and audio feedback when new apartments are found.
    
    Args:
        title (str, optional): Notification title. Defaults to
            "New Apartment Listing".
        message (str, optional): Notification message body. Defaults to
            "New apartment found!".
        sound (bool, optional): Whether to play a sound with the notification.
            Uses macOS "Glass" sound. Defaults to True.
    
    Returns:
        bool: True if notification was sent successfully, False otherwise.
            Always returns False on non-macOS systems.
    
    Note:
        - Only works on macOS (Darwin)
        - Automatically escapes special characters for AppleScript
        - Uses osascript command-line tool
        - Prints error messages but doesn't raise exceptions
    """
    if platform.system() != "Darwin":  # macOS
        return False
    
    try:
        # Escape special characters for AppleScript
        title_escaped = title.replace('"', '\\"')
        message_escaped = message.replace('"', '\\"').replace('\n', ' ')
        
        # Build AppleScript command
        if sound:
            script = f'''
            display notification "{message_escaped}" with title "{title_escaped}" sound name "Glass"
            '''
        else:
            script = f'''
            display notification "{message_escaped}" with title "{title_escaped}"
            '''
        
        # Execute AppleScript
        subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
        print("✓ System notification sent")
        return True
    except Exception as e:
        print(f"⚠ Could not send system notification: {e}")
        return False


def send_notification(message, title="New Apartment Listing", html_message=None, image_url=None):
    """
    Send notification using the configured method.
    
    This is the main entry point for sending notifications. It:
    1. Always sends a macOS system notification (if on macOS)
    2. Additionally sends via the configured method (email or ntfy)
       based on config.NOTIFICATION_METHOD
    
    Args:
        message (str): Plain text notification message
        title (str, optional): Notification title. Defaults to
            "New Apartment Listing".
        html_message (str, optional): HTML version of the message (for email).
            Defaults to None.
        image_url (str, optional): URL to apartment image (for email).
            Defaults to None.
    
    Returns:
        bool: True if notification was sent successfully via the configured
            method, False otherwise. System notifications are always attempted
            but don't affect the return value.
    
    Note:
        - System notifications are always sent (if on macOS) regardless of
          configured method
        - Email method uses html_message and image_url if provided
        - NTFY method only uses plain text message
    """
    # Always send system notification with sound when new apartments are found
    send_system_notification(title, message, sound=True)
    
    # Also send via configured method (email or ntfy)
    if config.NOTIFICATION_METHOD == "email":
        return send_email_notification(message, title, html_message, image_url)
    elif config.NOTIFICATION_METHOD == "ntfy":
        return send_ntfy_notification(message, title)
    else:
        print(f"⚠ Unknown notification method: {config.NOTIFICATION_METHOD}")
        return False

