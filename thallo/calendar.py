import os
import json
import subprocess

from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone

import thallo.auth
import thallo.utils as utils

from O365 import Account
from O365.calendar import Calendar, Event
from O365.utils.token import BaseTokenBackend, Token

from markdownify import markdownify as md

FIELDS_TO_SAVE = [
    "access_token_expiration",
    "refresh_token",
    "access_token",
]

HUMAN_TIME_FORMAT = "%d/%m/%Y %H:%M UTC%z"


def cleanup_string(s: str) -> str:
    lines = [l.strip() for l in s.strip().split("\n")]
    return "\n".join([l for l in lines if l != ""])


class Token(BaseTokenBackend):

    def __init__(self, token_path=utils.get_token_path()):
        super().__init__()
        self.token_is_valid = False
        self.decrypted_token = None
        self.token_path = token_path

    def _read_token_file(self) -> dict:
        """
        Read an access token from file.
        """
        # first we check the token is okay / refresh for good luck
        thallo.auth.run(self.token_path)

        if not self.token_path.exists():
            raise Exception("Token not found")

        if 0o777 & self.token_path.stat().st_mode != 0o600:
            raise Exception(
                "Token file has unsafe mode. Suggest deleting and starting over."
            )

        return thallo.auth.load_and_decrypt(self.token_path)

    def _write_token_file(self) -> None:
        """
        Write the access token.
        """
        if not self.token_path.exists():
            self.token_path.touch(mode=0o600)

        if 0o777 & self.token_path.stat().st_mode != 0o600:
            raise Exception(
                "Token file has unsafe mode. Suggest deleting and starting over."
            )

        thallo.auth.encrypt_and_save(self.token_path, self.decrypted_token)

    def _access_token_valid(self) -> bool:
        """
        Used to check the expiry date of a given token
        """
        token_exp = self.decrypted_token["access_token_expiration"]
        return token_exp and datetime.now() < datetime.fromisoformat(token_exp)

    def load_token(self):
        self.decrypted_token = self._read_token_file()
        return self.decrypted_token

    def save_token(self):
        for field in FIELDS_TO_SAVE:
            self.decrypted_token[field] = self.token[field]
        self._write_token_file()

    def should_refresh_token(self):
        if not self.decrypted_token:
            return False
        self.token_is_valid = self._access_token_valid()
        return self.token_is_valid


class Calendar:

    def __init__(self):
        self.token = Token()
        self.token.load_token()

        self.account = Account(
            (
                self.token.decrypted_token["client_id"],
                self.token.decrypted_token["client_secret"],
            ),
            token_backend=self.token,
        )
        self.schedule = self.account.schedule()
        self.calendar = self.schedule.get_default_calendar()

    def fetch(self, start: datetime, end: datetime, sort=True) -> list[Event]:
        """
        Fetch calendar events between two given dates.
        """
        query = self.calendar.new_query("start").greater_equal(start)
        query.chain("and").on_attribute("end").less_equal(end)

        events = self.calendar.get_events(query=query, include_recurring=True)
        evs = [e for e in events]

        if sort:
            return [i for i in sorted(evs, key=lambda i: i.start)]
        return evs

    def fetch_dict(self, start: datetime, end: datetime, **kwargs) -> list[dict]:
        """
        Fetch calendar events between two given dates, extracting and cleaning
        the fields into a pre-defined schema.
        """
        return [self.extract_fields(i) for i in self.fetch(start, end, **kwargs)]

    @staticmethod
    def extract_fields(event: Event) -> dict:
        attendees = [{"name": i.name, "address": i.address} for i in event.attendees]
        locations = event.locations

        e = {
            "name": event.attachment_name,
            "body": cleanup_string(md(event.body)),
            "attendees": attendees,
            "locations": locations,
            "start_time": event.start,
            "end_time": event.end,
        }
        return e

    def add_event(
        self,
        start: datetime,
        end: datetime,
        title="New Meeting",
        private=False,
        body=None,
    ) -> Event:
        start = start.astimezone(timezone.utc).replace(tzinfo=ZoneInfo("UTC"))
        end = end.astimezone(timezone.utc).replace(tzinfo=ZoneInfo("UTC"))

        ev = self.calendar.new_event()
        ev.subject = title
        ev.start = start
        ev.end = end

        if private:
            ev.sensitivity = "private"

        if body:
            ev.body = body

        return ev

    def serialize_event(self, event: Event) -> str:
        d = Calendar.extract_fields(event)

        start_time = d["start_time"].strftime(HUMAN_TIME_FORMAT)
        end_time = d["end_time"].strftime(HUMAN_TIME_FORMAT)
        title = d["name"]
        body = d["body"]

        buf = ""
        buf += f"Start: {start_time}\n"
        buf += f"End: {end_time}\n"
        buf += f"Title: {title}\n"
        buf += f"Body: {body}"
        return buf

    def deserialize_event(self, content: str) -> None | Event:
        start_time = None
        end_time = None
        title = None
        body = None

        lines = (i for i in content.split("\n"))

        def get_next(s: str) -> str:
            start = s.strip()
            line = next(lines)
            if not line.startswith(start):
                return None
            return line.removeprefix(start).strip()

        start_time = utils.parse_date_like(get_next("Start:").split(" "))
        end_time = utils.parse_date_like(get_next("End:").split(" "))
        title = get_next("Title:")
        body = "\n".join(lines)

        return self.add_event(start_time, end_time, title=title, body=body)
