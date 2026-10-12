from biblebot.bible import Passage
from biblebot.bot import build_embed
from biblebot.picker import VerseChoice


def test_embed_contents():
    embed = build_embed(VerseChoice("John 3:16", "God's love."), Passage("John 3:16", "For God so loved", "World English Bible"))
    assert embed.title == "John 3:16"
    assert embed.description == "For God so loved"
    assert embed.fields[0].value == "God's love."
    assert embed.footer.text == "World English Bible"


def test_long_passage_is_trimmed():
    embed = build_embed(VerseChoice("Psalm 119", "Long."), Passage("Psalm 119", "word " * 2000, "WEB"))
    assert len(embed.description) <= 3502
    assert embed.description.endswith("…")
