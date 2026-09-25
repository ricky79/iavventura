import logging

# The game writes this log to a file (see app/cli.py); without a handler it must stay silent,
# not end up in the player's terminal.
logging.getLogger(__name__).addHandler(logging.NullHandler())
