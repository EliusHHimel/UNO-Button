"""UNO deck: 108 cards, draw pile, discard pile."""
from __future__ import annotations

import random
from typing import List

from game.card import Card, Color, CardType


def _build_fresh_deck() -> List[Card]:
    """Return a shuffled standard 108-card UNO deck."""
    cards: List[Card] = []

    for color in (Color.RED, Color.BLUE, Color.GREEN, Color.YELLOW):
        # One 0
        cards.append(Card(color, CardType.NUMBER, 0))
        # Two of each 1-9
        for n in range(1, 10):
            cards.append(Card(color, CardType.NUMBER, n))
            cards.append(Card(color, CardType.NUMBER, n))
        # Two Skip, two Reverse, two Draw Two
        for _ in range(2):
            cards.append(Card(color, CardType.SKIP))
            cards.append(Card(color, CardType.REVERSE))
            cards.append(Card(color, CardType.DRAW_TWO))

    # Four Wild, four Wild Draw Four
    for _ in range(4):
        cards.append(Card(Color.WILD, CardType.WILD))
        cards.append(Card(Color.WILD, CardType.WILD_DRAW_FOUR))

    random.shuffle(cards)
    return cards


class Deck:
    """Manages the draw pile and discard pile for one UNO game."""

    def __init__(self) -> None:
        self._draw: List[Card] = _build_fresh_deck()
        self._discard: List[Card] = []

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self) -> Card:
        """Draw one card, reshuffling the discard pile if necessary."""
        if not self._draw:
            self._reshuffle_discard()
        return self._draw.pop()

    def draw_many(self, n: int) -> List[Card]:
        return [self.draw() for _ in range(n)]

    # ------------------------------------------------------------------
    # Discarding
    # ------------------------------------------------------------------

    def discard(self, card: Card) -> None:
        self._discard.append(card)

    def setup_first_card(self) -> Card:
        """
        Draw cards until we get a non-wild card and put it on the discard
        pile as the opening card.  Returns the card placed.
        """
        while True:
            card = self.draw()
            if not card.is_wild:
                self._discard.append(card)
                return card
            # Put wild back at the bottom so we don't lose it
            self._draw.insert(0, card)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def top_card(self) -> Card:
        return self._discard[-1]

    @property
    def draw_pile_size(self) -> int:
        return len(self._draw)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reshuffle_discard(self) -> None:
        """Move all but the top discard card back into the draw pile."""
        if len(self._discard) <= 1:
            # Emergency: rebuild from scratch (should be extremely rare)
            self._draw = _build_fresh_deck()
            return
        top = self._discard.pop()
        self._draw = self._discard
        random.shuffle(self._draw)
        self._discard = [top]
