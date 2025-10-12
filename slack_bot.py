import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import time
import requests
import schedule
from datetime import datetime, time as dt_time
from dotenv import load_dotenv
import pytz
from gita_quotes import get_random_quote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Slack session with retry
session = requests.Session()
retry = Retry(
    total=3,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["POST"]
)
adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)

# Get configuration from .env
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')

# Nepal timezone
NEPAL_TIMEZONE = pytz.timezone('Asia/Kathmandu')

# Working hours
START_TIME = dt_time(10, 0)  # 10:00 AM
END_TIME = dt_time(23, 0)    # 11:00 PM


class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "status": "healthy",
                "service": "Krishna Bot",
                "timestamp": datetime.now().isoformat(),
                "nepal_time": get_nepal_time().isoformat()
            }
            import json
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress default HTTP logging


def start_http_server():
    """Start HTTP server for Render health checks"""
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Health check server running on port {port}")
    server.serve_forever()


def validate_config():
    if not SLACK_BOT_TOKEN:
        logger.error("SLACK_BOT_TOKEN not found in .env file")
        return False
    if not CHANNEL_ID:
        logger.error("CHANNEL_ID not found in .env file")
        return False
    if not SLACK_BOT_TOKEN.startswith('xoxb-'):
        logger.error("Invalid SLACK_BOT_TOKEN format")
        return False
    return True


def get_nepal_time():
    """Get current time in Nepal timezone"""
    utc_now = pytz.utc.localize(datetime.utcnow())
    return utc_now.astimezone(NEPAL_TIMEZONE)


def is_within_working_hours():
    """Check if current Nepal time is within working hours"""
    nepal_time = get_nepal_time()
    return START_TIME <= nepal_time.time() <= END_TIME


def send_message():
    """Send a message with Bhagavad Gita wisdom if within working hours"""
    if not is_within_working_hours():
        logger.debug(f"Outside working hours - skipping message")
        return

    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    nepal_time = get_nepal_time()
    wisdom_quote = get_random_quote()
    message = f"*Dear Devotee,*\n\n{wisdom_quote}\n\nRegards,\n*Shree Krishna*"

    payload = {
        "channel": CHANNEL_ID,
        "text": message,
        "username": "Krishna Bot",
        "icon_emoji": ":lotus_position:",
        "mrkdwn": True
    }

    try:
        response = session.post(url, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            result = response.json()
            if result["ok"]:
                logger.info(f"Message sent successfully at {nepal_time.strftime('%H:%M')}")
            else:
                logger.error(f"Error sending message: {result.get('error', 'Unknown error')}")
        else:
            logger.error(f"HTTP Error: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


def test_connection():
    """Test if the bot can connect to Slack"""
    url = "https://slack.com/api/auth.test"
    headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
    try:
        response = session.post(url, headers=headers, timeout=20)
        if response.status_code == 200:
            data = response.json()
            if data["ok"]:
                logger.info(f"Connected as: {data['user']}")
                return True
            else:
                logger.error(f"Auth error: {data.get('error', 'Unknown error')}")
                return False
        else:
            logger.error(f"HTTP Error: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Connection error: {e}")
        return False


def log_status():
    """Log current status"""
    nepal_time = get_nepal_time()
    if is_within_working_hours():
        logger.info(f"Status: ACTIVE at {nepal_time.strftime('%H:%M')} NPT")
    else:
        logger.info(f"Status: IDLE (outside working hours)")

# prod
# def check_and_send():
#     """Check every minute if it's :00 or :30 in Nepal and send message"""
#     nepal_time = get_nepal_time()
#     if nepal_time.minute in (0, 30):
#         logger.info(f"Sharp time trigger at {nepal_time.strftime('%H:%M')} NPT")
#         send_message()

# test
def check_and_send():
    if is_within_working_hours():
        send_message()


def main():
    # Start health check server in a separate thread
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()

    logger.info("=" * 50)
    logger.info("Krishna Bot Starting...")
    logger.info("=" * 50)

    if not validate_config():
        return

    logger.info(f"Target channel: {CHANNEL_ID}")
    logger.info(f"Working hours: {START_TIME.strftime('%H:%M')} - {END_TIME.strftime('%H:%M')} NPT")
    logger.info(f"Frequency: Every 30 minutes at :00 and :30")

    if not test_connection():
        logger.error("Failed to connect to Slack")
        return

    nepal_time = get_nepal_time()
    logger.info(f"Current Nepal time: {nepal_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    if is_within_working_hours():
        logger.info("Currently within working hours")
    else:
        logger.info("Currently outside working hours")

    logger.info("Bot setup complete - starting scheduled operation")

    # Schedule jobs
    schedule.every(1).minutes.do(check_and_send)
    schedule.every().hour.do(log_status)

    log_status()

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")


if __name__ == "__main__":
    main()