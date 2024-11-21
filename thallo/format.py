from datetime import datetime

from thallo.calendar import Event

from colorama import init, Fore, Style

# initialise colorama
init()

BOX_TOP_LEFT = "╭"
BOX_CONT = "│"
BOX_BOT_LEFT = "╰"

TIME_FMT = Fore.YELLOW + Style.BRIGHT
TIME_END = Fore.RESET + Style.RESET_ALL

def pretty_print_events(events: list[Event]):
    for event in events:
        start = datetime.fromisoformat(event["start_time"])
        start_date = start.strftime('%a %d %b %Y')
        start_time = start.strftime('%H:%M')


        end = datetime.fromisoformat(event["end_time"])
        end_date = end.strftime('%a %d %b %Y')
        end_time = end.strftime('%H:%M')

        print(Style.DIM + BOX_TOP_LEFT, start_date + Style.RESET_ALL, TIME_FMT + start_time + TIME_END, end = "")
        print(" - ", end = "")
        print(Style.DIM + end_date + Style.RESET_ALL,  TIME_FMT + end_time + TIME_END)
        print(Style.DIM + BOX_BOT_LEFT + Style.RESET_ALL,  Style.BRIGHT + event["name"] + Style.RESET_ALL, end="")
        n = len(event["attendees"])
        print(f" - with {n} attendees")
        print()
