"""Core UNO game engine."""
from __future__ import annotations

from enum import Enum
from typing import List, Optional, Tuple

import discord

from game.card import Card, Color, CardType
from game.deck import Deck
from game.player import Player


class GameState(Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"


class UNOGame:
    """Manages the full state of one UNO game inside a Discord channel."""

    INITIAL_HAND = 7
    MIN_PLAYERS = 2
    MAX_PLAYERS = 10

    def __init__(self, channel_id: int, host_id: int) -> None:
        self.channel_id = channel_id
        self.host_id = host_id

        self.players: List[Player] = []
        self.state = GameState.WAITING

        self.deck = Deck()
        self.current_index: int = 0
        self.direction: int = 1   # +1 = clockwise, -1 = counter-clockwise
        self.active_color: Optional[Color] = None

        self.winner: Optional[Player] = None
        self.last_action: str = "Waiting for players to join…"
        self.awaiting_color: bool = False   # True right after a Wild is played

        # Reference to the single Discord message that shows game state
        self.game_message: Optional[discord.Message] = None
        # Reference to the currently active main View (so we can stop it on game end)
        self.current_view: Optional[discord.ui.View] = None
        # Maps user_id -> discord.Interaction for open ephemeral hand panels
        self.hand_panels: dict = {}
        # Reference to the cog's games dict (set externally) for End Game button
        self.games_dict: Optional[dict] = None

    # ==================================================================
    # Lobby management
    # ==================================================================

    def add_player(self, user_id: int, display_name: str) -> bool:
        """Return True if the player was added, False if already in / full."""
        if len(self.players) >= self.MAX_PLAYERS:
            return False
        if any(p.user_id == user_id for p in self.players):
            return False
        self.players.append(Player(user_id, display_name))
        return True

    def remove_player(self, user_id: int) -> bool:
        """Remove a player from the lobby (only valid before game starts)."""
        if self.state != GameState.WAITING:
            return False
        idx = next(
            (i for i, p in enumerate(self.players) if p.user_id == user_id),
            None,
        )
        if idx is None:
            return False
        self.players.pop(idx)
        return True

    # ==================================================================
    # Game start
    # ==================================================================

    def start(self) -> bool:
        """Deal cards and flip the first card.  Returns False if not ready."""
        if self.state != GameState.WAITING:
            return False
        if len(self.players) < self.MIN_PLAYERS:
            return False

        self.state = GameState.PLAYING

        # Deal initial hands
        for player in self.players:
            player.add_cards(self.deck.draw_many(self.INITIAL_HAND))

        # Flip the first card
        first = self.deck.setup_first_card()
        self.active_color = first.color
        self.last_action = (
            f"Game started! First card: **{first.full_name}**"
        )

        # Apply first-card effects
        self._apply_first_card(first)
        return True

    def _apply_first_card(self, card: Card) -> None:
        """Handle the effect of the opening card."""
        if card.card_type == CardType.SKIP:
            skipped = self.current_player
            self._next_turn()
            self.last_action += f"\n⊘ **{skipped.display_name}** is skipped by the opening card!"
        elif card.card_type == CardType.REVERSE:
            if len(self.players) == 2:
                self._next_turn()  # Acts as skip in 2-player
            else:
                self.direction = -1
            self.last_action += "\n↺ Direction reversed by the opening card!"
        elif card.card_type == CardType.DRAW_TWO:
            first_player = self.current_player
            first_player.add_cards(self.deck.draw_many(2))
            self._next_turn()
            self.last_action += (
                f"\n📥 **{first_player.display_name}** draws 2 from the opening card!"
            )

    # ==================================================================
    # Turn helpers
    # ==================================================================

    @property
    def current_player(self) -> Player:
        return self.players[self.current_index]

    def _peek_next_index(self) -> int:
        return (self.current_index + self.direction) % len(self.players)

    def _next_turn(self) -> None:
        self.current_index = self._peek_next_index()

    def _skip_next(self) -> None:
        """Advance past two players (skip the immediate next)."""
        self._next_turn()
        self._next_turn()

    def get_player(self, user_id: int) -> Optional[Player]:
        return next((p for p in self.players if p.user_id == user_id), None)

    def playable_indices(self, player: Player) -> List[int]:
        """Return indices of cards in *player*'s hand that are currently legal."""
        top = self.deck.top_card
        return [
            i
            for i, card in enumerate(player.hand)
            if card.can_play_on(top, self.active_color)
        ]

    # ==================================================================
    # Game actions
    # ==================================================================

    def play_card(
        self, user_id: int, card_index: int
    ) -> Tuple[bool, str]:
        """
        Attempt to play the card at *card_index* in the player's hand.

        Returns (success, result_code) where result_code is one of:
          "ok"           – normal play, turn advanced
          "color_choice" – wild played, caller must call set_wild_color()
          "win"          – player emptied their hand
          error string   – describes why the play was rejected
        """
        if self.state != GameState.PLAYING:
            return False, "The game is not running."

        player = self.get_player(user_id)
        if player is None:
            return False, "You are not in this game."
        if player is not self.current_player:
            return False, "It's not your turn!"
        if self.awaiting_color:
            return False, "Please choose a color for the Wild card first."
        if not (0 <= card_index < len(player.hand)):
            return False, "Invalid card."

        card = player.hand[card_index]
        if not card.can_play_on(self.deck.top_card, self.active_color):
            return False, "You cannot play that card on the current top card."

        # Remove from hand and put on discard
        player.hand.pop(card_index)
        self.deck.discard(card)

        self.last_action = (
            f"**{player.display_name}** played **{card.full_name}**"
        )

        # Win condition
        if player.has_won:
            self.state = GameState.FINISHED
            self.winner = player
            self.last_action += "\n🎉 They played their last card and **WON**!"
            return True, "win"

        # Warn if player should call UNO
        if player.card_count == 1:
            self.last_action += f"\n🃏 **{player.display_name}** has ONE card left!"

        # Apply card effect (advances turn internally)
        self._apply_effect(card)

        if card.is_wild:
            self.awaiting_color = True
            return True, "color_choice"

        return True, "ok"

    def _apply_effect(self, card: Card) -> None:
        """Apply the card's effect and advance the turn pointer."""
        if card.card_type == CardType.NUMBER:
            self.active_color = card.color
            self._next_turn()

        elif card.card_type == CardType.SKIP:
            self.active_color = card.color
            skipped = self.players[self._peek_next_index()]
            self.last_action += (
                f"\n⊘ **{skipped.display_name}** is skipped!"
            )
            self._skip_next()

        elif card.card_type == CardType.REVERSE:
            self.active_color = card.color
            self.direction *= -1
            self.last_action += "\n↺ Direction reversed!"
            if len(self.players) == 2:
                # Reverse acts as skip in 2-player
                self._skip_next()
            else:
                self._next_turn()

        elif card.card_type == CardType.DRAW_TWO:
            self.active_color = card.color
            next_idx = self._peek_next_index()
            victim = self.players[next_idx]
            victim.add_cards(self.deck.draw_many(2))
            self.last_action += (
                f"\n📥 **{victim.display_name}** draws 2 and is skipped!"
            )
            self._skip_next()

        elif card.card_type == CardType.WILD:
            # Color set later via set_wild_color(); just advance turn
            self._next_turn()

        elif card.card_type == CardType.WILD_DRAW_FOUR:
            next_idx = self._peek_next_index()
            victim = self.players[next_idx]
            victim.add_cards(self.deck.draw_many(4))
            self.last_action += (
                f"\n📥 **{victim.display_name}** draws 4 and is skipped!"
            )
            self._skip_next()

    def set_wild_color(self, color: Color) -> bool:
        """Set the active color after a Wild card was played."""
        if not self.awaiting_color:
            return False
        self.active_color = color
        self.awaiting_color = False
        self.last_action += (
            f"\n🎨 Active color set to **{color.value.capitalize()}**"
        )
        return True

    def draw_card(self, user_id: int) -> Tuple[bool, Optional[Card]]:
        """
        Current player draws one card.
        Returns (success, card_drawn).
        """
        if self.state != GameState.PLAYING:
            return False, None

        player = self.get_player(user_id)
        if player is None or player is not self.current_player:
            return False, None
        if self.awaiting_color:
            return False, None

        card = self.deck.draw()
        player.add_cards([card])
        self.last_action = (
            f"**{player.display_name}** drew a card and passed."
        )
        self._next_turn()
        return True, card

    def call_uno(self, user_id: int) -> Tuple[bool, str]:
        """A player announces UNO (they have exactly 1 card)."""
        player = self.get_player(user_id)
        if player is None:
            return False, "You are not in this game."
        if player.card_count != 1:
            return False, f"You have {player.card_count} cards — UNO is only for 1 card!"
        if player.called_uno:
            return False, "You already called UNO!"
        player.called_uno = True
        return True, f"🎴 **{player.display_name}** called **UNO!**"
