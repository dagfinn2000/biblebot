"""Start the bot with `python -m biblebot`."""

import logging
import sys

import discord

from .bot import BibleBot
from .config import ConfigError, load_config


def main() -> None:
    discord.utils.setup_logging(level=logging.INFO)
    try:
        config = load_config()
    except ConfigError as exc:
        sys.exit(f"Configuration error: {exc}")

    BibleBot(config).run(config.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
