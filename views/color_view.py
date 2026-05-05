"""Color picker view shown after a Wild card is played (ephemeral)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from game.card import Color, COLOR_EMOJI
from views.helpers import build_game_embed

if TYPE_CHECKING:
    from game.game import UNOGame


_COLOR_BUTTONS = [
    (Color.RED,    "🔴 Red",    discord.ButtonStyle.danger),
    (Color.BLUE,   "🔵 Blue",   discord.ButtonStyle.primary),
    (Color.GREEN,  "🟢 Green",  discord.ButtonStyle.success),
    (Color.YELLOW, "🟡 Yellow", discord.ButtonStyle.secondary),
]


class ColorPickerView(discord.ui.View):
    """Four colour buttons; ephemeral follow-up after a Wild play."""

    def __init__(self, game: "UNOGame") -> None:
        super().__init__(timeout=120)
        self.game = game
        for color, label, style in _COLOR_BUTTONS:
            self.add_item(_ColorButton(game, color, label, style))


class _ColorButton(discord.ui.Button):
    def __init__(
        self,
        game: "UNOGame",
        color: Color,
        label: str,
        style: discord.ButtonStyle,
    ) -> None:
        super().__init__(label=label, style=style)
        self.game = game
        self.chosen_color = color

    async def callback(self, interaction: discord.Interaction) -> None:
        # Only the player who played the wild can choose
        acting_player_idx = (
            self.game.current_index - self.game.direction
        ) % len(self.game.players)
        acting_player = self.game.players[acting_player_idx]

        if interaction.user.id != acting_player.user_id:
            await interaction.response.send_message(
                "Only the player who played the Wild card picks the colour!",
                ephemeral=True,
            )
            return

        self.game.set_wild_color(self.chosen_color)

        # Refresh the main game message
        from views.game_view import GameView

        new_embed = build_game_embed(self.game)
        new_view = GameView(self.game)
        if self.game.current_view:
            self.game.current_view.stop()
        self.game.current_view = new_view
        await self.game.game_message.edit(embed=new_embed, view=new_view)

        emoji = COLOR_EMOJI[self.chosen_color]
        await interaction.response.edit_message(
            content=f"{emoji} Colour set to **{self.chosen_color.value.capitalize()}**! Your turn is over.",
            embed=None,
            view=None,
        )
        self.view.stop()
