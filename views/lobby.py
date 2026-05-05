"""Lobby view: Join Game / Leave Game / Start Game buttons."""
from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from game.game import GameState
from views.helpers import build_game_embed

if TYPE_CHECKING:
    from game.game import UNOGame


class LobbyView(discord.ui.View):
    """
    Shown while the game is in WAITING state.
    Replaced by GameView once the host starts the game.
    """

    def __init__(self, game: "UNOGame", games_dict: dict) -> None:
        super().__init__(timeout=None)
        self.game = game
        self.games = games_dict  # channel_id -> UNOGame, so we can clean up

    @discord.ui.button(label="✅ Join Game", style=discord.ButtonStyle.success, row=0)
    async def join_game(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        added = self.game.add_player(
            interaction.user.id, interaction.user.display_name
        )
        if added:
            embed = build_game_embed(self.game)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            msg = (
                "You're already in the lobby!"
                if self.game.get_player(interaction.user.id)
                else "The lobby is full."
            )
            await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(label="🚪 Leave Game", style=discord.ButtonStyle.danger, row=0)
    async def leave_game(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        removed = self.game.remove_player(interaction.user.id)
        if removed:
            embed = build_game_embed(self.game)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message(
                "You are not in this lobby.", ephemeral=True
            )

    @discord.ui.button(label="🚀 Start Game", style=discord.ButtonStyle.primary, row=0)
    async def start_game(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if interaction.user.id != self.game.host_id:
            await interaction.response.send_message(
                "Only the host can start the game.", ephemeral=True
            )
            return

        if len(self.game.players) < self.game.MIN_PLAYERS:
            await interaction.response.send_message(
                f"Need at least **{self.game.MIN_PLAYERS}** players to start.",
                ephemeral=True,
            )
            return

        success = self.game.start()
        if not success:
            await interaction.response.send_message(
                "Could not start the game (already running?).", ephemeral=True
            )
            return

        # Swap lobby message to game message
        self.game.game_message = interaction.message

        from views.game_view import GameView

        new_embed = build_game_embed(self.game)
        new_view = GameView(self.game)
        self.game.current_view = new_view
        self.stop()
        await interaction.response.edit_message(embed=new_embed, view=new_view)
