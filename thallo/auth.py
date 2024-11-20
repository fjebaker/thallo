# This file is a modified version of the Mutt OAuth2 token management script.
# See the copyright notice below:

# Mutt OAuth2 token management script, version 2020-08-07
# Written against python 3.7.3, not tried with earlier python versions.
#
#   Copyright (C) 2020 Alexander Perlis
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License as
#   published by the Free Software Foundation; either version 2 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
#   02110-1301, USA.

import sys
import json
import subprocess
import logging
import secrets
import base64
import hashlib
import time
import socket
import http.server
import urllib.parse
import urllib.request

from pathlib import Path

from datetime import timedelta, datetime

import thallo.utils as utils

logger = logging.getLogger(__name__)


class NoToken(Exception):
    """No token present at specified location error"""

    pass


ENCRYPTION_PIPE = [
    "gpg",
    "--encrypt",
    "--recipient",
    utils.get_gpg_recipient(),
]
DECRYPTION_PIPE = ["gpg", "--decrypt"]

REGISTRATIONS = {
    "microsoft": {
        "authorize_endpoint": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "devicecode_endpoint": "https://login.microsoftonline.com/common/oauth2/v2.0/devicecode",
        "token_endpoint": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "redirect_uri": "https://login.microsoftonline.com/common/oauth2/nativeclient",
        "tenant": "common",
        "imap_endpoint": "outlook.office365.com",
        "pop_endpoint": "outlook.office365.com",
        "smtp_endpoint": "smtp.office365.com",
        # client id and secret hard-coded from Thunderbird
        "client_secret": "TxRBilcHdC6WGBee]fs?QR:SJ8nI[g82",
        "client_id": "08162f7c-0fd2-4200-a84a-f25a4db0b584",
        "sasl_method": "XOAUTH2",
        "scope": (
            "offline_access "
            "https://graph.microsoft.com/Calendars.Read "
            "https://graph.microsoft.com/Calendars.ReadWrite"
        ),
    },
}


def encrypt_and_save(path: Path, token: dict):
    sub2 = subprocess.run(
        encryption_pipe,
        check=true,
        input=json.dumps(token).encode(),
        capture_output=true,
    )
    path.write_bytes(sub2.stdout)


def load_and_decrypt(path: Path) -> dict:
    sub = subprocess.run(
        DECRYPTION_PIPE,
        check=True,
        input=path.read_bytes(),
        capture_output=True,
    )
    return json.loads(sub.stdout)


def run(path: Path, authorize=False, email=None):
    token = {}
    if path.exists():
        if 0o777 & path.stat().st_mode != 0o600:
            raise Exception(
                "Token file has unsafe mode. Suggest deleting and starting over."
            )
        try:
            sub = subprocess.run(
                DECRYPTION_PIPE,
                check=True,
                input=path.read_bytes(),
                capture_output=True,
            )
            token = json.loads(sub.stdout)
        except subprocess.CalledProcessError:
            raise Exception(
                "Difficulty decrypting token file. Is your decryption agent primed for "
                "non-interactive usage, or an appropriate environment variable such as "
                "GPG_TTY set to allow interactive agent usage from inside a pipe?"
            )

    def writetokenfile():
        """Writes global token dictionary into token file."""
        if not path.exists():
            path.touch(mode=0o600)
        if 0o777 & path.stat().st_mode != 0o600:
            raise Exception(
                "Token file has unsafe mode. Suggest deleting and starting over."
            )
        sub2 = subprocess.run(
            ENCRYPTION_PIPE,
            check=True,
            input=json.dumps(token).encode(),
            capture_output=True,
        )
        path.write_bytes(sub2.stdout)

    if not token:
        if not authorize:
            raise NoToken(
                f"No token at {path}, must use `authorize` command to setup the authentication token"
            )

        token["registration"] = "microsoft"
        token["authflow"] = "localhostauthcode"
        token["email"] = email or input("Account e-mail address: ")
        token["access_token"] = ""
        token["access_token_expiration"] = ""
        token["refresh_token"] = ""
        reg = REGISTRATIONS["microsoft"]
        token["client_id"] = reg["client_id"]
        token["client_secret"] = reg["client_secret"]
        writetokenfile()

    if token["registration"] not in REGISTRATIONS:
        raise Exception(
            f'ERROR: Unknown registration "{token["registration"]}". Delete token file '
            f"and start over."
        )
    registration = REGISTRATIONS[token["registration"]]

    authflow = token["authflow"]

    baseparams = {"client_id": token["client_id"]}
    # Microsoft uses 'tenant' but Google does not
    if "tenant" in registration:
        baseparams["tenant"] = registration["tenant"]

    def access_token_valid():
        """Returns True when stored access token exists and is still valid at this time."""
        token_exp = token["access_token_expiration"]
        return token_exp and datetime.now() < datetime.fromisoformat(token_exp)

    def update_tokens(r):
        """Takes a response dictionary, extracts tokens out of it, and updates token file."""
        token["access_token"] = r["access_token"]
        token["access_token_expiration"] = (
            datetime.now() + timedelta(seconds=int(r["expires_in"]))
        ).isoformat()
        if "refresh_token" in r:
            token["refresh_token"] = r["refresh_token"]
        writetokenfile()

    if authorize:
        p = baseparams.copy()
        p["scope"] = registration["scope"]

        # hardcode the authflow
        authflow = "localhostauthcode"

        verifier = secrets.token_urlsafe(90)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        )[:-1]
        redirect_uri = registration["redirect_uri"]
        listen_port = 0

        # Find an available port to listen on
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        listen_port = s.getsockname()[1]
        s.close()
        redirect_uri = "http://localhost:" + str(listen_port) + "/"
        # Probably should edit the port number into the actual redirect URL.

        p.update(
            {
                "login_hint": token["email"],
                "response_type": "code",
                "redirect_uri": redirect_uri,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )

        print(
            registration["authorize_endpoint"]
            + "?"
            + urllib.parse.urlencode(p, quote_via=urllib.parse.quote)
        )

        print(
            "Visit displayed URL to authorize this application. Waiting...",
            end="",
            flush=True,
        )

        global authcode
        authcode = ""

        class MyHandler(http.server.BaseHTTPRequestHandler):
            """Handles the browser query resulting from redirect to redirect_uri."""

            # pylint: disable=C0103
            def do_HEAD(self):
                """Response to a HEAD requests."""
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

            def do_GET(self):
                """For GET request, extract code parameter from URL."""
                # pylint: disable=W0603
                global authcode
                querystring = urllib.parse.urlparse(self.path).query
                querydict = urllib.parse.parse_qs(querystring)
                if "code" in querydict:
                    authcode = querydict["code"][0]
                self.do_HEAD()
                self.wfile.write(
                    b"<html><head><title>Authorizaton result</title></head>"
                )
                self.wfile.write(
                    b"<body><p>Authorization redirect completed. You may "
                    b"close this window.</p></body></html>"
                )

        with http.server.HTTPServer(("127.0.0.1", listen_port), MyHandler) as httpd:
            try:
                httpd.handle_request()
            except KeyboardInterrupt:
                pass

        if not authcode:
            raise Exception("Did not obtain an authcode.")

        for k in (
            "response_type",
            "login_hint",
            "code_challenge",
            "code_challenge_method",
        ):
            del p[k]
        p.update(
            {
                "grant_type": "authorization_code",
                "code": authcode,
                "client_secret": token["client_secret"],
                "code_verifier": verifier,
            }
        )
        try:
            response = urllib.request.urlopen(
                registration["token_endpoint"], urllib.parse.urlencode(p).encode()
            )
        except urllib.error.HTTPError as err:
            logger.debug(err.code, err.reason)
            response = err
        response = response.read()
        response = json.loads(response)
        if "error" in response:
            logger.debug(response["error"])
            if "error_description" in response:
                logger.debug(response["error_description"])
            raise Exception(1)

        update_tokens(response)

    if not access_token_valid():
        if not token["refresh_token"]:
            raise Exception('ERROR: No refresh token. Run script with "--authorize".')
        p = baseparams.copy()
        p.update(
            {
                "client_id": token["client_id"],
                "client_secret": token["client_secret"],
                "refresh_token": token["refresh_token"],
                "grant_type": "refresh_token",
            }
        )
        try:
            response = urllib.request.urlopen(
                registration["token_endpoint"], urllib.parse.urlencode(p).encode()
            )
        except urllib.error.HTTPError as err:
            logger.debug(err.code, err.reason)
            response = err
        response = response.read()
        response = json.loads(response)
        if "error" in response:
            logger.debug(response["error"])
            if "error_description" in response:
                logger.debug(response["error_description"])
            logger.debug(
                'Perhaps refresh token invalid. Try running once with "--authorize"'
            )
            raise Exception(1)
        update_tokens(response)

    if not access_token_valid():
        raise Exception(
            "ERROR: No valid access token. This should not be able to happen."
        )

    logger.debug(token["access_token"])

    def build_sasl_string(user, host, port, bearer_token):
        """Build appropriate SASL string, which depends on cloud server's supported SASL method."""
        if registration["sasl_method"] == "OAUTHBEARER":
            return (
                f"n,a={user},\1host={host}\1port={port}\1auth=Bearer {bearer_token}\1\1"
            )
        if registration["sasl_method"] == "XOAUTH2":
            return f"user={user}\1auth=Bearer {bearer_token}\1\1"
        raise Exception(f'Unknown SASL method {registration["sasl_method"]}.')
