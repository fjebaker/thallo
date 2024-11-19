import subprocess
import pathlib
import json
import datetime
import sys

from datetime import datetime, timedelta

from markdownify import markdownify as md


from O365 import Account
from O365.calendar import Calendar, Event
from O365.utils.token import BaseTokenBackend, Token

ENCRYPTION_PIPE = [
    "gpg",
    "--encrypt",
    "--recipient",
    "REDACTED",
]
DECRYPTION_PIPE = ["gpg", "--decrypt"]
FIELDS_TO_SAVE = [
    "access_token_expiration",
    "refresh_token",
    "access_token",
]
path = pathlib.Path("/home/lilith/developer/py-outlook/TOKEN_CALENDAR_RW")


def readtokenfile():
    if path.exists():
        if 0o777 & path.stat().st_mode != 0o600:
            sys.exit("Token file has unsafe mode. Suggest deleting and starting over.")
        try:
            sub = subprocess.run(
                DECRYPTION_PIPE,
                check=True,
                input=path.read_bytes(),
                capture_output=True,
            )
            return json.loads(sub.stdout)
        except subprocess.CalledProcessError:
            sys.exit("Failed to decrypt")


def writetokenfile():
    if not path.exists():
        path.touch(mode=0o600)
    if 0o777 & path.stat().st_mode != 0o600:
        sys.exit("Token file has unsafe mode. Suggest deleting and starting over.")
    sub2 = subprocess.run(
        ENCRYPTION_PIPE,
        check=True,
        input=json.dumps(token).encode(),
        capture_output=True,
    )
    path.write_bytes(sub2.stdout)


def access_token_valid(token):
    token_exp = token["access_token_expiration"]
    return token_exp and datetime.now() < datetime.fromisoformat(token_exp)

class MyToken(BaseTokenBackend):
    def __init__(self):
        super().__init__()
        self.token_is_valid = False
        self.decrypted_token = None

    def load_token(self):
        self.decrypted_token = readtokenfile()
        return self.decrypted_token

    def save_token(self):
        for field in FIELDS_TO_SAVE:
            self.decrypted_token[field] = self.token[field]
        writetokenfile()

    def should_refresh_token(self):
        if not self.decrypted_token:
            return False
        self.token_is_valid = access_token_valid(self.decrypted_token)
        return self.token_is_valid

def fetch_events(start, end):

    token = MyToken()
    token.load_token()
    acc = Account(
        (token.decrypted_token["client_id"], token.decrypted_token["client_secret"]),
        token_backend=token,
    )

    schedule = acc.schedule()
    calendar = schedule.get_default_calendar()

    q = calendar.new_query("start").greater_equal(start)
    q.chain("and").on_attribute("end").less_equal(end)

    events = calendar.get_events(query=q, include_recurring=True)
    return events

def cleanup_string(s: str) -> str:
    lines = [l.strip() for l in s.strip().split("\n")]
    return "\n".join([l for l in lines if l != ""])

def extract_fields(event: Event) -> dict:
    attendees = [{"name": i.name, "address": i.address} for i in event.attendees]
    locations = event.locations

    e = {
        "name": event.attachment_name,
        "body": cleanup_string(md(event.body)),
        "attendees": attendees,
        "locations": locations,
        "start_time": event.start.isoformat(),
        "end_time": event.end.isoformat(),
    }
    return e


today = datetime.today()
week_before = today - timedelta(days=7 * 2)
week_after = today + timedelta(days=7 * 2)

events = fetch_events(week_before, week_after)

evs = [extract_fields(e) for e in events]
print(json.dumps(evs, indent=4))


