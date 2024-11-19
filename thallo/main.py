import json

from datetime import datetime, timedelta

import click
import dateparser
import pytimeparse2


from thallo.calendar import Calendar


def get_calendar(calendar=[]) -> Calendar:
    if len(calendar) > 0:
        return calendar[0]
    else:
        calendar.append(Calendar())
        return calendar[0]


def _TODAY():
    return datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)


def _parse_date(s: str) -> datetime:
    return dateparser.parse(s, settings={"PREFER_DATES_FROM": "future"})


def _parse_delta(s: str) -> timedelta:
    return timedelta(seconds=pytimeparse2.parse(s))


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
    """Fetch events from the calendar and print in various ways."""
    start = kwargs["from"]
    end = kwargs["to"]

    calendar = get_calendar()
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

    calendar = get_calendar()
    events = calendar.fetch_dict(start, start + timedelta(days=1))

    if kwargs["json"]:
        return print(json.dumps(events))

    print(events)


@click.command()
@click.argument("dates", nargs=-1)
@click.option(
    "-t",
    "--title",
    type=str,
    required=True,
    help="The title of the event",
)
@click.option(
    "--duration",
    default="1h",
    type=str,
    show_default=True,
    help="Duration of the calendar event.",
)
@click.option(
    "--private",
    is_flag=True,
    help="Set the event to a private event.",
)
def add(dates, **kwargs):
    """Add a new event to a calendar."""
    date = " ".join(dates)

    start = date if date is click.DateTime else _parse_date(date)
    duration = _parse_delta(kwargs["duration"])
    end = start + duration

    calendar = get_calendar()
    ev = calendar.add_event(
        start, end, title=kwargs["title"], private=kwargs["private"]
    )
    print("Event:", ev)
    inp = input("Accept? [Y/n] ").strip().lower()
    if inp == "" or inp == "y":
        ev.save()
        print("Event saved to calendar.")
    else:
        print("Event discarded.")


def main():
    entry()


entry.add_command(fetch)
entry.add_command(day)
entry.add_command(add)
