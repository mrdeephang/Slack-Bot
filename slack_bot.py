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
from urllib.parse import urlparse, parse_qs
import json
import logging

# -------------------------------
# Logging
# -------------------------------
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -------------------------------
# Load .env
# -------------------------------
load_dotenv()

SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
BASE_URL = os.getenv("BASE_URL")
PORT = int(os.getenv("PORT", 10000))

# Nepal timezone & working hours
NEPAL_TIMEZONE = pytz.timezone("Asia/Kathmandu")
START_TIME = dt_time(10, 0)
END_TIME = dt_time(18, 0)

WORKSPACES_FILE = "workspaces.json"

# -------------------------------
# Workspace JSON helpers
# -------------------------------
def load_workspaces():
    try:
        with open(WORKSPACES_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_workspace(team_id, bot_token, channel_id=None):
    workspaces = load_workspaces()
    workspaces[team_id] = {"bot_token": bot_token, "channel_id": channel_id}
    with open(WORKSPACES_FILE, "w") as f:
        json.dump(workspaces, f)
    logger.info(f"Workspace saved: {team_id}, channel: {channel_id}")

def update_channel_if_missing(team_id, bot_token):
    workspaces = load_workspaces()
    if workspaces[team_id].get("channel_id"):
        return  # already has channel
    headers = {"Authorization": f"Bearer {bot_token}"}
    ch_resp = requests.get(
        "https://slack.com/api/conversations.list?types=public_channel,private_channel",
        headers=headers
    ).json()
    channels = [c["id"] for c in ch_resp.get("channels", []) if c.get("is_member")]
    if channels:
        workspaces[team_id]["channel_id"] = channels[0]
        with open(WORKSPACES_FILE, "w") as f:
            json.dump(workspaces, f)
        logger.info(f"Auto-detected channel for {team_id}: {channels[0]}")

# -------------------------------
# Health & OAuth handler
# -------------------------------
class MainHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)

        # Health check
        if path == "/health":
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
            return

        # OAuth redirect
        elif path == "/slack/oauth_redirect":
            code = query.get("code", [None])[0]
            if code:
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
                    # Detect a channel bot is member of
                    headers = {"Authorization": f"Bearer {bot_token}"}
                    ch_resp = requests.get(
                        "https://slack.com/api/conversations.list?types=public_channel,private_channel",
                        headers=headers
                    ).json()
                    channels = [c["id"] for c in ch_resp.get("channels", []) if c.get("is_member")]
                    channel_id = channels[0] if channels else None
                    save_workspace(team_id, bot_token, channel_id)
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"App installed successfully! Krishna Bot will now send quotes here.")
                    return

            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Installation failed")
            return

        # Catch-all
        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress logging

def start_http_server():
    server = HTTPServer(("0.0.0.0", PORT), MainHandler)
    logger.info(f"Server running on port {PORT}")
    server.serve_forever()

# -------------------------------
# Time helpers
# -------------------------------
def get_nepal_time():
    utc_now = pytz.utc.localize(datetime.utcnow())
    return utc_now.astimezone(NEPAL_TIMEZONE)

def is_within_working_hours():
    nepal_time = get_nepal_time()
    return START_TIME <= nepal_time.time() <= END_TIME

# -------------------------------
# Slack messaging
# -------------------------------
def send_message(bot_token, channel_id):
    if not channel_id:
        return
    url = "https://slack.com/api/chat.postMessage"
    headers = {"Authorization": f"Bearer {bot_token}",
               "Content-Type": "application/json"}
    payload = {
        "channel": channel_id,
        "text": f"*Dear Devotee,*\n\n{get_random_quote()}\n\nRegards,\n*Shree Krishna*",
        "username": "Krishna Bot",
        "icon_emoji": ":lotus_position:",
        "mrkdwn": True
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20).json()
        if resp.get("ok"):
            logger.info(f"Message sent to channel {channel_id}")
        else:
            logger.error(f"Error sending to {channel_id}: {resp.get('error')}")
    except Exception as e:
        logger.error(f"Exception sending to {channel_id}: {e}")

def send_message_to_all():
    workspaces = load_workspaces()
    for team_id, info in workspaces.items():
        # auto-update channel if missing
        update_channel_if_missing(team_id, info["bot_token"])
        send_message(info["bot_token"], info.get("channel_id"))

# -------------------------------
# Scheduler
# -------------------------------
def check_and_send():
    # nepal_time = get_nepal_time()
    # if nepal_time.minute in (0, 30) and is_within_working_hours():
        send_message_to_all()

def log_status():
    nepal_time = get_nepal_time()
    status = "ACTIVE" if is_within_working_hours() else "IDLE"
    logger.info(f"Status: {status} at {nepal_time.strftime('%H:%M')} NPT")

# -------------------------------
# Main
# -------------------------------
def main():
    threading.Thread(target=start_http_server, daemon=True).start()
    logger.info("Krishna Bot starting...")

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
