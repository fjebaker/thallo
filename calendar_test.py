import subprocess
import pathlib
import json
import datetime
import sys

from O365 import Account
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



path = pathlib.Path("/home/lilith/Developer/py-outlook/TOKEN_CALENDAR")


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


decrypted_token = readtokenfile()


def access_token_valid():
    token_exp = decrypted_token["access_token_expiration"]
    return token_exp and datetime.now() < datetime.fromisoformat(token_exp)


class MyToken(BaseTokenBackend):
    def __init__(self):
        super().__init__()
        self.token_is_valid = False

    def load_token(self):
        return decrypted_token

    def save_token(self):
        for field in FIELDS_TO_SAVE:
            decrypted_token[field] = self.token[field]
        writetokenfile()

    def should_refresh_token(self):
        print("REFRESH?")
        self.token_is_valid = access_token_valid()
        return self.token_is_valid


token = MyToken()
acc = Account(
    (decrypted_token["client_id"], decrypted_token["client_secret"]),
    token_backend=token,
)

# if acc.authenticate(scopes=["calendar"]):
#     print("Works :D")
# else:
#     print("No works :C")

schedule = acc.schedule()
calendar = schedule.get_default_calendar()

q = calendar.new_query("start").greater_equal(datetime.datetime(2024, 10, 15))
q.chain("and").on_attribute("end").less_equal(datetime.datetime(2024, 11, 22))

events = calendar.get_events(query=q, include_recurring=True)
for event in events:
    print(event)
