"""Fetches verse text from bible-api.com, so the wording always comes from a real translation."""

from dataclasses import dataclass
from urllib.parse import quote

import aiohttp

API_URL = "https://bible-api.com"

# Public-domain translations served by bible-api.com.
TRANSLATIONS = {
    "web": "World English Bible",
    "kjv": "King James Version",
    "asv": "American Standard Version",
    "bbe": "Bible in Basic English",
    "ylt": "Young's Literal Translation",
}


class PassageNotFound(Exception):
    """The reference doesn't exist (for example, a verse number past the end of a chapter)."""


class BibleAPIError(Exception):
    """bible-api.com could not be reached or answered with an error."""


@dataclass(frozen=True)
class Passage:
    reference: str
    text: str
    translation_name: str


def format_verses(verses: list[dict]) -> str:
    """Join verses into one paragraph, numbering them when there is more than one."""
    cleaned = [(v["verse"], " ".join(v["text"].split())) for v in verses]
    if len(cleaned) == 1:
        return cleaned[0][1]
    return " ".join(f"**{number}** {text}" for number, text in cleaned)


async def fetch_passage(session: aiohttp.ClientSession, reference: str, translation: str) -> Passage:
    url = f"{API_URL}/{quote(reference)}"
    try:
        async with session.get(
            url,
            params={"translation": translation},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status == 404:
                raise PassageNotFound(reference)
            if resp.status != 200:
                raise BibleAPIError(f"bible-api.com returned HTTP {resp.status} for {reference!r}")
            data = await resp.json()
    except aiohttp.ClientError as exc:
        raise BibleAPIError(f"Could not reach bible-api.com: {exc}") from exc

    verses = data.get("verses") or []
    if not verses:
        raise PassageNotFound(reference)

    return Passage(
        reference=data.get("reference", reference),
        text=format_verses(verses),
        translation_name=data.get("translation_name") or TRANSLATIONS.get(translation, translation.upper()),
    )
