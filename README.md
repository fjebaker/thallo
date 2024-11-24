# Thallo

    Usage: thallo [OPTIONS] COMMAND [ARGS]...

      Thallo is a tool for interacting with Outlook calendars.

    Options:
      --help  Show this message and exit.

    Commands:
      add        Add a new event to a calendar.
      authorize  Fetch an OAuth2 token (requires a browser).
      fetch      Fetch events from the calendar and print in various ways.
      info       Get detailed information about a day or specific event.

## Setup

Requires [GNUPG](https://gnupg.org/) to be installed on your machine with a key
already setup. To setup a key (if you don't already have one):

    gpg --full-generate-key

The GPG key is only needed for local encryption.

To setup, use:

    thallo authorize

This will open your web-browser and ask you to login to your O365 account so
that we can get the OAuth2 token. This will be stored (encrypted) in
`~/.thallo/`. It will prompt you for a `gpg` key ID to use.

