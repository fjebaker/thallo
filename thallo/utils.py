import configparser
import pathlib
import functools


def get_root_dir() -> pathlib.Path:
    return pathlib.Path.home() / ".thallo"


def get_token_path() -> pathlib.Path:
    root_dir = get_root_dir()
    return root_dir / "TOKEN"


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
