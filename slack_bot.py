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
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
BASE_URL = os.getenv("BASE_URL")
PORT = int(os.getenv("PORT", 10000))

NEPAL_TIMEZONE = pytz.timezone("Asia/Kathmandu")
START_TIME = dt_time(10, 0)
END_TIME = dt_time(23, 0)

WORKSPACES_FILE = "workspaces.json"

# ---------------------------------------------
# JSON storage functions
# ---------------------------------------------
def load_workspaces():
    try:
        with open(WORKSPACES_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_workspace(team_id, bot_token, channel_id):
    workspaces = load_workspaces()
    workspaces[team_id] = {"bot_token": bot_token, "channel_id": channel_id}
    with open(WORKSPACES_FILE, "w") as f:
        json.dump(workspaces, f)

# ---------------------------------------------
# Health check server
# ---------------------------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {
                "status": "healthy",
                "service": "Krishna Bot",
                "timestamp": datetime.now().isoformat(),
                "nepal_time": get_nepal_time().isoformat()
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, format, *args):
        pass  # suppress logging

def start_http_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
    logger.info(f"Health check server running on port {PORT}")
    server.serve_forever()

# ---------------------------------------------
# Time helpers
# ---------------------------------------------
def get_nepal_time():
    utc_now = pytz.utc.localize(datetime.utcnow())
    return utc_now.astimezone(NEPAL_TIMEZONE)

def is_within_working_hours():
    nepal_time = get_nepal_time()
    return START_TIME <= nepal_time.time() <= END_TIME

# ---------------------------------------------
# Slack message sender
# ---------------------------------------------
def send_message(bot_token, channel_id):
    url = "https://slack.com/api/chat.postMessage"
    headers = {"Authorization": f"Bearer {bot_token}", "Content-Type": "application/json"}
    message = f"*Dear Devotee,*\n\n{get_random_quote()}\n\nRegards,\n*Shree Krishna*"
    payload = {"channel": channel_id, "text": message, "username": "Krishna Bot", "icon_emoji": ":lotus_position:", "mrkdwn": True}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        result = response.json()
        if response.status_code == 200 and result.get("ok"):
            logger.info(f"Message sent to {channel_id}")
        else:
            logger.error(f"Error sending message to {channel_id}: {result.get('error', 'Unknown')}")
    except Exception as e:
        logger.error(f"Exception sending message to {channel_id}: {e}")

def send_message_to_all():
    workspaces = load_workspaces()
    for team_id, info in workspaces.items():
        send_message(info["bot_token"], info["channel_id"])

# ---------------------------------------------
# Scheduler
# ---------------------------------------------
def check_and_send():
    nepal_time = get_nepal_time()
    if nepal_time.minute in (0, 30) and is_within_working_hours():
        send_message_to_all()

def log_status():
    nepal_time = get_nepal_time()
    if is_within_working_hours():
        logger.info(f"Status: ACTIVE at {nepal_time.strftime('%H:%M')} NPT")
    else:
        logger.info(f"Status: IDLE (outside working hours)")

# ---------------------------------------------
# OAuth redirect handler (for multi-workspace)
# ---------------------------------------------
class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/slack/oauth_redirect"):
            from urllib.parse import urlparse, parse_qs
            query = parse_qs(urlparse(self.path).query)
            code = query.get("code", [None])[0]
            if code:
                # Exchange code for access token
                data = {
                    "code": code,
                    "client_id": SLACK_CLIENT_ID,
                    "client_secret": SLACK_CLIENT_SECRET,
                    "redirect_uri": f"{BASE_URL}/slack/oauth_redirect"
                }
                resp = requests.post("https://slack.com/api/oauth.v2.access", data=data).json()
                bot_token = resp.get("access_token")
                team_id = resp.get("team", {}).get("id")
                if bot_token and team_id:
                    # Get a channel where bot is a member
                    headers = {"Authorization": f"Bearer {bot_token}"}
                    ch_resp = requests.get("https://slack.com/api/conversations.list?types=public_channel,private_channel", headers=headers).json()
                    channels = [c["id"] for c in ch_resp.get("channels", []) if c.get("is_member")]
                    if channels:
                        channel_id = channels[0]  # pick first channel bot is in
                        save_workspace(team_id, bot_token, channel_id)
                        self.send_response(200)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        self.wfile.write(b"App installed successfully! Krishna Bot will now send quotes here.")
                        logger.info(f"New workspace added: {team_id}, channel {channel_id}")
                        return
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Installation failed")
    def log_message(self, format, *args):
        pass

def start_oauth_server():
    server = HTTPServer(("0.0.0.0", PORT+1), OAuthHandler)  # using PORT+1 for OAuth to avoid conflict
    logger.info(f"OAuth server running on port {PORT+1}")
    server.serve_forever()

# ---------------------------------------------
# Main
# ---------------------------------------------
def main():
    threading.Thread(target=start_http_server, daemon=True).start()
    threading.Thread(target=start_oauth_server, daemon=True).start()
    logger.info("Krishna Bot Starting...")

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
