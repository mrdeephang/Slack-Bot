import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import time
import requests
import schedule
from datetime import datetime, time as dt_time
from dotenv import load_dotenv
import pytz
from gita_quotes import get_random_quote, get_daily_quote  # Import our quotes

# Load environment variables from .env file
load_dotenv()

# Get configuration from environment variables
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')

# Nepal timezone
NEPAL_TIMEZONE = pytz.timezone('Asia/Kathmandu')

# Time restrictions in Nepal time (24-hour format)
START_TIME = dt_time(10, 0)  # 10:00 AM Nepal time
END_TIME = dt_time(23, 0)    # 6:00 PM Nepal time

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Bot is running!')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress default logging

def start_http_server():
    """Start HTTP server for Render health checks"""
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"Health check server running on port {port}")
    server.serve_forever()

def validate_config():
    if not SLACK_BOT_TOKEN:
        print("❌ ERROR: SLACK_BOT_TOKEN not found in .env file")
        return False
    
    if not CHANNEL_ID:
        print("❌ ERROR: CHANNEL_ID not found in .env file")
        return False
    
    if not SLACK_BOT_TOKEN.startswith('xoxb-'):
        print("❌ ERROR: Invalid SLACK_BOT_TOKEN format")
        return False
    
    if not CHANNEL_ID.startswith('C'):
        print("❌ ERROR: Invalid CHANNEL_ID format")
        return False
    
    return True

def get_nepal_time():
    """Get current time in Nepal timezone"""
    utc_now = pytz.utc.localize(datetime.utcnow())
    nepal_time = utc_now.astimezone(NEPAL_TIMEZONE)
    return nepal_time

def is_within_working_hours():
    """Check if current Nepal time is within working hours"""
    nepal_time = get_nepal_time()
    current_time = nepal_time.time()
    return START_TIME <= current_time <= END_TIME

def send_message():
    """Send a message with Bhagavad Gita wisdom if within working hours"""
    if not is_within_working_hours():
        nepal_time = get_nepal_time()
        current_time_str = nepal_time.strftime("%Y-%m-%d %H:%M:%S %Z%z")
        print(f"⏰ Outside working hours at {current_time_str} - skipping message")
        return
    
    url = "https://slack.com/api/chat.postMessage"
    
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    
    nepal_time = get_nepal_time()
    current_time_str = nepal_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Get a random quote from Bhagavad Gita
    wisdom_quote = get_random_quote()  # or use get_daily_quote()
    
    message = f"*Dear Devotee,*\n\n{wisdom_quote}\n\nRegards,\n*Shree Krishna*"
    
    payload = {
        "channel": CHANNEL_ID,
        "text": message,
        "username": "Krishna Bot",
        "icon_emoji": ":lotus_position:",
        "mrkdwn": True
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result["ok"]:
                print(f"✅ Message sent successfully at {current_time_str}")
                print(f"📜 Quote: {wisdom_quote[:50]}...")
            else:
                print(f"❌ Error sending message: {result.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_connection():
    """Test if the bot can connect to Slack"""
    url = "https://slack.com/api/auth.test"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}"
    }
    
    try:
        response = requests.post(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data["ok"]:
                print(f"✅ Connected as: {data['user']}")
                return True
            else:
                print(f"❌ Auth error: {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def log_status():
    """Log current status every hour"""
    nepal_time = get_nepal_time()
    current_time_str = nepal_time.strftime("%Y-%m-%d %H:%M:%S %Z%z")
    if is_within_working_hours():
        print(f"🟢 ACTIVE: Bot is running at {current_time_str}")
    else:
        print(f"🔴 IDLE: Outside working hours at {current_time_str}")

def check_and_send():
    """Check every minute if it's :00 or :30 in Nepal and send message"""
    nepal_time = get_nepal_time()
    minute = nepal_time.minute
    if minute in (0, 30):
        print(f"🕒 Sharp time check at {nepal_time.strftime('%H:%M')} NPT")
        send_message()

def main():
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()
    
    print("=" * 70)
    print("🚀 KRISHNA BOT WITH BHAGAVAD GITA WISDOM STARTING...")
    print("=" * 70)
    
    if not validate_config():
        return
    
    print(f"🔒 Configuration loaded from .env file")
    print(f"🎯 Target channel ID: {CHANNEL_ID}")
    print(f"🔑 Token: {SLACK_BOT_TOKEN[:12]}{'*' * 20}")
    print(f"⏰ Working hours (Nepal time): {START_TIME.strftime('%I:%M %p')} - {END_TIME.strftime('%I:%M %p')}")
    print(f"📅 Frequency: Every 30 minutes (Nepal time) at sharp :00 and :30")
    print(f"🔄 Status check: Every hour")
    print(f"📜 Wisdom: Random Bhagavad Gita quotes")
    print("-" * 70)
    
    if not test_connection():
        print("❌ Failed to connect to Slack. Check your bot token.")
        return
    
    nepal_time = get_nepal_time()
    print(f"⏰ Current Nepal time: {nepal_time.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
    
    if is_within_working_hours():
        print("✅ Currently within working hours - bot will send messages")
    else:
        print("⏰ Currently outside working hours - bot will wait")
    
    print("✅ Bot setup complete! Starting scheduled operation...")
    print("💡 Press Ctrl+C to stop the bot")
    print("-" * 70)
    
    # Schedule jobs
    schedule.every(1).minutes.do(check_and_send)  # check sharp times
    schedule.every().hour.do(log_status)          # status log
    
    log_status()
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n" + "=" * 70)
        print("👋 Bot stopped by user. Goodbye!")
        print("=" * 70)

if __name__ == "__main__":
    main()
