"""Shared embed/view helpers used by all UNO views."""
from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from game.card import COLOR_EMOJI, EMBED_COLOR, Color

if TYPE_CHECKING:
    from game.game import UNOGame


def build_game_embed(game: "UNOGame") -> discord.Embed:
    """Build the main game-state embed shown in the channel."""
    from game.game import GameState

    if game.state == GameState.WAITING:
        embed = discord.Embed(
            title="🃏 UNO — Lobby",
            description=(
                f"**{len(game.players)}/{game.MAX_PLAYERS}** players joined.\n"
                "Press **Join Game** to enter, then the host presses **Start Game**."
            ),
            color=discord.Color.blurple(),
        )
        if game.players:
            embed.add_field(
                name="Players",
                value="\n".join(
                    f"{'👑 ' if p.user_id == game.host_id else '• '}{p.display_name}"
                    for p in game.players
                ),
                inline=False,
            )
        return embed

    if game.state == GameState.FINISHED:
        embed = discord.Embed(
            title="🎉 UNO — Game Over!",
            description=f"**{game.winner.display_name}** wins! 🏆",
            color=discord.Color.gold(),
        )
        embed.add_field(
            name="Final Card Counts",
            value="\n".join(
                f"{'🏆 ' if p is game.winner else '  '}{p.display_name} — {p.card_count} card(s)"
                for p in game.players
            ),
            inline=False,
        )
        embed.add_field(name="Last Action", value=game.last_action, inline=False)
        return embed

    # PLAYING
    top = game.deck.top_card
    colour = EMBED_COLOR.get(game.active_color, discord.Color.blurple())
    top_emoji = COLOR_EMOJI[top.color]
    direction_icon = "↻ Clockwise" if game.direction == 1 else "↺ Counter-clockwise"
    active_emoji = COLOR_EMOJI.get(game.active_color, "❓")

    # Build player list
    player_lines = []
    for i, p in enumerate(game.players):
        is_current = i == game.current_index
        prefix = "▶ " if is_current else "   "
        uno_badge = " 🎴UNO!" if p.called_uno and p.card_count == 1 else ""
        card_str = "🂠" * min(p.card_count, 7) + (f" +{p.card_count - 7}" if p.card_count > 7 else "")
        player_lines.append(f"{prefix}**{p.display_name}**{uno_badge} — {p.card_count} card(s)  {card_str}")

    embed = discord.Embed(
        title="🃏 UNO",
        color=colour,
    )
    embed.add_field(
        name=f"Top Card  {top_emoji} {top.full_name}",
        value=f"Active colour: {active_emoji} **{game.active_color.value.capitalize() if game.active_color else 'TBD'}**",
        inline=True,
    )
    embed.add_field(name="Direction", value=direction_icon, inline=True)
    embed.add_field(
        name="Players",
        value="\n".join(player_lines),
        inline=False,
    )
    embed.add_field(name="Last Action", value=game.last_action, inline=False)

    if game.awaiting_color:
        embed.set_footer(text=f"⏳ {game.players[(game.current_index - game.direction) % len(game.players)].display_name} must choose a colour!")
    else:
        embed.set_footer(text=f"⏳ It's {game.current_player.display_name}'s turn!")

    return embed
