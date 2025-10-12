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
import json
from urllib.parse import urlparse, parse_qs

# ------------------ CONFIG & SETUP ------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()

session = requests.Session()
retry = Retry(
    total=3,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["POST"]
)
adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)

# --- ENV Variables ---
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
SLACK_CLIENT_ID = os.getenv('SLACK_CLIENT_ID')
SLACK_CLIENT_SECRET = os.getenv('SLACK_CLIENT_SECRET')
BASE_URL = os.getenv('BASE_URL', 'https://slack-bot-b653.onrender.com')

NEPAL_TIMEZONE = pytz.timezone('Asia/Kathmandu')
START_TIME = dt_time(10, 0)
END_TIME = dt_time(23, 0)

# Temporary storage for installed workspace tokens
WORKSPACE_TOKENS = {}


# ------------------ UTILITY FUNCTIONS ------------------

def get_nepal_time():
    utc_now = pytz.utc.localize(datetime.utcnow())
    return utc_now.astimezone(NEPAL_TIMEZONE)


def is_within_working_hours():
    nepal_time = get_nepal_time()
    return START_TIME <= nepal_time.time() <= END_TIME


def validate_config():
    if not SLACK_BOT_TOKEN or not SLACK_BOT_TOKEN.startswith('xoxb-'):
        logger.error("Invalid or missing SLACK_BOT_TOKEN")
        return False
    if not CHANNEL_ID:
        logger.error("CHANNEL_ID not found in .env file")
        return False
    return True


# ------------------ SLACK FUNCTIONS ------------------

def send_message():
    if not is_within_working_hours():
        logger.debug("Outside working hours - skipping message")
        return

    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    nepal_time = get_nepal_time()
    message = f"*Dear Devotee,*\n\n{get_random_quote()}\n\nRegards,\n*Shree Krishna*"

    payload = {
        "channel": CHANNEL_ID,
        "text": message,
        "username": "Krishna Bot",
        "icon_emoji": ":lotus_position:",
        "mrkdwn": True
    }

    try:
        response = session.post(url, headers=headers, json=payload, timeout=20)
        data = response.json()
        if response.status_code == 200 and data.get("ok"):
            logger.info(f"Message sent successfully at {nepal_time.strftime('%H:%M')} NPT")
        else:
            logger.error(f"Slack error: {data.get('error', 'unknown')} ({response.status_code})")
    except Exception as e:
        logger.error(f"Error sending message: {e}")


def test_connection():
    url = "https://slack.com/api/auth.test"
    headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
    try:
        response = session.post(url, headers=headers, timeout=20)
        data = response.json()
        if data.get("ok"):
            logger.info(f"Connected as: {data['user']}")
            return True
        else:
            logger.error(f"Auth error: {data.get('error')}")
            return False
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False


# ------------------ OAUTH HANDLER ------------------

def handle_oauth_callback(query_params):
    code = query_params.get("code", [None])[0]
    if not code:
        return (400, {"error": "Missing 'code' parameter"})

    oauth_url = "https://slack.com/api/oauth.v2.access"
    payload = {
        "client_id": SLACK_CLIENT_ID,
        "client_secret": SLACK_CLIENT_SECRET,
        "code": code,
        "redirect_uri": f"{BASE_URL}/slack/oauth_redirect"
    }

    try:
        response = requests.post(oauth_url, data=payload)
        data = response.json()
        if data.get("ok"):
            team_id = data["team"]["id"]
            access_token = data["access_token"]
            WORKSPACE_TOKENS[team_id] = access_token
            logger.info(f"✅ Installed successfully for team {team_id}")
            return (200, {"message": "App installed successfully!", "team_id": team_id})
        else:
            logger.error(f"OAuth failed: {data.get('error')}")
            return (400, {"error": data.get("error", "OAuth failed")})
    except Exception as e:
        logger.error(f"OAuth exception: {e}")
        return (500, {"error": str(e)})


# ------------------ HTTP SERVER ------------------

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query_params = parse_qs(parsed.query)

        if path == '/':
            self._respond(200, {"service": "Krishna Bot", "status": "running"})
        elif path == '/health':
            self._respond(200, {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "nepal_time": get_nepal_time().isoformat()
            })
        elif path == '/slack/oauth_redirect':
            status, response = handle_oauth_callback(query_params)
            self._respond(status, response)
        else:
            self._respond(404, {"error": "Not found"})

    def _respond(self, status, payload):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def log_message(self, format, *args):
        return


def start_http_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"HTTP server running on port {port}")
    server.serve_forever()


# ------------------ SCHEDULER ------------------

def log_status():
    nepal_time = get_nepal_time()
    if is_within_working_hours():
        logger.info(f"Status: ACTIVE at {nepal_time.strftime('%H:%M')} NPT")
    else:
        logger.info("Status: IDLE (outside working hours)")


def check_and_send():
    nepal_time = get_nepal_time()
    if nepal_time.minute in (0, 30):
        logger.info(f"Trigger at {nepal_time.strftime('%H:%M')} NPT")
        send_message()


# ------------------ MAIN ------------------

def main():
    threading.Thread(target=start_http_server, daemon=True).start()

    logger.info("=" * 60)
    logger.info("🪷 Starting Krishna Bot with OAuth enabled 🪷")
    logger.info("=" * 60)

    if not validate_config():
        return

    if not test_connection():
        logger.error("Failed to connect to Slack")
        return

    logger.info(f"Channel: {CHANNEL_ID}")
    logger.info(f"Working hours: {START_TIME.strftime('%H:%M')} - {END_TIME.strftime('%H:%M')} NPT")

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
