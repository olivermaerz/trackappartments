"""
Main entry point for apartment tracker.

This module provides the scheduler that runs the scraper on a schedule with:
- Dynamic intervals based on whether new listings are found
- Random variation in intervals to appear more natural
- Quiet hours support (no scraping during specified hours)
- Automatic resumption after quiet hours end

The scheduler runs continuously, checking for new apartments at configurable
intervals. When new listings are found, it uses a shorter interval to check
more frequently (since new listings often appear in batches). After a period
with no new listings, it returns to the normal interval.

Example:
    Run the tracker:
    >>> python main.py
    
    The tracker will:
    - Run immediately on start
    - Check every 5 minutes (±3 min random) normally
    - Check every 1 minute (±0.5 min random) when new listings found
    - Skip scraping during quiet hours (9 PM - 8 AM by default)
"""
import time
import random
from datetime import datetime
from scraper import scrape_apartments, init_database
import config


def is_quiet_hours():
    """
    Check if the current time falls within the configured quiet hours.
    
    Quiet hours are periods when scraping should be paused (e.g., during
    nighttime). This function handles quiet hours that span midnight
    (e.g., 9 PM to 7 AM).
    
    Returns:
        bool: True if current time is within quiet hours, False otherwise.
            Also returns False if quiet hours are disabled in config.
    
    Examples:
        If QUIET_HOURS_START=21 and QUIET_HOURS_END=7:
        - 20:00 -> False (before start)
        - 21:00 -> True (at start)
        - 08:00 -> False (after end)
    
    Note:
        Quiet hours can be disabled by setting QUIET_HOURS_ENABLED=False
        in config.py.
    """
    if not config.QUIET_HOURS_ENABLED:
        return False
    
    now = datetime.now()
    current_hour = now.hour
    
    start_hour = config.QUIET_HOURS_START
    end_hour = config.QUIET_HOURS_END
    
    # Handle quiet hours that span midnight (e.g., 21:00 to 07:00)
    if start_hour > end_hour:
        return current_hour >= start_hour or current_hour < end_hour
    else:
        return start_hour <= current_hour < end_hour


def get_next_interval(new_listings_found=False):
    """
    Calculate the next scraping interval with random variation.
    
    This function determines how long to wait before the next scrape. It uses
    different intervals based on whether new listings were found:
    - Shorter interval when new listings found (to catch batches quickly)
    - Normal interval when no new listings (to avoid unnecessary requests)
    
    Random variation is added to make the scraping pattern appear more natural
    and less bot-like.
    
    Args:
        new_listings_found (bool, optional): Whether new listings were found
            in the last scrape. Defaults to False.
    
    Returns:
        float: Next interval in minutes (always at least 1 minute).
    
    Examples:
        With defaults (normal: 5±3, new: 1±0.5):
        >>> get_next_interval(False)  # Normal: 2-8 minutes
        >>> get_next_interval(True)   # New listings: 0.5-1.5 minutes
    
    Note:
        The interval is guaranteed to be at least 1 minute to avoid
        excessive requests.
    """
    if new_listings_found:
        # Shorter interval when new listings found
        base = config.SCRAPE_INTERVAL_NEW_LISTINGS_MINUTES
        random_variation = random.uniform(
            -config.SCRAPE_INTERVAL_NEW_LISTINGS_RANDOM_MINUTES,
            config.SCRAPE_INTERVAL_NEW_LISTINGS_RANDOM_MINUTES
        )
    else:
        # Normal interval
        base = config.SCRAPE_INTERVAL_MINUTES
        random_variation = random.uniform(
            -config.SCRAPE_INTERVAL_RANDOM_MINUTES,
            config.SCRAPE_INTERVAL_RANDOM_MINUTES
        )
    
    interval = max(1, base + random_variation)  # Ensure at least 1 minute
    return interval


def run_scraper_with_scheduling():
    """
    Run the scraper and determine the next interval based on results.
    
    This function:
    1. Checks if we're in quiet hours (skips scraping if so)
    2. Runs the scraper if not in quiet hours
    3. Determines next interval based on whether new listings were found
    4. Returns the next interval in minutes
    
    If quiet hours are active, it calculates when quiet hours end and returns
    that as the next interval, so scraping resumes automatically.
    
    Returns:
        float: Next interval in minutes until the next scrape should run.
    
    Side Effects:
        - Runs scrape_apartments() which may send notifications
        - Prints status messages to console
    
    Note:
        - Handles quiet hours that span midnight correctly
        - Always returns a positive interval (at least 1 minute)
    """
    # Check quiet hours
    if is_quiet_hours():
        now = datetime.now()
        print(f"⏸️  Quiet hours active ({now.strftime('%H:%M')}). Skipping scrape.")
        
        # Calculate time until quiet hours end
        end_hour = config.QUIET_HOURS_END
        current_hour = now.hour
        current_minute = now.minute
        
        if config.QUIET_HOURS_START > end_hour:  # Spans midnight
            if current_hour >= config.QUIET_HOURS_START:
                # We're in the evening/night part (e.g., 21:00-23:59)
                # Wait until next day's end_hour
                hours_until_end = (24 - current_hour) + end_hour
            else:
                # We're in the morning part (e.g., 00:00-06:59)
                # Wait until end_hour today
                hours_until_end = end_hour - current_hour
        else:
            # Quiet hours don't span midnight
            if current_hour < end_hour:
                hours_until_end = end_hour - current_hour
            else:
                hours_until_end = (24 - current_hour) + end_hour
        
        # Subtract current minutes and add some buffer
        minutes_until_end = (hours_until_end * 60) - current_minute + 5
        next_interval = max(1, minutes_until_end)  # At least 1 minute
        print(f"   Next scrape in {next_interval:.0f} minutes (at {end_hour:02d}:00)")
        return next_interval
    
    # Run scraper
    new_listings_count = scrape_apartments()
    
    # Determine next interval based on results
    new_listings_found = new_listings_count > 0
    next_interval = get_next_interval(new_listings_found)
    
    if new_listings_found:
        print(f"⚡ New listings found! Next check in {next_interval:.1f} minutes (shortened interval)")
    else:
        print(f"⏰ Next check in {next_interval:.1f} minutes")
    
    return next_interval


def run_scheduler():
    """
    Main scheduler loop that runs the scraper continuously.
    
    This function:
    1. Initializes and prints configuration
    2. Runs scraper immediately on start
    3. Enters infinite loop that:
       - Waits for calculated interval
       - Checks for quiet hours during wait
       - Runs scraper and gets next interval
       - Repeats
    
    The scheduler sleeps in 1-minute chunks to allow for:
    - Keyboard interrupt (Ctrl+C) to stop gracefully
    - Detection of quiet hours during long waits
    - More responsive behavior
    
    The function handles KeyboardInterrupt gracefully, allowing clean shutdown.
    
    Side Effects:
        - Prints startup configuration
        - Continuously runs scraper and prints status
        - Handles quiet hours automatically
    
    Example:
        >>> run_scheduler()
        🏠 Apartment Tracker started
        📅 Base interval: 5 minutes (±3 min)
        ⚡ Short interval (new listings): 1 minutes (±0.5 min)
        🌙 Quiet hours: 21:00 - 08:00
        ...
    
    Note:
        - Runs until interrupted with Ctrl+C
        - Automatically pauses during quiet hours
        - Resumes automatically when quiet hours end
    """
    print("🏠 Apartment Tracker started")
    print(f"📅 Base interval: {config.SCRAPE_INTERVAL_MINUTES} minutes (±{config.SCRAPE_INTERVAL_RANDOM_MINUTES} min)")
    print(f"⚡ Short interval (new listings): {config.SCRAPE_INTERVAL_NEW_LISTINGS_MINUTES} minutes (±{config.SCRAPE_INTERVAL_NEW_LISTINGS_RANDOM_MINUTES} min)")
    
    if config.QUIET_HOURS_ENABLED:
        print(f"🌙 Quiet hours: {config.QUIET_HOURS_START:02d}:00 - {config.QUIET_HOURS_END:02d}:00")
    else:
        print("🌙 Quiet hours: Disabled")
    
    print(f"🔔 Notifications via: {config.NOTIFICATION_METHOD}")
    print(f"💾 Database: {config.DATABASE_PATH}")
    print("\nPress Ctrl+C to stop\n")
    
    # Run immediately on start
    next_interval = run_scraper_with_scheduling()
    
    # Keep running with dynamic scheduling
    try:
        while True:
            # Wait for the calculated interval
            wait_seconds = next_interval * 60
            print(f"\n⏳ Waiting {next_interval:.1f} minutes until next scrape...\n")
            
            # Sleep in smaller chunks to allow for interruption
            sleep_chunk = 60  # Check every minute
            chunks = int(wait_seconds / sleep_chunk)
            remainder = wait_seconds % sleep_chunk
            
            for _ in range(chunks):
                time.sleep(sleep_chunk)
                # Check if we've entered quiet hours during wait
                if is_quiet_hours():
                    print(f"⏸️  Entered quiet hours. Pausing until {config.QUIET_HOURS_END:02d}:00")
                    # Wait until quiet hours end
                    while is_quiet_hours():
                        time.sleep(60)  # Check every minute
                    print("✅ Quiet hours ended. Resuming...")
                    break
            
            if remainder > 0:
                time.sleep(remainder)
            
            # Run scraper and get next interval
            next_interval = run_scraper_with_scheduling()
            
    except KeyboardInterrupt:
        print("\n\n👋 Stopping apartment tracker...")


if __name__ == "__main__":
    init_database()
    run_scheduler()

