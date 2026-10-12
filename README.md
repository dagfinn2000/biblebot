# biblebot

A Discord bot that answers a conversation with a fitting Bible verse.

- **`/verse`** reads the last few messages in the channel and shares a passage that fits them.
- **`/verse topic: anxiety`** shares a passage about a topic you name.
- **Right-click a message → Apps → Find a verse** replies to that one message.

Claude reads the messages and picks the passage. The verse text itself comes from
[bible-api.com](https://bible-api.com), so the wording is always the real translation and
never made up by the AI. The default translation is the World English Bible (WEB); KJV, ASV,
BBE and YLT are also available.

## Setup

You need Python 3.10 or newer, a Discord account, and an Anthropic account.

### 1. Create the Discord bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and click **New Application**. Name it (for example "BibleBot").
2. Open the **Bot** tab:
   - Click **Reset Token**, copy the token and keep it somewhere safe. This is your `DISCORD_TOKEN`.
   - Under **Privileged Gateway Intents**, turn on **Message Content Intent** and save. Without it, `/verse` can't read the recent messages.
3. Open the **OAuth2** tab, then **URL Generator**:
   - Scopes: tick `bot` and `applications.commands`.
   - Bot permissions: tick `View Channels`, `Send Messages`, `Embed Links` and `Read Message History`.
   - Open the generated URL in your browser and add the bot to your server.

### 2. Get an Anthropic API key

1. Sign in at [console.anthropic.com](https://console.anthropic.com), add a little credit under **Billing**, and create a key under **API Keys**. This is your `ANTHROPIC_API_KEY`.
2. Cost: with the default model (`claude-opus-5-5`) each verse costs roughly one US cent. Set `CLAUDE_MODEL=claude-haiku-5-5` in `.env` to make it about 40 times cheaper; it is usually good enough for this job. You can also set a monthly spend limit in the console.

### 3. Install

```bash
git clone https://github.com/dagfinn2000/biblebot.git
cd biblebot
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
```

Open `.env` in a text editor and paste in `DISCORD_TOKEN` and `ANTHROPIC_API_KEY`.

Tip: while testing, also set `GUILD_ID` to your server's ID (in Discord, enable Developer Mode under
Settings → Advanced, then right-click your server → Copy Server ID). Commands then appear
instantly instead of taking up to an hour.

### 4. Run it

```bash
python -m biblebot
```

You should see `Logged in as BibleBot#1234`. Try `/verse` in your server. Stop the bot with Ctrl+C.

### 5. Keep it running (Linux or Raspberry Pi)

To start the bot automatically and restart it if it crashes, install it as a systemd service:

```bash
sed "s/YOUR_USER/$USER/g" deploy/biblebot.service | sudo tee /etc/systemd/system/biblebot.service
sudo systemctl daemon-reload
sudo systemctl enable --now biblebot
```

This assumes you cloned into your home folder. Check on it with `systemctl status biblebot`
and read its logs with `journalctl -u biblebot -f`.

On Windows you can use Task Scheduler to run `.venv\Scripts\python.exe -m biblebot` at startup,
with the repo folder as "Start in".

## Settings

All settings live in `.env`; see `.env.example` for the full list.

| Setting | Default | What it does |
| --- | --- | --- |
| `CLAUDE_MODEL` | `claude-opus-5-5` | Model that picks the verse |
| `DEFAULT_TRANSLATION` | `web` | `web`, `kjv`, `asv`, `bbe` or `ylt` |
| `CONTEXT_MESSAGES` | `10` | How many recent messages `/verse` reads |
| `COOLDOWN_SECONDS` | `15` | How long each person waits between verses |
| `GUILD_ID` | empty | Sync commands to one server instantly |

## Development

```bash
pip install -r requirements-dev.txt
pytest
```
