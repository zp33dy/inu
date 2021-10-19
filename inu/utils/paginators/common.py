import asyncio
from contextlib import suppress
from typing import (
    Any,
    Callable,
    Optional,
    Sequence,
    TypeVar,
    Union,
    List,
    Final,
    Dict
)
import traceback
import logging
from abc import abstractmethod, ABCMeta

import hikari
from hikari.embeds import Embed
from hikari.messages import Message
from hikari.impl import ActionRowBuilder
from hikari import ButtonStyle, ComponentInteraction, InteractionCreateEvent, MessageCreateEvent, NotFoundError
from hikari.events.base_events import Event
import lightbulb
from lightbulb.context import Context


__all__: Final[List[str]] = ["Paginator", "BaseListener", "BaseObserver", "EventListener", "EventObserver"]
_Sendable = Union[Embed, str]
T = TypeVar("T")

# I know this is kinda to much just for a paginator - but I want to learn design patterns, so I do it

class BaseListener(metaclass=ABCMeta):
    """A Base Listener. This will later notify all observers on event"""
    @property
    def observers(self):
        raise NotImplementedError

    @abstractmethod
    def subscribe():
        pass
    
    @abstractmethod
    def unsubscribe():
        pass

    @abstractmethod
    async def notify():
        pass


class BaseObserver(metaclass=ABCMeta):
    """A Base Observer. It will receive events from a Listener"""
    @property
    def callback(self):
        raise NotImplementedError

    @abstractmethod
    async def on_event(self, event):
        raise NotImplementedError





class EventObserver(BaseObserver):
    """An Observer used to trigger hikari events, given from the paginator"""
    def __init__(self, callback: Callable, event: str):
        self._callback = callback
        self.event = event
        self.name: Optional[str] = None
        self.paginator: Paginator

    @property
    def callback(self) -> Callable:
        return self._callback

    async def on_event(self, event: Event):
        await self.callback(self.paginator, event)



class EventListener(BaseListener):
    """A Listener which receives events from a Paginator and notifies its observers about it"""
    def __init__(self):
        self._observers: Dict[str, List[EventObserver]] = {}
    @property
    def observers(self):
        return self._observers

    def subscribe(self, observer: EventObserver, event: Event):
        if event not in self._observers.keys():
            self._observers[str(event)] = []
        self._observers[str(event)].append(observer)
    
    def unsubscribe(self, observer: EventObserver, event: Event):
        if event not in self._observers.keys():
            return
        self._observers[str(event)].remove(observer)

    async def notify(self, event: Event):
        try:
            if str(type(event)) not in self._observers.keys():
                return
            for observer in self._observers[str(type(event))]:
                await observer.on_event(event)
        except Exception as e:
            traceback.print_exc()

def listener(event: Any):
    """A decorator to add listeners to a paginator"""
    def decorator(func: Callable):
        return EventObserver(callback=func, event=str(event))
    return decorator



class Paginator():
    def __init__(
        self,
        page_s: Union[List[Embed], List[str]],
        timeout: int = 120,
        component_factory: Callable[[int], ActionRowBuilder] = None,
        components_factory: Callable[[int], List[ActionRowBuilder]] = None,
        disable_pagination: bool = False,
        disable_component: bool = False,
        disable_components: bool = False,
        disable_paginator_when_one_site: bool = True,
    ):
        self._pages: Union[List[Embed], List[str]] = page_s
        self._component: Optional[ActionRowBuilder] = None
        self._components: Optional[List[ActionRowBuilder]] = None
        self._disable_components = disable_components
        self._disable_component = disable_component
        self._exit_when_one_site = disable_paginator_when_one_site
        self._task: asyncio.Task
        self._message: Message
        self._component_factory = component_factory
        self._components_factory = components_factory
        self.bot: lightbulb.Bot
        self.ctx: Context

        
        self.listener = EventListener()
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)
        self.timeout = timeout

        # paginator configuration
        self.pagination = not disable_pagination
        if self.pagination:
            self._stop = False
            self._position: int = 0
            self.compact = len(page_s) <= 2
        

        # register all listeners

        for name, obj in type(self).__dict__.items():
            if isinstance(obj, EventObserver):
                obj = getattr(self, name)
                obj.name = name
                obj.paginator = self
                self.listener.subscribe(obj, obj.event)

    @property
    def pages(self):
        return self._pages

    @property
    def component(self) -> Optional[ActionRowBuilder]:
        if self._disable_component:
            return None
        if self._component_factory is not None:
            return self._component_factory(self._position)
        elif self._component is not None:
            return self._component
        elif hasattr(self, "build_default_component"):
            return getattr(self, "build_default_component")(self._position)
        else:
            raise RuntimeError((
                "Nothing specified for `component`. "
                "Consider passing in a component factory or set"
                "a value for `instance`._component"
                ))

    @property
    def components(self) -> Union[List[ActionRowBuilder]]:
        if self._disable_components:
            return []
        if self._components_factory is not None:
            return self._components_factory(self._position)
        elif self._components is not None:
            return self._components
        elif hasattr(self, "build_default_components"):
            return getattr(self, "build_default_components")(self._position)
        else:
            raise RuntimeError((
                "Nothing specified for `components`. "
                "Consider passing in a components_factory or set"
                "a value for `instance`._components"
                ))

    def interaction_pred(self, event: InteractionCreateEvent):
        if not isinstance((i := event.interaction), ComponentInteraction):
            return False
        return (
            i.user.id == self.ctx.author.id
            and i.message.id == self._message.id
        )

    def message_pred(self, event: MessageCreateEvent):
        msg = event.message
        return (
            msg.channel_id == self.ctx.channel_id
            and self.ctx.author.id == msg.author.id
        )

    def build_default_component(self, position = None) -> Optional[ActionRowBuilder]:
        if not self.pagination:
            return None
        def button_factory( 
            disable_when_index_is: Union[Callable[[Optional[int]], bool]] = (lambda x: False),
            label: str = "",
            style = ButtonStyle.SECONDARY,
            custom_id: Optional[str] = None,
            emoji: Optional[str] = None,
            action_row_builder: ActionRowBuilder = ActionRowBuilder(),
            
        ) -> ActionRowBuilder:
            state: bool = disable_when_index_is(self._position)
            if not custom_id:
                custom_id = label
            if not emoji:
                btn = (
                    action_row_builder
                    .add_button(style, custom_id)
                    .set_is_disabled(state)
                    .set_label(label)
                    .add_to_container()
                )
            else:
                btn = (
                    action_row_builder
                    .add_button(style, custom_id)
                    .set_is_disabled(state)
                    .set_emoji(emoji)
                    .add_to_container()
                )
            return btn

        action_row = None
        if not self.compact:
            action_row = button_factory(
                custom_id="first", 
                emoji="⏮", 
                disable_when_index_is=lambda p: p == 0
            )
        action_row = button_factory(
            custom_id="previous",
            emoji="◀",
            action_row_builder=action_row or ActionRowBuilder(),
            disable_when_index_is=lambda p: p == 0,
        )
        button_factory(
            custom_id="stop",
            emoji="✖",
            action_row_builder=action_row,
            style=ButtonStyle.DANGER,
        )
        button_factory(
            custom_id="next",
            emoji="▶",
            action_row_builder=action_row,
            disable_when_index_is=lambda p: p == len(self.pages)-1,
        )
        if not self.compact:
            button_factory(
                custom_id="last",
                emoji="⏭",
                action_row_builder=action_row,
                disable_when_index_is=lambda p: p == len(self.pages)-1,
            )

        return action_row



    async def send(self, content: _Sendable, interaction: Optional[ComponentInteraction] = None):
        try:
            kwargs: Dict[str, Any] = {}
            if interaction:
                update_message = interaction.create_initial_response
                kwargs["response_type"] = hikari.ResponseType.MESSAGE_UPDATE
            else:
                update_message = self._message.edit
            if not self._disable_component:
                kwargs["component"] = self.component
            elif not self._disable_components:
                kwargs["components"] = self.components

            if isinstance(content, str):
                kwargs["content"] = content
                await update_message(**kwargs)
            elif isinstance(content, Embed):
                kwargs["embed"] = content
                await update_message(**kwargs)
            else:
                raise TypeError(f"<content> can't be an isntance of {type(content).__name__}")
        except Exception as e:
            print(e)

    async def stop(self):
        self._stop = True
        with suppress(NotFoundError):
            if not self._disable_component:
                await self._message.edit(component=None)
            elif not self._disable_components:
                await self._message.edit(components=[])

    async def start(self, ctx: Context) -> None:
        self.ctx = ctx
        self.bot = ctx.bot
        if len(self.pages) < 1:
            raise RuntimeError("<pages> must have minimum 1 item")
        elif len(self.pages) == 1 and self._exit_when_one_site:
            if isinstance(self.pages[0], Embed):
                self._message = await ctx.respond(
                    embed=self.pages[0],
                )
            else:
                self._message = await ctx.respond(
                    content=self.pages[0],
                )
            return

        self._position = 0
        kwargs = {}
        if not self._disable_component:
            kwargs["component"] = self.component
        elif not self._disable_components:
            kwargs["components"] = self.components
        if isinstance(self.pages[0], Embed):
            self._message = await ctx.respond(
                embed=self.pages[0],
                **kwargs
            )
        else:
            self._message = await ctx.respond(
                content=self.pages[0],
                **kwargs
            )
        
        if len(self.pages) == 1 and self._exit_when_one_site:
            return
        self._position = 0
        self._task = asyncio.create_task(self.pagination_loop())
        


    async def pagination_loop(self):
        if self.timeout > int(60*15):
            raise RuntimeError("<timeout> has a max time of 15 min")
        def create_event(event, predicate: Callable):
            return self.bot.wait_for(
                event,
                timeout=self.timeout,
                predicate=predicate
            )

        while not self._stop:
            try:
                events = [
                    create_event(InteractionCreateEvent, self.interaction_pred),
                    create_event(MessageCreateEvent, self.message_pred),
                ]
                done, pending = await asyncio.wait(
                    [asyncio.create_task(task) for task in events],
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                self._stop = True
                return
            # maybe called from outside
            if self._stop:
                return
            try:
                event = done.pop().result()
            except Exception:
                pass
            for e in pending:
                e.cancel()
            await self.dispatch_event(event)
            
    async def dispatch_event(self, event: Event):
        if isinstance(event, InteractionCreateEvent):
            await self.paginate(event)
        await self.listener.notify(event)

    async def paginate(self, event):
        id = event.interaction.custom_id or None
        last_position = self._position

        if id == "first":
            self._position = 0
        elif id == "previous":
            if self._position == 0:
                return
            self._position -= 1
        elif id == "stop":
            await self.delete_presence()
            await self.stop()
        elif id == "next":
            if self._position == (len(self.pages)-1):
                return
            self._position += 1
        elif id == "last":
            self._position = len(self.pages)-1

        if last_position != self._position:
            await self._update_position(interaction=event.interaction)

    async def delete_presence(self):
        """Deletes this message, and invokation message, if invocation was in a guild"""
        if self.ctx.channel is not None:
            await self.ctx.channel.delete_messages(
                self._message,
                self.ctx.message,
            )

    async def _update_position(self, interaction: ComponentInteraction):
        await self.send(content=self.pages[self._position], interaction=interaction)

    # usage
    # @listener(InteractionCreateEvent)
    # async def on_interaction(self, event):
    #     print("interaction received")

    # @listener(GuildMessageCreateEvent)
    # async def on_message(self, event):
    #     print("message received")

            

def navigation_row(
    position: int, 
    len_pages: int,
    compact: bool = False,
) -> ActionRowBuilder:
    def button_factory( 
        disable_when_index_is: Union[Callable[[Optional[int]], bool]] = (lambda x: False),
        label: str = "",
        style = ButtonStyle.SECONDARY,
        custom_id: Optional[str] = None,
        emoji: Optional[str] = None,
        action_row_builder: ActionRowBuilder = ActionRowBuilder(),
        
    ) -> ActionRowBuilder:
        state: bool = disable_when_index_is(position)
        if not custom_id:
            custom_id = label
        if not emoji:
            btn = (
                action_row_builder
                .add_button(style, custom_id)
                .set_is_disabled(state)
                .set_label(label)
                .add_to_container()
            )
        else:
            btn = (
                action_row_builder
                .add_button(style, custom_id)
                .set_is_disabled(state)
                .set_emoji(emoji)
                .add_to_container()
            )
        return btn

    action_row = None
    if not compact:
        action_row = button_factory(
            custom_id="first", 
            emoji="⏮", 
            disable_when_index_is=lambda p: p == 0
        )
    action_row = button_factory(
        custom_id="previous",
        emoji="◀",
        action_row_builder=action_row or ActionRowBuilder(),
        disable_when_index_is=lambda p: p == 0,
    )
    button_factory(
        custom_id="stop",
        emoji="✖",
        action_row_builder=action_row,
        style=ButtonStyle.DANGER,
    )
    button_factory(
        custom_id="next",
        emoji="▶",
        action_row_builder=action_row,
        disable_when_index_is=lambda p: p == len_pages-1,
    )
    if not compact:
        button_factory(
            custom_id="last",
            emoji="⏭",
            action_row_builder=action_row,
            disable_when_index_is=lambda p: p == len_pages-1,
        )

    return action_row
            
