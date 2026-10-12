import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from biblebot import bible
from biblebot.bible import PassageNotFound, fetch_passage, format_verses


def test_format_single_verse_strips_whitespace():
    assert format_verses([{"verse": 16, "text": "For God so\nloved the world  "}]) == "For God so loved the world"


def test_format_multiple_verses_are_numbered():
    text = format_verses([{"verse": 6, "text": "A\n"}, {"verse": 7, "text": "B\n"}])
    assert text == "**6** A **7** B"


@pytest.fixture
async def fake_api(monkeypatch):
    async def handler(request):
        if request.match_info["ref"] == "Psalm 151:1":
            return web.json_response({"error": "not found"}, status=404)
        assert request.query["translation"] == "kjv"
        return web.json_response({
            "reference": "Philippians 4:6-7",
            "verses": [{"verse": 6, "text": "Be careful for nothing\n"}, {"verse": 7, "text": "And the peace of God\n"}],
            "translation_name": "King James Version",
        })

    app = web.Application()
    app.router.add_get("/{ref}", handler)
    server = TestServer(app)
    await server.start_server()
    monkeypatch.setattr(bible, "API_URL", str(server.make_url("")).rstrip("/"))
    async with aiohttp.ClientSession() as session:
        yield session
    await server.close()


async def test_fetch_passage(fake_api):
    passage = await fetch_passage(fake_api, "Philippians 4:6-7", "kjv")
    assert passage.reference == "Philippians 4:6-7"
    assert passage.translation_name == "King James Version"
    assert passage.text.startswith("**6** Be careful")


async def test_fetch_missing_passage(fake_api):
    with pytest.raises(PassageNotFound):
        await fetch_passage(fake_api, "Psalm 151:1", "kjv")
