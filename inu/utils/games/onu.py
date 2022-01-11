from abc import abstractmethod, ABC
import math
from pydoc import describe
import random
import re
from typing import (
    Dict,
    List,
    Optional,
    Union,
    Final
    
)
import enum
from collections import deque
import logging


from onu_cards import (
    card_0,
    card_1,
    card_2,
    card_3,
    card_4,
    card_5,
    card_6,
    card_7,
    card_8,
    card_9,
    card_color_changer,
    card_draw_cards_2,
    card_draw_cards_4,
    card_reverse,
    card_stop
)

__all__: Final[List[str]] = [
    "Card",
    "Hand",
    "Onu",
    "Event",
    "TurnErrorEvent",
    "TurnSuccessEvent",
    "CardsReceivedEvent",
    "GameEndEvent",
    "OnuHandler",
]


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class CardColors(enum.Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
    YELLOW = "yellow"
    COLORFULL = "colorfull"

class CardAlgorithms:
    @staticmethod
    def draw_cards(onu: "Onu", hand: "Hand", card: Optional["Card"]):
        if card is None:
            raise RuntimeError("Can't draw cards when card (for draw_value) is not given")
    
    @staticmethod
    def normal(onu: "Onu", hand: "Hand", card: Optional["Card"]):
        pass

    @staticmethod
    def stop(onu: "Onu", hand: "Hand", card: Optional["Card"]):
        pass

    @staticmethod
    def reverse(onu: "Onu", hand: "Hand", card: Optional["Card"]):
        pass
    
    @staticmethod
    def change_color(onu: "Onu", hand: "Hand", card: Optional["Card"]):
        pass

class CardFunctions(enum.Enum):
    DRAW_CARDS = 1
    NORMAL = 11
    STOP = 12
    REVERSE = 13
    CHANGE_COLOR = 14
    
class CardDesigns(enum.Enum):
    CARD_0 = card_0
    CARD_1 = card_1
    CARD_2 = card_2
    CARD_3 = card_3
    CARD_4 = card_4
    CARD_5 = card_5
    CARD_6 = card_6
    CARD_7 = card_7
    CARD_8 = card_8
    CARD_9 = card_9
    COLOR_CHANGER = card_color_changer
    DRAW_CARDS_2 = card_draw_cards_2
    DRAW_CARDS_4 = card_draw_cards_4
    REVERSE = card_reverse
    STOP = card_stop
    
    
class Card:
    def __init__(
        self, 
        function: Union[CardFunctions, List[CardFunctions]],
        color: CardColors,
        card_design: CardDesigns = None,
        value: int = None,
        is_active: bool = False,
        draw_value: int = 0,
    ):
        if card_design is None and value is None:
            raise RuntimeError(
                "Can't build a card without value or card_design. Minimun one of them has to be given"
                )
        self.design = card_design
        if isinstance(function, List):
            self.functions = function
        else:
            self.functions = [function]
        self.color = color
        if card_design is None:
            self.design = self.get_design_from_value(value)
        else:
            self.design = card_design
        if value is None:
            self.value = self.get_value_from_design(self.design)
        else:
            self.value = value
        self.is_active = is_active or bool(draw_value)
        self.draw_value = self.get_draw_value(self.design)
        
    
    @staticmethod
    def get_value_from_design(design: CardDesigns) -> int:
        regex = "CARD_[0-9]"
        if re.match(regex, design.name):
            return int(design.name[-1])
        else:
            return 0
        
    @staticmethod
    def get_design_from_value(value) -> CardDesigns:
        regex = "CARD_[0-9]"
        if not 0 <= value <= 9:
            raise RuntimeError(f"Can't build card with value: {value}")
        for design in CardDesigns:
            if re.match(regex, design.name):
                return design
        raise RuntimeError(f"Card design with matches to value {value} not found")
       
    @staticmethod 
    def get_draw_value(design: CardDesigns) -> int:
        regex = "DRAW_CARDS_[0-9]"
        if re.match(regex, design.name):
            return int(design.name[-1])
        else:
            return 0

    def disable(self):
        """disables the is_active attr, which represents, wether or not the draw_value has been drawen"""
        self.is_active = False

    def can_cast_onto(self, other: "Card") -> bool:
        """
        Checks if <other> can be casted onto this card

        Returns:
        --------
            - (bool) wether or not <other> can be casted onto this card
        
        """
        if other.color == CardColors.COLORFULL:
            print("other card is colorfull")
            return False
        if self.is_active:
            if not other.is_active:
                print("other card is not active")
                return False
        if not (self.functions == other.functions or self.color == other.color):
            print("function or color is not same")
            return False
        return True

    def __str__(self):
        prefix = ""
        for f in self.functions:
            prefix += (
                {
                    CardFunctions.CHANGE_COLOR: "color chagner",
                    CardFunctions.REVERSE: "reverse",
                    CardFunctions.STOP: "stop",
                }.get(f, "")
            )
        number = ""
        if self.value:
            number += str(self.value)
        if self.draw_value > 0:
            number += f"+{self.draw_value}"
        color = self.color.name.lower()
        l = []
        for x in (prefix, number, color):
            if x:
                l.append(x)
        return " | ".join(l)
        



        

class Hand:
    def __init__(
        self,
        name: str,
        id: str,
    ):
        self.name = name
        self.id = id
        self.cards: List[Card] = []

    def __len__(self):
        return len(self.cards)

    def build_card_row(self, cards_per_row: int = 5) -> List[str]:
        """
        Returns:
        --------
            - List[str] A list with strings which represent one row of cards respectively
        """
        rows = []
        row_str = ""
        to_process = []
        for card_i, card in enumerate(self.cards):
            row_str = ""
            to_process.append(card)
            if len(to_process) == cards_per_row or card_i+1 == len(self.cards):
                # draw fist row of <cards_per_row> cards to hand_str
                for i in range(len(card.design.value)):
                    # draw line for line until row is complete
                    row_str += f'{"||".join([card.design.value[i] for card in to_process])}\n'
                rows.append(row_str)
                to_process = []
        return rows

    def __str__(self) -> str:
        return "\n--------------\n".join(self.build_card_row())


class NewCardStack:
    def __init__(self):
        self.stack: List[Card] = []
        self.extend_stack()

    def pop(self, index: int = 0) -> Card:
        "returns a card from the stack"
        if len(self.stack) < 1:
            self.extend_stack()
        return self.stack.pop(index)

    def extend_stack(self):
        numbers = [0,1,2,3,4,5,6,7,8,9]
        colors = [CardColors.RED, CardColors.BLUE, CardColors.GREEN, CardColors.YELLOW]

        for color in colors:
            for _ in range(0,4):
                self.stack.extend(
                    [
                        Card(
                            card_design=CardDesigns.DRAW_CARDS_2,
                            function=CardFunctions.DRAW_CARDS,
                            color=color,
                            draw_value=2,
                            is_active=True,
                        ),

                        Card(
                            card_design=CardDesigns.REVERSE,
                            function=CardFunctions.REVERSE,
                            color=color,
                        ),
                        Card(
                            card_design=CardDesigns.STOP,
                            function=CardFunctions.STOP,
                            color=color,
                        ),
                    ]
                )

            for number in numbers:
                if number == 0:
                    count = 2
                        
                else:
                    count = 4
                for _ in range(0, count):
                    self.stack.append(
                        Card(
                            color=color,
                            function=CardFunctions.NORMAL,
                            value=number,
                        )
                    )
                        
        for _ in range(0,4):
            self.stack.extend(
                [
                    Card(
                        function=[CardFunctions.DRAW_CARDS, CardFunctions.CHANGE_COLOR],
                        color=CardColors.COLORFULL,
                        draw_value=4,
                        is_active=True,
                        card_design=CardDesigns.DRAW_CARDS_4
                    ),
                    Card(
                        function=CardFunctions.CHANGE_COLOR,
                        color=CardColors.COLORFULL,
                        card_design=CardDesigns.COLOR_CHANGER,
                    )
                ]
            ) 
        for _ in range(0,3):
            random.shuffle(self.stack)

class CastOffStack:
    def __init__(self):
        self.stack: deque[Card] = deque()
        self._draw_value = 0

    @property
    def draw_calue(self) -> int:
        if self._draw_value == 0:
            return 1
        else:
            return self._draw_value

    @property
    def top(self) -> Card:
        return self.stack[-1]
        
    def append(self, card: Card):
        if self.draw_calue and CardFunctions.REVERSE in card.functions:
            card.is_active = True
        self.stack.append(card)
        self._draw_value += card.draw_value
        
    def reset_draw_value(self):
        self._draw_value = 0
        self.top.disable()


class Event:
    def __init__(
        self,
        hand: Hand,
        info: str,
    ):
        self.hand = hand
        self.info = info


class CardsReceivedEvent(Event):
    def __init__(
        self,
        hand: Hand,
        info: str,
        cards: List[Card],
    ):
        super().__init__(hand, info)
        self.cards = cards


class TurnErrorEvent(Event):
    def __init__(
        self,
        hand: Hand,
        info: str,
        top_card: Card,
        given_card: Card,

    ):
        super().__init__(hand, info)
        self.top_card = top_card
        self.given_card = given_card


class TurnSuccessEvent(Event):
    def __init__(
        self,
        hand: Hand,
        info: str,
        top_card: Card,

    ):
        super().__init__(hand, info)
        self.top_card = top_card

class GameEndEvent(Event):
    def __init__(
        self,
        hand: Hand,
        info: str,
        winner: Hand,
    ):
        super().__init__(hand, info)
        self.winner = winner


class Onu:
    def __init__(
        self,
        players: Dict[str, str],
        cards_per_hand: int,
    ):
        """
        Constructor of Onu

        Args:
        -----
            - player_names (Dict[int, str]) A mapping from str (id of player) to str (name of player)
            - cards_per_hand (int) how many cards should one hand have
        """
        self.stack: NewCardStack = NewCardStack()

        self.cast_off: CastOffStack = CastOffStack()
        self.cast_off.append(self.stack.pop())

        self.hands: List[Hand] = [Hand(name, str(id)) for id, name in players.items()]
        random.shuffle(self.hands)
        for hand in self.hands:
            for _ in range(0, cards_per_hand):
                hand.cards.append(self.stack.pop())

    def turn(
        self,
        hand: Union[Hand, str],
        card: Card,
        draw: bool = False,
    ) -> Event:
        """
        Main function to control the game
        
        Args:
        ----
            - hand: (`~.Hand`) The player who made an aktion
            - card: (`~.Card`) The card the player has casted
            - draw: (bool) wether or not the player wants to draw cards
        """
        if draw is True and not card is None:
            raise RuntimeError(f"Can't make a turn, where a card is played AND the player draw cards")
        if isinstance(hand, str):
            hand = [h for h in self.hands if h.id == hand][0]
        args = {
            "hand": hand,
            "info": f"You can't cast a {str(card)} onto a {str(self.cast_off.top)}",
            "top_card": self.cast_off.top,   
        }
        if draw:
            for _ in range(0, self.cast_off.draw_calue):
                hand.cards.append(self.stack.pop())
            self.cast_off.reset_draw_value()
            args["info"] = f"Successfully drawn {self.cast_off.draw_calue} cards"
            self.cycle_hands()
            return TurnSuccessEvent(**args)

        if not self.cast_off.top.can_cast_onto(card):
            if card.color == CardColors.COLORFULL:
                args["info"] = "given <card> color is `~.CardColors.COLORFULL` which is not castable"
                return TurnErrorEvent(**args, given_card=card)
            else:
                return TurnErrorEvent(**args, given_card=card)
        hand.cards.remove(card)
        self.cast_off.append(card)
        args["info"] = "Successfully casted card"
        if self.winner:
            return GameEndEvent(**args, winner=self.winner)
        else:
            self.cycle_hands()
            return TurnSuccessEvent(**args)
    
    @property
    def game_over(self) -> bool:
        for hand in self.hands:
            if len(hand.cards) == 0:
                return True
        return False
    
    @property
    def winner(self) -> Optional[Hand]:
        for hand in self.hands:
            if len(hand.cards) == 0:
                return hand
        return None

        
        
    @property
    def current_hand(self):
        return self.hands[0]
    
    def cycle_hands(self):
        """cycles hands in direction left"""
        self.hands.append(self.hands.pop(0))
        

class OnuHandler:
    def __init__(
        self,
        players: Dict[str, str],
        cards_per_hand: int = 10,
    ):
        self.onu = Onu(players, cards_per_hand=cards_per_hand)

    @property
    def current_hand(self) -> Hand:
        return self.onu.current_hand

    def on_event(self, event: Event):
        pass

    def on_turn_success(self, event: TurnSuccessEvent):
        pass

    def on_game_end(self, event: GameEndEvent):
        pass

    def on_turn_error(self, event: TurnErrorEvent):
        pass
    
    def on_cards_received(self, event: CardsReceivedEvent):
        pass
    
    def do_turn(
        self,
        hand: Optional[Hand] = None,
        card: Optional[Card] = None,
        draw_cards: bool = False,
    ):
        event = self.onu.turn(hand, card, draw_cards)
        self.on_event(event)
        if isinstance(event, TurnSuccessEvent):
            self.on_turn_success(event)
        elif isinstance(event, GameEndEvent):
            self.on_game_end(event)
        elif isinstance(event, TurnErrorEvent):
            self.on_turn_error(event)
        elif isinstance(event, CardsReceivedEvent):
            self.on_cards_received(event)
        return event

# bare example
if __name__ == "__main__":
    log.debug("TEST")
    class TerminalOnu(OnuHandler):
        def on_event(self, event: Event):
            print(event)
            print(event.hand)

        def on_turn_success(self, event: TurnSuccessEvent):
            pass

        def on_game_end(self, event: GameEndEvent):
            pass

        def on_turn_error(self, event: TurnErrorEvent):
            print(event.info)
        
        def on_cards_received(self, event: CardsReceivedEvent):
            pass

        def loop(self):
            hand = self.current_hand
            print(self.create_player_hand_embed(hand))
            while not self.onu.game_over:
                for i, card in enumerate(self.current_hand.cards):
                    print(i, "---", card)
                print(f"top card: {self.onu.cast_off.top}")
                card_index = input(f"Which card do you wanna play @{self.current_hand.name}:\n")
                self.do_turn(hand, hand.cards[int(card_index)])

        def create_player_hand_embed(self, hand: Hand):
            display = "Your hand:\n"
            display += str(hand)
            display += f"top card: {str(self.onu.cast_off.top)}"
            display += "\n".join(self.onu.cast_off.top.design.value)
            display += "upcoming players"
            display += "--> ".join(hand.name for hand in self.onu.hands)
            return display
    players = {
        "1": "Olaf",
        "2": "Annie"
    }
    onu = TerminalOnu(players)
    onu.loop()


