import configparser
import pathlib
import functools
import subprocess
import os
import tempfile

from datetime import datetime, timedelta

import click
import dateparser
import pytimeparse2


def today():
    return datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)


def get_root_dir() -> pathlib.Path:
    return pathlib.Path.home() / ".thallo"


def get_token_path() -> pathlib.Path:
    root_dir = get_root_dir()
    return root_dir / "TOKEN"


def tmp_editor(contents="") -> str:
    """Pop an $EDITOR with some optional contents."""
    with tempfile.NamedTemporaryFile(mode="w+") as tmp:
        tmp.write(contents)
        subprocess.run([os.environ.get("EDITOR", "vim"), tmp.name])
        tmp.seek(0)
        return tmp.read()


def parse_date(s: str) -> datetime:
    return dateparser.parse(s, settings={"PREFER_DATES_FROM": "future"})


def parse_delta(s: str) -> timedelta:
    return timedelta(seconds=pytimeparse2.parse(s))


def parse_date_like(dates: list[str]) -> datetime:
    date = " ".join(dates) if len(dates) > 0 else str(today())

    return (date if date is click.DateTime else parse_date(date)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


@functools.lru_cache()
def get_gpg_recipient() -> str:
    config_path = get_root_dir() / "thallo.conf"
    config = configparser.ConfigParser()
    config.read(config_path)

    if "general" in config:
        if "gpg_recipient" in config["general"]:
            return config["general"]["gpg_recipient"]

    print(
        "No gpg_recipient set in the configuration file (`~/.thallo/thallo.conf`). Please provide the GPG ID of the recipient (see the README of thallo if you're unsure what that means"
    )
    recipient = input("Recipient:\n")

    config["general"] = {"gpg_recipient": recipient}

    with config_path.open("w") as f:
        config.write(f)

    return recipient
