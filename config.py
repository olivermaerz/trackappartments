"""
Configuration file for apartment tracker.

This module contains all configuration settings for the apartment tracker.
Sensitive credentials (email settings) are loaded from environment variables
via the .env file. Non-sensitive settings (search criteria, intervals, etc.)
are defined directly in this file.

Environment Variables:
    The following variables should be set in .env (see .env.example):
    - EMAIL_SMTP_SERVER: SMTP server address (e.g., smtp.gmail.com)
    - EMAIL_SMTP_PORT: SMTP server port (default: 587)
    - EMAIL_USERNAME: Email address for sending notifications
    - EMAIL_PASSWORD: Email password or app password
    - EMAIL_TO: Recipient email address

Usage:
    Import this module to access configuration:
    >>> import config
    >>> max_rent = config.SEARCH_CRITERIA["kaltmiete_max"]
    >>> interval = config.SCRAPE_INTERVAL_MINUTES
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# SEARCH CRITERIA
# ============================================================================
# These criteria are used to filter apartment listings on the website.
# The scraper will only extract listings that match ALL of these criteria.

SEARCH_CRITERIA = {
    "kaltmiete_max": 440,  # Maximum cold rent in EUR (excludes utilities)
    "zimmer_min": 1,       # Minimum number of rooms
    "zimmer_max": 2,       # Maximum number of rooms
    "wohnflaeche_max": 50  # Maximum living area in square meters
}

# ============================================================================
# WEBSITE CONFIGURATION
# ============================================================================

BASE_URL = "https://www.inberlinwohnen.de/wohnungsfinder"
"""Base URL of the apartment search website."""

# ============================================================================
# SCRAPING SETTINGS
# ============================================================================
# These settings control how often and when the scraper runs.

SCRAPE_INTERVAL_MINUTES = 5
"""Base interval between scrapes in minutes. Random variation will be added."""

SCRAPE_INTERVAL_RANDOM_MINUTES = 3
"""Random variation added to base interval: ±N minutes. Makes scraping pattern
less predictable and more human-like."""

SCRAPE_INTERVAL_NEW_LISTINGS_MINUTES = 1
"""Shorter interval used when new listings are found. Allows catching batches
of new listings quickly."""

SCRAPE_INTERVAL_NEW_LISTINGS_RANDOM_MINUTES = 0.5
"""Random variation for the new listings interval: ±N minutes."""

HEADLESS_BROWSER = True
"""Whether to run browser in headless mode (no visible window).
Set to False to see the browser window (useful for debugging)."""

# ============================================================================
# QUIET HOURS
# ============================================================================
# During quiet hours, scraping is paused to avoid unnecessary requests
# during times when new listings are unlikely (e.g., nighttime).

QUIET_HOURS_ENABLED = True
"""Whether quiet hours are enabled. Set to False to scrape 24/7."""

QUIET_HOURS_START = 21
"""Start of quiet hours in 24-hour format (21 = 9 PM)."""

QUIET_HOURS_END = 8
"""End of quiet hours in 24-hour format (8 = 8 AM).
If END < START, quiet hours span midnight (e.g., 9 PM to 8 AM)."""

# ============================================================================
# DATABASE SETTINGS
# ============================================================================

DATABASE_PATH = "apartments.db"
"""Path to SQLite database file for storing listings."""

# ============================================================================
# NOTIFICATION SETTINGS
# ============================================================================

NOTIFICATION_METHOD = os.getenv("NOTIFICATION_METHOD", "email")
"""Notification method: 'email' or 'ntfy'. Defaults to 'email'."""

# ============================================================================
# NTFY.SH SETTINGS
# ============================================================================
# Configure these if using ntfy.sh for push notifications.
# See https://ntfy.sh for more information.

NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")
"""NTFY topic name for push notifications. Leave empty if not using ntfy."""

# ============================================================================
# EMAIL SETTINGS
# ============================================================================
# These are loaded from environment variables (.env file) for security.
# See .env.example for the required format.

EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER")
"""SMTP server address (e.g., smtp.gmail.com)."""

EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
"""SMTP server port. Defaults to 587 (TLS)."""

EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
"""Email address for sending notifications."""

EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
"""Email password or app password. For Gmail, use an App Password."""

EMAIL_TO = os.getenv("EMAIL_TO")
"""Recipient email address for notifications."""



