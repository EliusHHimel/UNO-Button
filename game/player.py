"""Player in a UNO game."""
from __future__ import annotations

from typing import List

from game.card import Card


class Player:
    def __init__(self, user_id: int, display_name: str) -> None:
        self.user_id = user_id
        self.display_name = display_name
        self.hand: List[Card] = []
        self.called_uno: bool = False  # True after player calls UNO with 1 card

    # ------------------------------------------------------------------
    # Hand management
    # ------------------------------------------------------------------

    def add_cards(self, cards: List[Card]) -> None:
        self.hand.extend(cards)

    def remove_card(self, index: int) -> Card:
        """Remove and return the card at *index* from the player's hand."""
        card = self.hand.pop(index)
        self.called_uno = False  # Reset UNO flag whenever hand changes
        return card

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def card_count(self) -> int:
        return len(self.hand)

    @property
    def has_won(self) -> bool:
        return len(self.hand) == 0

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Player({self.display_name!r}, {self.card_count} cards)"
