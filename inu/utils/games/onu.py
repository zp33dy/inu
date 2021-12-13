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


from .onu_cards import (
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
    "CardsReceivedEvent"
]

class CardColors(enum.Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
    YELLOW = "yellow"
    COLORFULL = "colorfull"


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
        self.is_active = is_active
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
            return False
        if self.is_active:
            if not other.is_active:
                return False
        if not self.functions == other.functions or not self.color == other.color:
            return False
        return True

    def __str__(self):
        prefix = []
        for f in self.functions:
            prefix.append(
                {
                    CardFunctions.CHANGE_COLOR: "color chagner",
                    CardFunctions.REVERSE: "reverse",
                    CardFunctions.STOP: "stop"
                }.get(f)
            )
        prefix = " ".join(prefix)
        number = ""
        if self.value:
            if self.draw_value > 0:
                number += "+"
            number += str(self.value)
        color = self.color.value.lower()
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
                            is_active=True,
                        ),
                        Card(
                            card_design=CardDesigns.STOP,
                            function=CardFunctions.STOP,
                            color=color,
                            is_active=True,
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
                        function=CardFunctions.DRAW_CARDS,
                        color=CardColors.COLORFULL,
                        draw_value=4,
                        is_active=True,
                    ),
                    Card(
                        function=CardFunctions.CHANGE_COLOR,
                        color=CardColors.COLORFULL,
                    )
                ]
            ) 
        for _ in range(0,3):
            random.shuffle(self.stack)

class CastOffStack:
    def __init__(self):
        self.stack: deque[Card] = deque()

    @property
    def top(self):
        self.stack[-1]
        
    def append(self, item: Card):
        self.stack.append(item)


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


class Onu:
    def __init__(
        self,
        players: Dict[int, str],
        cards_per_hand: int,
    ):
        """
        Constructor of Onu

        Args:
        -----
            - player_names (Dict[int, str]) A mapping from int (id of player) to str (name of player)
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
        

    
