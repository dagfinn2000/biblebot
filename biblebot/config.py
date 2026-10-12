"""Settings read from environment variables (or a .env file next to the code)."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    discord_token: str
    claude_model: str
    default_translation: str
    context_messages: int
    cooldown_seconds: float
    guild_id: int | None


def load_config() -> Config:
    load_dotenv()

    discord_token = os.getenv("DISCORD_TOKEN", "").strip()
    if not discord_token:
        raise ConfigError("DISCORD_TOKEN is not set. Copy .env.example to .env and fill it in.")
    if not os.getenv("ANTHROPIC_API_KEY", "").strip():
        raise ConfigError("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in.")

    guild_id = os.getenv("GUILD_ID", "").strip()

    return Config(
        discord_token=discord_token,
        claude_model=os.getenv("CLAUDE_MODEL", "claude-opus-5-5").strip(),
        default_translation=os.getenv("DEFAULT_TRANSLATION", "web").strip().lower(),
        context_messages=int(os.getenv("CONTEXT_MESSAGES", "10")),
        cooldown_seconds=float(os.getenv("COOLDOWN_SECONDS", "15")),
        guild_id=int(guild_id) if guild_id else None,
    )
