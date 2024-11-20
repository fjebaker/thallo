import pathlib


def get_root_dir() -> pathlib.Path:
    return pathlib.Path.home() / ".thallo"


def get_token_path() -> pathlib.Path:
    root_dir = get_root_dir()
    return root_dir / "TOKEN"


def get_gpg_recipient() -> str:
    return "REDACTED"
