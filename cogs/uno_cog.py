"""UNO slash-command cog."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from game.game import UNOGame, GameState
from views.helpers import build_game_embed
from views.lobby import LobbyView


class UNOCog(commands.Cog):
    """Provides the /uno command that starts a UNO lobby in the channel."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # One active game per channel; channel_id -> UNOGame
        self.games: dict[int, UNOGame] = {}

    # ------------------------------------------------------------------
    # /uno  — create a lobby (or refuse if one already exists)
    # ------------------------------------------------------------------

    @app_commands.command(name="uno", description="Start a UNO game in this channel!")
    async def uno(self, interaction: discord.Interaction) -> None:
        channel_id = interaction.channel_id

        existing = self.games.get(channel_id)
        if existing and existing.state != GameState.FINISHED:
            await interaction.response.send_message(
                "A UNO game is already running in this channel!\n"
                "The game host can end it with `/unoend`, or wait for it to finish.",
                ephemeral=True,
            )
            return

        # Create a new game and register it
        game = UNOGame(channel_id=channel_id, host_id=interaction.user.id)
        # Automatically add the host as the first player
        game.add_player(interaction.user.id, interaction.user.display_name)
        game.games_dict = self.games
        self.games[channel_id] = game

        embed = build_game_embed(game)
        view = LobbyView(game, self.games)
        await interaction.response.send_message(embed=embed, view=view)

        # Store the message so the lobby can later edit it into the game view
        game.game_message = await interaction.original_response()

    # ------------------------------------------------------------------
    # /unoend  — force-end a game (host or server admin only)
    # ------------------------------------------------------------------

    @app_commands.command(name="unoend", description="Force-end the current UNO game.")
    async def unoend(self, interaction: discord.Interaction) -> None:
        channel_id = interaction.channel_id
        game = self.games.get(channel_id)

        if game is None or game.state == GameState.FINISHED:
            await interaction.response.send_message(
                "No active UNO game in this channel.", ephemeral=True
            )
            return

        is_admin = (
            isinstance(interaction.user, discord.Member)
            and interaction.user.guild_permissions.manage_guild
        )
        if interaction.user.id != game.host_id and not is_admin:
            await interaction.response.send_message(
                "Only the game host or a server admin can end the game.",
                ephemeral=True,
            )
            return

        # Clean up
        if game.current_view:
            game.current_view.stop()
        game.state = GameState.FINISHED
        del self.games[channel_id]

        embed = discord.Embed(
            title="🛑 UNO Game Ended",
            description=f"The game was force-ended by {interaction.user.mention}.",
            color=discord.Color.red(),
        )
        if game.game_message:
            await game.game_message.edit(embed=embed, view=None)

        await interaction.response.send_message(
            "Game ended.", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UNOCog(bot))
