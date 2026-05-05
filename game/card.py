"""Card definitions for UNO."""
from __future__ import annotations

from enum import Enum
from typing import Optional

import discord


class Color(Enum):
    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"
    WILD = "wild"  # Wild cards before a color is chosen


class CardType(Enum):
    NUMBER = "number"
    SKIP = "skip"
    REVERSE = "reverse"
    DRAW_TWO = "draw_two"
    WILD = "wild"
    WILD_DRAW_FOUR = "wild_draw_four"


# Display helpers
COLOR_EMOJI: dict[Color, str] = {
    Color.RED: "🔴",
    Color.BLUE: "🔵",
    Color.GREEN: "🟢",
    Color.YELLOW: "🟡",
    Color.WILD: "🃏",
}

BUTTON_STYLE: dict[Color, discord.ButtonStyle] = {
    Color.RED: discord.ButtonStyle.danger,
    Color.BLUE: discord.ButtonStyle.primary,
    Color.GREEN: discord.ButtonStyle.success,
    Color.YELLOW: discord.ButtonStyle.secondary,
    Color.WILD: discord.ButtonStyle.secondary,
}

EMBED_COLOR: dict[Color, discord.Color] = {
    Color.RED: discord.Color.red(),
    Color.BLUE: discord.Color.blue(),
    Color.GREEN: discord.Color.green(),
    Color.YELLOW: discord.Color.yellow(),
    Color.WILD: discord.Color.purple(),
}

# Sort order for organizing hands
_COLOR_ORDER: dict[Color, int] = {
    Color.RED: 0,
    Color.BLUE: 1,
    Color.GREEN: 2,
    Color.YELLOW: 3,
    Color.WILD: 4,
}
_TYPE_ORDER: dict[CardType, int] = {
    CardType.NUMBER: 0,
    CardType.SKIP: 1,
    CardType.REVERSE: 2,
    CardType.DRAW_TWO: 3,
    CardType.WILD: 4,
    CardType.WILD_DRAW_FOUR: 5,
}


class Card:
    """Represents a single UNO card."""

    def __init__(
        self,
        color: Color,
        card_type: CardType,
        number: Optional[int] = None,
    ) -> None:
        self.color = color
        self.card_type = card_type
        self.number = number  # 0-9 for NUMBER cards, None otherwise

    # ------------------------------------------------------------------
    # Game logic
    # ------------------------------------------------------------------

    @property
    def is_wild(self) -> bool:
        return self.color == Color.WILD

    def can_play_on(self, top_card: Card, active_color: Color) -> bool:
        """Return True if this card is a legal play on *top_card*."""
        # Wild cards are always playable
        if self.is_wild:
            return True
        # Same active colour
        if self.color == active_color:
            return True
        # Same card type (and same number for NUMBER cards)
        if self.card_type == top_card.card_type:
            if self.card_type == CardType.NUMBER:
                return self.number == top_card.number
            return True
        return False

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    @property
    def label(self) -> str:
        """Short label suitable for a Discord button (≤ 80 chars)."""
        emoji = COLOR_EMOJI[self.color]
        if self.card_type == CardType.NUMBER:
            return f"{emoji} {self.number}"
        labels = {
            CardType.SKIP: f"{emoji} Skip",
            CardType.REVERSE: f"{emoji} Rev",
            CardType.DRAW_TWO: f"{emoji} +2",
            CardType.WILD: "🃏 Wild",
            CardType.WILD_DRAW_FOUR: "🃏 +4",
        }
        return labels.get(self.card_type, "?")

    @property
    def full_name(self) -> str:
        """Human-readable card name."""
        if self.is_wild:
            return (
                "Wild Draw Four"
                if self.card_type == CardType.WILD_DRAW_FOUR
                else "Wild"
            )
        color_name = self.color.value.capitalize()
        type_names = {
            CardType.NUMBER: str(self.number),
            CardType.SKIP: "Skip",
            CardType.REVERSE: "Reverse",
            CardType.DRAW_TWO: "Draw Two",
        }
        return f"{color_name} {type_names.get(self.card_type, '?')}"

    @property
    def button_style(self) -> discord.ButtonStyle:
        return BUTTON_STYLE[self.color]

    def sort_key(self) -> tuple:
        num = self.number if self.number is not None else 99
        return (_COLOR_ORDER[self.color], _TYPE_ORDER[self.card_type], num)

    def __repr__(self) -> str:
        return self.full_name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return (
            self.color == other.color
            and self.card_type == other.card_type
            and self.number == other.number
        )
