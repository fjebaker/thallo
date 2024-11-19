import json

from datetime import datetime, timedelta

import click
import dateparser

from thallo.calendar import Calendar

calendar = Calendar()


def _TODAY():
    return datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

def _parse_date(s: str) -> datetime:
    return dateparser.parse(s)


@click.group()
def entry():
    """Thallo is a tool for interacting with Outlook calendars."""
    pass


@click.command()
@click.option(
    "--from",
    default=_TODAY(),
    type=click.DateTime(),
    show_default=True,
    help="The date to select from",
)
@click.option(
    "--to",
    default=_TODAY() + timedelta(days=7 * 2),
    type=click.DateTime(),
    show_default=True,
    help="The date to select to, not inclusive (defaults to a fortnight ahead).",
)
@click.option(
    "--json",
    is_flag=True,
    help="Output the fetched events as a JSON string.",
)
def fetch(**kwargs):
    """Fetch events from the calendar and print in various ways.
    """
    start = kwargs["from"]
    end = kwargs["to"]

    events = calendar.fetch_dict(start, end)

    if kwargs["json"]:
        print(json.dumps(events))
        return

    print(events)


@click.command()
@click.argument("date", default=_TODAY())
@click.option(
    "--json",
    is_flag=True,
    help="Output the events as a JSON string.",
)
def day(date, **kwargs):
    """Show the events on a specific day. Defaults to today."""
    start = date if date is click.DateTime else _parse_date(date)
    events = calendar.fetch_dict(start, start + timedelta(days=1))

    if kwargs["json"]:
        return print(json.dumps(events))

    print(events)


def main():
    entry()


entry.add_command(fetch)
entry.add_command(day)
