"""Main in-channel game view: Play Hand, Draw Card, UNO! buttons."""
from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from game.game import GameState
from views.helpers import build_game_embed

if TYPE_CHECKING:
    from game.game import UNOGame


class GameView(discord.ui.View):
    """
    Persistent (timeout=None) view attached to the single game message.
    All players see the same buttons; access control is enforced in callbacks.
    """

    def __init__(self, game: "UNOGame") -> None:
        super().__init__(timeout=None)
        self.game = game
        # Dynamically disable Draw / Play when awaiting wild color
        waiting = game.awaiting_color
        self.add_item(_ViewHandButton(game, disabled=waiting))
        self.add_item(_DrawCardButton(game, disabled=waiting))
        self.add_item(_CallUNOButton(game))


# ------------------------------------------------------------------
# View Hand / Play Card button
# ------------------------------------------------------------------

class _ViewHandButton(discord.ui.Button):
    def __init__(self, game: "UNOGame", disabled: bool = False) -> None:
        super().__init__(
            label="🃏 View / Play Hand",
            style=discord.ButtonStyle.primary,
            disabled=disabled,
            row=0,
        )
        self.game = game

    async def callback(self, interaction: discord.Interaction) -> None:
        player = self.game.get_player(interaction.user.id)
        if player is None:
            await interaction.response.send_message(
                "You are not in this game.", ephemeral=True
            )
            return

        if self.game.state != GameState.PLAYING:
            await interaction.response.send_message(
                "The game is not currently running.", ephemeral=True
            )
            return

        from views.hand_view import HandView, build_hand_embed

        embed = build_hand_embed(player, self.game)
        view = HandView(player, self.game)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ------------------------------------------------------------------
# Draw Card button
# ------------------------------------------------------------------

class _DrawCardButton(discord.ui.Button):
    def __init__(self, game: "UNOGame", disabled: bool = False) -> None:
        super().__init__(
            label="📥 Draw Card",
            style=discord.ButtonStyle.secondary,
            disabled=disabled,
            row=0,
        )
        self.game = game

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.game.state != GameState.PLAYING:
            await interaction.response.send_message(
                "The game is not running.", ephemeral=True
            )
            return

        player = self.game.get_player(interaction.user.id)
        if player is None:
            await interaction.response.send_message(
                "You are not in this game.", ephemeral=True
            )
            return
        if player is not self.game.current_player:
            await interaction.response.send_message(
                f"It's **{self.game.current_player.display_name}**'s turn, not yours.",
                ephemeral=True,
            )
            return
        if self.game.awaiting_color:
            await interaction.response.send_message(
                "A color must be chosen for the Wild card first.", ephemeral=True
            )
            return

        success, card = self.game.draw_card(interaction.user.id)
        if not success:
            await interaction.response.send_message(
                "Could not draw a card right now.", ephemeral=True
            )
            return

        # Refresh the public game message
        new_embed = build_game_embed(self.game)
        new_view = GameView(self.game)
        if self.game.current_view:
            self.game.current_view.stop()
        self.game.current_view = new_view
        await self.game.game_message.edit(embed=new_embed, view=new_view)

        await interaction.response.send_message(
            f"📥 You drew **{card.full_name}**. Turn passed.",
            ephemeral=True,
        )


# ------------------------------------------------------------------
# Call UNO button
# ------------------------------------------------------------------

class _CallUNOButton(discord.ui.Button):
    def __init__(self, game: "UNOGame") -> None:
        super().__init__(
            label="🎴 UNO!",
            style=discord.ButtonStyle.success,
            row=0,
        )
        self.game = game

    async def callback(self, interaction: discord.Interaction) -> None:
        success, msg = self.game.call_uno(interaction.user.id)
        if success:
            # Broadcast the UNO call by updating the game embed
            self.game.last_action = msg
            new_embed = build_game_embed(self.game)
            new_view = GameView(self.game)
            if self.game.current_view:
                self.game.current_view.stop()
            self.game.current_view = new_view
            await self.game.game_message.edit(embed=new_embed, view=new_view)
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
