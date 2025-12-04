# Apartment Tracker for inberlinwohnen.de

Can't find an appartment in Berlin? Welcome to the club! I have put together a python script on MacOS to monitor the [inberlinwohnen.de](https://www.inberlinwohnen.de/wohnungsfinder) site for new entries that match certain criteria (configurable in the config.py). If a new appartment is available you get an email plus a notification on you mac. 

If you are on linux ot windows feel free to adapft the script. 

Automatically monitors for new apartment listings matching your criteria and sends notifications when new apartments are found.

## Features

- 🔍 Automated apartment search with customizable criteria
- 🔔 Email or push notifications (via ntfy.sh)
- 💾 Tracks seen listings to avoid duplicates
- ⏰ Runs automatically on a schedule
- 🖥️ Runs in background on macOS

## Setup

### 1. Create Virtual Environment (Recommended)

Create and activate a Python virtual environment to isolate dependencies:

```bash
cd trackappartment
python3 -m venv venv
source venv/bin/activate
```

**Important:** Always activate the virtual environment before running the scripts:
```bash
source venv/bin/activate
```

You'll know it's activated when you see `(venv)` in your terminal prompt.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install ChromeDriver

The script uses Selenium with Chrome. You need ChromeDriver:

**Option A: Using Homebrew (recommended on macOS)**
```bash
brew install chromedriver
```

**Option B: Manual installation**
- Download from https://chromedriver.chromium.org/
- Make sure it's in your PATH

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and configure your settings:

```bash
cp .env.example .env
```

Then edit `.env` with your actual values:

**For Email (Gmail):**
```env
NOTIFICATION_METHOD=email
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password  # Use App Password, not regular password
EMAIL_TO=your-email@gmail.com
```

**Important:** For Gmail, you need to use an App Password, not your regular password:
1. Go to your Google Account settings
2. Enable 2-Step Verification
3. Generate an App Password for "Mail"
4. Use that password in `EMAIL_PASSWORD`

**For ntfy.sh (Push Notifications):**
```env
NOTIFICATION_METHOD=ntfy
NTFY_TOPIC=your-topic-name
```

To use ntfy.sh:
1. Go to https://ntfy.sh
2. Create a topic (e.g., `apartment-alerts`)
3. Install the ntfy app on your iPhone
4. Subscribe to your topic
5. Set `NTFY_TOPIC=apartment-alerts` in `.env`

**Note:** The `.env` file is already in `.gitignore` and will not be committed to version control. Keep your credentials secure!

## Usage

**Remember to activate the virtual environment first:**
```bash
source venv/bin/activate
```

### Run Once (Test)

```bash
python scraper.py
```

### Run on Schedule

```bash
python main.py
```

This will:
- Run immediately
- Then check periodically based on your settings in `config.py`:
  - **Normal interval**: `SCRAPE_INTERVAL_MINUTES` ± random variation (default: 5 ± 3 minutes)
  - **Short interval when new listings found**: `SCRAPE_INTERVAL_NEW_LISTINGS_MINUTES` ± random variation (default: 1 ± 0.5 minutes)
  - **Quiet hours**: No scraping between `QUIET_HOURS_START` and `QUIET_HOURS_END` (default: 9 PM - 8 AM)

### Run in Background

**Option 1: Using nohup**
```bash
source venv/bin/activate
nohup python main.py > logs/output.log 2>&1 &
```

**Option 2: Using screen**
```bash
screen -S apartment-tracker
source venv/bin/activate
python main.py
# Press Ctrl+A then D to detach
# Reattach: screen -r apartment-tracker
```

**Option 3: Using tmux**
```bash
tmux new -s apartment-tracker
source venv/bin/activate
python main.py
# Press Ctrl+B then D to detach
# Reattach: tmux attach -t apartment-tracker
```

**Option 4: macOS LaunchAgent (Recommended for Production)**

Create `~/Library/LaunchAgents/com.trackapartment.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.trackapartment</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/wolf/dev/trackappartment/venv/bin/python3</string>
        <string>/Users/wolf/dev/trackappartment/main.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/wolf/dev/trackappartment/logs/output.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/wolf/dev/trackappartment/logs/error.log</string>
    <key>WorkingDirectory</key>
    <string>/Users/wolf/dev/trackappartment</string>
</dict>
</plist>
```

Then:
```bash
mkdir -p logs
launchctl load ~/Library/LaunchAgents/com.trackapartment.plist
```

## Database

Listings are stored in `apartments.db` (SQLite). You can inspect it:

```bash
sqlite3 apartments.db
.tables
SELECT * FROM listings;
```

## Configuration

### Search Criteria (`config.py`)

Edit `config.py` to adjust your search criteria:

```python
SEARCH_CRITERIA = {
    "kaltmiete_max": 440,  # Maximum cold rent in EUR
    "zimmer_min": 1,       # Minimum rooms
    "zimmer_max": 2,       # Maximum rooms
    "wohnflaeche_max": 50  # Maximum living area in m²
}
```

### Scraping Settings (`config.py`)

```python
SCRAPE_INTERVAL_MINUTES = 5  # Base interval for checking (will have randomness added)
SCRAPE_INTERVAL_RANDOM_MINUTES = 3  # Random variation: ±3 minutes
SCRAPE_INTERVAL_NEW_LISTINGS_MINUTES = 1  # Shorter interval when new listings found
SCRAPE_INTERVAL_NEW_LISTINGS_RANDOM_MINUTES = 0.5  # Random variation for new listings interval
HEADLESS_BROWSER = True  # Set to False to see the browser window

# Quiet hours (no scraping during this time)
QUIET_HOURS_ENABLED = True
QUIET_HOURS_START = 21  # 9 PM
QUIET_HOURS_END = 8     # 8 AM
```

### Environment Variables (`.env`)

All sensitive credentials and notification settings are stored in `.env`:
- Email settings (SMTP server, username, password, recipient)
- Notification method (email or ntfy)
- NTFY topic (if using ntfy.sh)

See `.env.example` for the template.

## Troubleshooting

- **ChromeDriver issues**: Make sure ChromeDriver version matches your Chrome version
- **Privacy banner not found**: The site might have already accepted cookies, or the selector needs updating
- **No listings found**: The website structure might have changed - check the HTML selectors in `scraper.py`
- **Email not working**: For Gmail, use an App Password, not your regular password. Make sure `.env` file exists and contains correct values.
- **Environment variables not loading**: Make sure `.env` file exists in the project root and contains all required variables

## Legal Notice

Please respect the website's terms of service and robots.txt. This tool is for personal use only. Consider adding delays between requests to avoid overloading the server.

