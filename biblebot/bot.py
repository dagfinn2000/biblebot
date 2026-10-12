"""The Discord side: a /verse slash command and a "Find a verse" message menu."""

import logging

import aiohttp
import discord
from discord import app_commands

from .bible import TRANSLATIONS, BibleAPIError, Passage, PassageNotFound, fetch_passage
from .config import Config
from .picker import ChatLine, PickerError, VerseChoice, VersePicker

log = logging.getLogger(__name__)

EMBED_COLOR = discord.Color.from_rgb(201, 162, 39)
TRANSLATION_CHOICES = [app_commands.Choice(name=f"{name} ({key.upper()})", value=key) for key, name in TRANSLATIONS.items()]
# Messages read before the one picked from the "Find a verse" menu, for context.
CONTEXT_BEFORE_FOCUS = 5


def to_chat_line(message: discord.Message, focus: bool = False) -> ChatLine | None:
    content = message.clean_content.strip()
    if not content:
        return None
    return ChatLine(author=message.author.display_name, content=content[:1500], focus=focus)


def build_embed(choice: VerseChoice, passage: Passage, about: discord.Message | None = None) -> discord.Embed:
    text = passage.text if len(passage.text) <= 3500 else passage.text[:3500].rsplit(" ", 1)[0] + " …"
    embed = discord.Embed(title=passage.reference, description=text, color=EMBED_COLOR)
    embed.add_field(name="Why this verse", value=choice.reason[:1024], inline=False)
    if about is not None:
        embed.add_field(name="In reply to", value=f"[{about.author.display_name}'s message]({about.jump_url})", inline=False)
    embed.set_footer(text=passage.translation_name)
    return embed


class BibleBot(discord.Client):
    def __init__(self, config: Config):
        intents = discord.Intents.default()
        # Needed so /verse can read the recent messages in a channel.
        intents.message_content = True
        super().__init__(intents=intents)

        self.config = config
        self.picker = VersePicker(model=config.claude_model)
        self.http_session: aiohttp.ClientSession | None = None
        self.tree = app_commands.CommandTree(self)
        self.tree.on_error = self.on_app_command_error
        self._register_commands()

    def _register_commands(self) -> None:
        cooldown = app_commands.checks.cooldown(1, self.config.cooldown_seconds, key=lambda i: i.user.id)

        @self.tree.command(name="verse", description="Share a Bible verse that fits the conversation or a topic")
        @app_commands.describe(
            topic="Optional: what the verse should be about. Leave empty to use the recent messages.",
            translation="Bible translation to quote",
        )
        @app_commands.choices(translation=TRANSLATION_CHOICES)
        @cooldown
        async def verse(
            interaction: discord.Interaction,
            topic: str | None = None,
            translation: app_commands.Choice[str] | None = None,
        ) -> None:
            await interaction.response.defer(thinking=True)
            chosen_translation = translation.value if translation else self.config.default_translation

            if topic:
                await self.share_verse(interaction, chosen_translation, topic=topic)
                return

            lines = await self.recent_lines(interaction.channel, limit=self.config.context_messages)
            if not lines:
                await interaction.followup.send(
                    "I couldn't read any recent messages here. Try `/verse topic:...`, "
                    "or right-click a message and choose Apps → Find a verse."
                )
                return
            await self.share_verse(interaction, chosen_translation, lines=lines)

        @self.tree.context_menu(name="Find a verse")
        @cooldown
        async def find_a_verse(interaction: discord.Interaction, message: discord.Message) -> None:
            await interaction.response.defer(thinking=True)

            focus = to_chat_line(message, focus=True)
            if focus is None:
                await interaction.followup.send("That message has no text for me to read.")
                return
            before = await self.recent_lines(message.channel, limit=CONTEXT_BEFORE_FOCUS, before=message)
            await self.share_verse(interaction, self.config.default_translation, lines=[*before, focus], about=message)

    async def recent_lines(self, channel, limit: int, before: discord.Message | None = None) -> list[ChatLine]:
        """Read the last few human messages in a channel, oldest first."""
        if channel is None or not hasattr(channel, "history"):
            return []
        lines = []
        try:
            async for message in channel.history(limit=limit, before=before):
                if message.author.bot:
                    continue
                line = to_chat_line(message)
                if line:
                    lines.append(line)
        except discord.Forbidden:
            log.warning("Missing permission to read history in channel %s", getattr(channel, "id", "?"))
            return []
        lines.reverse()
        return lines

    async def share_verse(
        self,
        interaction: discord.Interaction,
        translation: str,
        lines: list[ChatLine] | None = None,
        topic: str | None = None,
        about: discord.Message | None = None,
    ) -> None:
        avoid: list[str] = []
        try:
            # If Claude names a reference that doesn't exist, ask once more for a different one.
            for _ in range(2):
                choice = await self.picker.pick(lines or (), topic=topic, avoid=avoid)
                try:
                    passage = await fetch_passage(self.http_session, choice.reference, translation)
                    break
                except PassageNotFound:
                    log.warning("Reference not found: %s", choice.reference)
                    avoid.append(choice.reference)
            else:
                await interaction.followup.send("Sorry, I couldn't find a matching verse this time. Please try again.")
                return
        except PickerError as exc:
            log.warning("Picker failed: %s", exc)
            await interaction.followup.send("Sorry, I couldn't pick a verse right now. Please try again in a moment.")
            return
        except BibleAPIError as exc:
            log.warning("Bible API failed: %s", exc)
            await interaction.followup.send("Sorry, the Bible text service isn't answering right now. Please try again later.")
            return

        await interaction.followup.send(embed=build_embed(choice, passage, about))

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.CommandOnCooldown):
            message = f"Please wait {error.retry_after:.0f} more seconds before asking for another verse."
        else:
            log.error("Command failed", exc_info=error)
            message = "Something went wrong. Please try again."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    async def setup_hook(self) -> None:
        self.http_session = aiohttp.ClientSession(headers={"User-Agent": "biblebot (Discord bot)"})
        if self.config.guild_id:
            # Syncing to one server is instant; global sync can take up to an hour to show up.
            guild = discord.Object(id=self.config.guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
        else:
            synced = await self.tree.sync()
        log.info("Synced %d commands", len(synced))

    async def on_ready(self) -> None:
        log.info("Logged in as %s (model %s)", self.user, self.config.claude_model)

    async def close(self) -> None:
        if self.http_session:
            await self.http_session.close()
        await super().close()
