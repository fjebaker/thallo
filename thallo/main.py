import json
import copy

from datetime import datetime, timedelta

import click

import thallo.auth
import thallo.utils as utils

from thallo.format import pretty_print_events, pretty_print_info, str_date_local
from thallo.calendar import Calendar, Event


def get_calendar(calendar=[]) -> Calendar:
    if len(calendar) > 0:
        return calendar[0]
    else:
        calendar.append(Calendar())
        return calendar[0]


def get_calendar_dates(dates: list[str], delta_days=1) -> Calendar:
    date = utils.parse_start_of_day(dates)
    calendar = get_calendar()
    return date, calendar.fetch_dict(date, date + timedelta(days=delta_days))


def json_dump_events(events: list[Event]) -> str:
    _events = copy.deepcopy(events)
    for ev in _events:
        ev["start_time"] = ev["start_time"].isoformat()
        ev["end_time"] = ev["end_time"].isoformat()
    return json.dumps(_events)


@click.group()
def entry():
    """Thallo is a tool for interacting with Outlook calendars."""
    pass


@click.command()
@click.option(
    "--from",
    default=utils.today(),
    type=click.DateTime(),
    show_default=True,
    help="The date to select from",
)
@click.option(
    "--to",
    default=utils.today() + timedelta(days=7 * 2),
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
        print(json_dump_events(events))
        return

    pretty_print_events(events)


@click.command()
@click.argument("dates", nargs=-1)
@click.option(
    "-i",
    "--index",
    type=int,
    help="The index of the event on the selected day.",
)
@click.option(
    "-n",
    "--name",
    type=str,
    help="The name of the event on the selected day.",
)
@click.option(
    "--json",
    is_flag=True,
    help="Output the events as a JSON string.",
)
def info(dates, **kwargs):
    """Get detailed information about a day or specific event."""
    parsed_date, events = get_calendar_dates(dates)

    print(f"Events for {str_date_local(parsed_date)}")

    if kwargs["index"] is None and kwargs["name"] is None:
        if len(events) == 0:
            print("\n - No events - \n")
            return

        if kwargs["json"]:
            return print(json_dump_events(events))

        return pretty_print_events(events)

    if kwargs["index"] and kwargs["name"]:
        print("Can only specify one event selector (`--index` or `--name`)")
        return

    ev = None
    if kwargs["index"] is not None:
        ev = events[int(kwargs["index"])]
    elif kwargs["name"] is not None:
        name = kwargs["name"].lower()
        evs = [i for i in events if i["name"].lower() == name]
        ev = evs[0]
    else:
        print("Unknown event selection!")
        return

    if kwargs["json"]:
        return print(json_dump_events([ev]))

    print()
    pretty_print_info(ev, body=True, attendees=True, location=True)
    print()


@click.command()
@click.argument("dates", nargs=-1)
@click.option(
    "-t",
    "--title",
    default="No Title",
    type=str,
    show_default=True,
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
@click.option(
    "-i",
    "--interactive",
    is_flag=True,
    help="Edit the event in $EDITOR.",
)
@click.option(
    "--body",
    type=str,
    help="Body of the event",
)
@click.option(
    "--location",
    type=str,
    help="The location of the event (specify by `uniqueId`).",
)
@click.option(
    "--invite",
    type=str,
    help="A comma seperated list of email addresses to invite to the event.",
)
def add(dates, **kwargs):
    """Add a new event to a calendar."""
    date = " ".join(dates)

    start = date if date is click.DateTime else utils.parse_date(date)
    if not start:
        print("Must supply a start time for the event!")
        return

    duration = utils.parse_delta(kwargs["duration"])
    end = start + duration

    invites = []
    if kwargs["invite"]:
        invites += kwargs["invite"].split(",")

    calendar = get_calendar()
    ev = calendar.add_event(
        start,
        end,
        title=kwargs["title"],
        private=kwargs["private"],
        body=kwargs["body"],
        location=kwargs["location"],
        attendees=invites,
    )

    if kwargs["interactive"]:
        contents = calendar.serialize_event(ev)

        while True:
            updated_contents = utils.tmp_editor(contents)
            ev = calendar.deserialize_event(updated_contents)
            if not ev:
                inp = input("Input invalid. Try again? [Y/n] ").strip().lower()
                if inp == "" or inp == "y":
                    continue
            break

    if not ev:
        return

    print("New event:")
    print()
    pretty_print_info(
        Calendar.extract_fields(ev, parse_body=False),
        body=True,
        attendees=True,
        location=True,
        wrap=False,
    )
    print()

    inp = input("Accept? [Y/n] ").strip().lower()
    if inp == "" or inp == "y":
        ev.save()
        print("Event saved to calendar.")
    else:
        print("Event discarded.")


@click.command()
@click.option(
    "--email",
    help="The email address to use to login to Outlook.",
)
def authorize(email=None):
    """Fetch an OAuth2 token (requires a browser)."""
    thallo.auth.run(utils.get_token_path(), authorize=True, email=email)
    print("Successfully authenticated!")


def main():
    entry()


entry.add_command(fetch)
entry.add_command(add)
entry.add_command(authorize)
entry.add_command(info)
