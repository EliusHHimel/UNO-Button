"""UNO Discord Bot — entry point."""
from __future__ import annotations

import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN: str = os.environ["DISCORD_TOKEN"]
GUILD_ID: str | None = os.getenv("GUILD_ID") or None

intents = discord.Intents.default()
# Message content intent is not required for slash-command-only bots
# but keep it off unless needed to reduce permission footprint.


class UNOBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix="!",   # Prefix unused; slash commands only
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self) -> None:
        # Load the UNO cog
        await self.load_extension("cogs.uno_cog")

        # Sync slash commands
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Slash commands synced to guild {GUILD_ID}.")
        else:
            await self.tree.sync()
            print("Slash commands synced globally (may take up to 1 hour to propagate).")

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Game(name="UNO 🃏  |  /uno to play")
        )


def main() -> None:
    bot = UNOBot()
    asyncio.run(bot.start(TOKEN))


if __name__ == "__main__":
    main()
