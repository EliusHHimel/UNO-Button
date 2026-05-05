# UNO-Button 🃏

A fully playable **UNO Discord bot** where an entire game is driven through
**Discord Buttons** — no commands needed mid-game.

---

## Features

| Feature | Details |
|---|---|
| **Single message** | The whole game lives in one channel message that updates after every action |
| **Ephemeral hand** | Each player views & plays their private hand via an ephemeral (invisible to others) button panel |
| **Full card set** | 108-card standard deck: Numbers 0-9, Skip, Reverse, Draw Two, Wild, Wild Draw Four |
| **All effects** | Skip, Reverse (with 2-player rule), Draw Two, Wild colour picker, Wild Draw Four |
| **Paginated hand** | Up to 20 card buttons per page; auto-pagination for large hands |
| **UNO call** | 🎴 UNO! button broadcasts the announcement to the whole channel |
| **2–10 players** | Works for any supported player count |
| **Force-end** | Host or server admin can end a stalled game with `/unoend` |

---

## Quick Start

### 1. Create a Discord application & bot

1. Go to <https://discord.com/developers/applications> and create a new application.
2. Under **Bot**, click **Add Bot** and copy the **Token**.
3. Under **OAuth2 → URL Generator**, select the `bot` and `applications.commands`
   scopes, then choose at minimum the `Send Messages` / `Read Messages` permissions.
4. Use the generated URL to invite the bot to your server.

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env and paste your bot token
```

Set `GUILD_ID` to your server's ID for **instant** slash-command syncing while
testing (leave blank for global deployment).

### 4. Run

```bash
python bot.py
```

---

## How to Play

1. In any channel, type `/uno` to open a lobby.
2. Players click **✅ Join Game** (the host joins automatically).
3. Once 2+ players have joined, the host clicks **🚀 Start Game**.
4. On your turn:
   - Click **🃏 View / Play Hand** to see your cards (only you can see them).
   - Tap a **coloured card button** to play it, or…
   - Click **📥 Draw Card** (in the hand panel or the main buttons) to draw and pass.
5. After playing a **Wild / Wild Draw Four**, choose a colour from the picker.
6. Click **🎴 UNO!** when you're down to one card.
7. First player to empty their hand wins! 🏆

---

## Project Structure

```
UNO-Button/
├── bot.py              Entry point
├── requirements.txt
├── .env.example
├── game/
│   ├── card.py         Card & Color enums, playability logic
│   ├── deck.py         108-card deck with auto-reshuffle
│   ├── player.py       Player state
│   └── game.py         Game engine (turns, effects, win detection)
├── views/
│   ├── helpers.py      Shared embed builder
│   ├── lobby.py        Join / Leave / Start lobby view
│   ├── game_view.py    Main in-channel game buttons
│   ├── hand_view.py    Ephemeral paginated hand panel
│   └── color_view.py   Wild card colour picker
└── cogs/
    └── uno_cog.py      /uno and /unoend slash commands
```
