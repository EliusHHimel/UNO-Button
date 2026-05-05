"""Ephemeral hand view: lets a player see and play their cards."""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

import discord

from game.card import Card
from game.game import GameState
from views.helpers import build_game_embed

if TYPE_CHECKING:
    from game.game import UNOGame
    from game.player import Player

# Maximum card buttons per page (4 rows × 5 = 20); row 5 reserved for nav
CARDS_PER_PAGE = 20


def build_hand_embed(player: "Player", game: "UNOGame") -> discord.Embed:
    """Embed shown above the hand-view buttons."""
    from game.card import COLOR_EMOJI

    is_my_turn = (
        game.state == GameState.PLAYING
        and game.current_player is player
        and not game.awaiting_color
    )

    top = game.deck.top_card
    active_emoji = COLOR_EMOJI.get(game.active_color, "❓")
    top_emoji = COLOR_EMOJI[top.color]

    description_lines = [
        f"**Top card:** {top_emoji} {top.full_name}",
        f"**Active colour:** {active_emoji} {game.active_color.value.capitalize() if game.active_color else 'TBD'}",
        "",
    ]

    if game.state != GameState.PLAYING:
        description_lines.append("The game is not running.")
    elif game.awaiting_color:
        description_lines.append("Waiting for the Wild-card player to choose a colour…")
    elif is_my_turn:
        playable = game.playable_indices(player)
        if playable:
            description_lines.append(
                f"✅ It's **your turn**! You have **{len(playable)}** playable card(s). "
                "Enabled buttons = playable."
            )
        else:
            description_lines.append(
                "❌ No playable cards — press **📥 Draw Card** below."
            )
    else:
        description_lines.append(
            f"⏳ It's **{game.current_player.display_name}**'s turn. "
            "You can view but not play."
        )

    return discord.Embed(
        title=f"🃏 Your Hand  ({player.card_count} cards)",
        description="\n".join(description_lines),
        color=discord.Color.blurple(),
    )


class HandView(discord.ui.View):
    """
    Paginated view of a player's hand.
    Playable cards are shown as enabled buttons; others are greyed out.
    A Draw Card button appears at the bottom when it's the player's turn.
    """

    def __init__(self, player: "Player", game: "UNOGame", page: int = 0) -> None:
        super().__init__(timeout=120)
        self.player = player
        self.game = game
        self.page = page
        self._build_buttons()

    # ------------------------------------------------------------------
    # Internal builders
    # ------------------------------------------------------------------

    def _sorted_hand(self) -> List[Tuple[int, Card]]:
        """Return [(original_index, card), ...] sorted for display."""
        return sorted(
            enumerate(self.player.hand),
            key=lambda ic: ic[1].sort_key(),
        )

    def _build_buttons(self) -> None:
        self.clear_items()

        is_my_turn = (
            self.game.state == GameState.PLAYING
            and self.game.current_player is self.player
            and not self.game.awaiting_color
        )
        playable_set = (
            set(self.game.playable_indices(self.player)) if is_my_turn else set()
        )

        sorted_hand = self._sorted_hand()
        total_pages = max(1, (len(sorted_hand) + CARDS_PER_PAGE - 1) // CARDS_PER_PAGE)
        self.page = min(self.page, total_pages - 1)

        page_cards = sorted_hand[
            self.page * CARDS_PER_PAGE : (self.page + 1) * CARDS_PER_PAGE
        ]

        for orig_idx, card in page_cards:
            playable = orig_idx in playable_set
            self.add_item(
                _CardButton(
                    orig_idx=orig_idx,
                    card=card,
                    game=self.game,
                    player=self.player,
                    enabled=playable and is_my_turn,
                )
            )

        # Navigation row
        prev_btn = discord.ui.Button(
            label="◀",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page == 0),
            row=4,
        )
        prev_btn.callback = self._prev_page

        page_btn = discord.ui.Button(
            label=f"{self.page + 1}/{total_pages}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
            row=4,
        )

        next_btn = discord.ui.Button(
            label="▶",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page >= total_pages - 1),
            row=4,
        )
        next_btn.callback = self._next_page

        draw_btn = discord.ui.Button(
            label="📥 Draw Card",
            style=discord.ButtonStyle.primary,
            disabled=not is_my_turn,
            row=4,
        )
        draw_btn.callback = self._draw_card

        close_btn = discord.ui.Button(
            label="✖ Close",
            style=discord.ButtonStyle.danger,
            row=4,
        )
        close_btn.callback = self._close

        self.add_item(prev_btn)
        self.add_item(page_btn)
        self.add_item(next_btn)
        self.add_item(draw_btn)
        self.add_item(close_btn)

    # ------------------------------------------------------------------
    # Navigation callbacks
    # ------------------------------------------------------------------

    async def _prev_page(self, interaction: discord.Interaction) -> None:
        self.page -= 1
        self._build_buttons()
        await interaction.response.edit_message(
            embed=build_hand_embed(self.player, self.game),
            view=self,
        )

    async def _next_page(self, interaction: discord.Interaction) -> None:
        self.page += 1
        self._build_buttons()
        await interaction.response.edit_message(
            embed=build_hand_embed(self.player, self.game),
            view=self,
        )

    async def _draw_card(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.player.user_id:
            await interaction.response.send_message("This isn't your hand!", ephemeral=True)
            return

        success, card = self.game.draw_card(interaction.user.id)
        if not success:
            await interaction.response.send_message(
                "You can't draw right now.", ephemeral=True
            )
            return

        # Refresh main game message
        await _refresh_game_message(self.game)

        await interaction.response.edit_message(
            content=(
                f"📥 You drew **{card.full_name}**. Your turn is over.\n"
                "You can view your updated hand from the main message."
            ),
            embed=None,
            view=None,
        )
        self.stop()

    async def _close(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message(
            content="Hand closed.", embed=None, view=None
        )
        self.stop()


# ------------------------------------------------------------------
# Card button
# ------------------------------------------------------------------

class _CardButton(discord.ui.Button):
    def __init__(
        self,
        orig_idx: int,
        card: Card,
        game: "UNOGame",
        player: "Player",
        enabled: bool,
    ) -> None:
        super().__init__(
            label=card.label,
            style=card.button_style if enabled else discord.ButtonStyle.secondary,
            disabled=not enabled,
        )
        self.orig_idx = orig_idx
        self.card = card
        self.game = game
        self.player = player

    async def callback(self, interaction: discord.Interaction) -> None:
        # Sanity checks
        if interaction.user.id != self.player.user_id:
            await interaction.response.send_message("This isn't your hand!", ephemeral=True)
            return

        if self.game.state != GameState.PLAYING:
            await interaction.response.edit_message(
                content="The game has already ended.", embed=None, view=None
            )
            return

        # The hand index may have shifted if a card was removed earlier in
        # the same page.  Locate the card by value to get the current index.
        try:
            current_idx = next(
                i
                for i, c in enumerate(self.player.hand)
                if c == self.card
            )
        except StopIteration:
            await interaction.response.send_message(
                "That card is no longer in your hand.", ephemeral=True
            )
            return

        success, result = self.game.play_card(interaction.user.id, current_idx)

        if not success:
            await interaction.response.send_message(result, ephemeral=True)
            return

        if result == "color_choice":
            from views.color_view import ColorPickerView

            embed = discord.Embed(
                title="🎨 Choose a Colour",
                description="Pick the active colour for your Wild card:",
                color=discord.Color.dark_grey(),
            )
            await interaction.response.edit_message(
                embed=embed, view=ColorPickerView(self.game)
            )
            self.view.stop()
            return

        # "ok" or "win"
        await _refresh_game_message(self.game)

        if result == "win":
            await interaction.response.edit_message(
                content="🎉 **You played your last card and WON!** Congratulations!",
                embed=None,
                view=None,
            )
        else:
            await interaction.response.edit_message(
                content=f"✅ You played **{self.card.full_name}**. Turn complete!",
                embed=None,
                view=None,
            )
        self.view.stop()


# ------------------------------------------------------------------
# Shared helper
# ------------------------------------------------------------------

async def _refresh_game_message(game: "UNOGame") -> None:
    """Edit the main game message with the latest embed + view."""
    if game.game_message is None:
        return

    from game.game import GameState
    from views.game_view import GameView

    if game.state == GameState.FINISHED:
        if game.current_view:
            game.current_view.stop()
            game.current_view = None
        await game.game_message.edit(embed=build_game_embed(game), view=None)
    else:
        new_view = GameView(game)
        if game.current_view:
            game.current_view.stop()
        game.current_view = new_view
        await game.game_message.edit(embed=build_game_embed(game), view=new_view)
