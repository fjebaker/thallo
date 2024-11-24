import shutil
import textwrap
from datetime import datetime

from thallo.calendar import Event

from colorama import init, Fore, Style

# initialise colorama
init()

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
        buf += Style.DIM
        if i == 0:
            buf += BOX_TOP_LEFT
        elif i == len(lines) - 1:
            buf += BOX_BOT_LEFT
        else:
            buf += BOX_CONT
        buf += Style.RESET_ALL

        buf += " " + l + "\n"
    return buf[:-1]


def wrap(text: str, indent: int = 2) -> str:
    return textwrap.indent(
        textwrap.fill(
            text,
            TERMINAL_WIDTH - indent,
            replace_whitespace=False,
            drop_whitespace=False,
        ),
        " " * indent,
    )


def pretty_print_info(
    event: Event, attendees=False, location=False, body=False, index=None
):
    start = datetime.fromisoformat(event["start_time"])
    start_date = start.strftime("%a %d %b %Y")
    start_time = start.strftime("%H:%M")

    end = datetime.fromisoformat(event["end_time"])
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

    # body

    # newline
    print(encapsulate(lines))


def pretty_print_events(events: list[Event]):
    # new line at the top
    print()
    for i, event in enumerate(events):
        pretty_print_info(event, index=i)
        print("")
