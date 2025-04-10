import shutil
import textwrap
from datetime import datetime

from thallo.calendar import Event

from colorama import init, Fore, Style

# initialise colorama
init()

# get the current timezone for the lifetime of the program
current_tz = datetime.now().astimezone().tzinfo


BOX_TOP_LEFT = "╭"
BOX_CONT = "│"
BOX_BOT_LEFT = "╰"

INDENT = "  "

TIME_FMT = Fore.YELLOW + Style.BRIGHT
TIME_END = Fore.RESET + Style.RESET_ALL

TITLE_FMT = Fore.CYAN + Style.BRIGHT
TITLE_END = Fore.RESET + Style.RESET_ALL

TERMINAL_WIDTH = shutil.get_terminal_size().columns


def encapsulate(lines: list[str]) -> str:
    buf = ""
    for i, l in enumerate(lines):
        buf += " " + Style.DIM
        if i == 0:
            buf += BOX_TOP_LEFT
        elif i == len(lines) - 1:
            buf += BOX_BOT_LEFT
        else:
            buf += BOX_CONT
        buf += Style.RESET_ALL

        buf += " " + l + "\n"
    return buf[:-1]


def text_wrap(text: str, width=TERMINAL_WIDTH, indent=0) -> list[str]:
    lines = []
    for line in text.split("\n"):
        if len(line.strip()) == 0:
            lines += [""]
        else:
            lines += textwrap.wrap(line, width)
    _indent = " " * indent
    return [_indent + line for line in lines]


def str_date_local(date) -> str:
    return date.astimezone(current_tz).strftime("%a %b %d %Y")


def pretty_print_info(
    event: Event,
    attendees=False,
    location=False,
    body=False,
    index=None,
    wrap=True,
):
    start = event["start_time"].astimezone(current_tz)
    start_date = start.strftime("%a %d %b %Y")
    start_time = start.strftime("%H:%M")

    end = event["end_time"].astimezone(current_tz)
    end_date = end.strftime("%a %d %b %Y")
    end_time = end.strftime("%H:%M")

    lines = []
    if index is not None:
        lines.append(Style.DIM + f"Event #{index}" + Style.RESET_ALL)

    # print the time of the event
    buf = ""
    buf += Style.DIM + start_date + Style.RESET_ALL
    buf += " "
    buf += TIME_FMT + start_time + TIME_END
    buf += " - "
    buf += Style.DIM + end_date + Style.RESET_ALL
    buf += " "
    buf += TIME_FMT + end_time + TIME_END
    lines.append(buf)

    # title
    buf = ""
    buf += TITLE_FMT + event["name"] + TITLE_END
    n = len(event["attendees"])
    buf += f" - with {n} attendees"
    lines.append(buf)

    # location details
    if location and event["location"]:
        loc = event["location"]
        loc_name = loc.get("displayName", loc.get("uniqueId", None))
        if loc_name:
            buf = Style.DIM + "Location: " + Style.RESET_ALL
            buf += loc_name
            lines.append(buf)

    # body
    if body:
        lines.append(Style.DIM + "Body:" + Style.RESET_ALL)
        body = event["body"] or " - No body - "
        if wrap:
            lines += text_wrap(body, width=80, indent=1)
        else:
            lines += body.split("\n")

    if attendees and n > 0:
        lines.append(Style.DIM + "Attendees:" + Style.RESET_ALL)
        for att in event["attendees"]:
            name = att["name"]
            address = att["address"]
            lines.append(f" - {name} {Style.DIM}<{address}>{Style.RESET_ALL}")

    # newline
    print(encapsulate(lines))


def pretty_print_events(events: list[Event]):
    # new line at the top
    print()
    for i, event in enumerate(events):
        pretty_print_info(event, index=i)
        print("")
