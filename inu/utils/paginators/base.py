import asyncio
from contextlib import suppress
from pprint import pformat
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
from copy import deepcopy
import textwrap

import hikari
from hikari.embeds import Embed
from hikari.messages import Message
from hikari.impl import ActionRowBuilder
from hikari import ButtonStyle, ComponentInteraction, GuildMessageCreateEvent, InteractionCreateEvent, MessageCreateEvent, NotFoundError, ResponseType
from hikari.events.base_events import Event
import lightbulb
from lightbulb.context import Context


log = logging.getLogger(__name__)
log.setLevel(logging.WARNING)

__all__: Final[List[str]] = ["Paginator", "BaseListener", "BaseObserver", "EventListener", "EventObserver"]
_Sendable = Union[Embed, str]
T = TypeVar("T")

count = 0

# I know this is kinda to much just for a paginator - but I want to learn design patterns, so I do it
class PaginatorReadyEvent(hikari.Event):
    def __init__(self, bot: lightbulb.BotApp):
        self.bot = bot

    @property
    def app(self):
        return self.bot

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
    def __init__(self, pag):
        self._pag = pag
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
        if str(type(event)) not in self._observers.keys():
            return
        for observer in self._observers[str(type(event))]:
            log.debug(f"listener pag: {self._pag.count} | notify observer with id {observer.paginator.count} | {observer.paginator._message.id} | {observer.paginator}")
            await observer.on_event(event)

def listener(event: Any):
    """A decorator to add listeners to a paginator"""
    def decorator(func: Callable):
        log.debug("listener registered")
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
        disable_component: bool = True,
        disable_components: bool = False,
        disable_paginator_when_one_site: bool = True,
        listen_to_events: List[Any] = [],
        compact: Optional[bool] = None,
        default_site: Optional[int] = 0,
        download: Union[Callable[["Paginator"], str], str, bool] = False,
        first_message_kwargs: Dict[str, Any] = {},
    ):
        """
        ### A Paginator with many options

        Args:
        -----
            - pege_s: (List[Embed] | List[str]) the page*s the Paginator should paginate
            - timeout: (int, default=120) the seconds the paginator has to be inactive to "shutdown"; maximum is 15*60 min
            - component_factory: (Callable[[int], ActionRowBuilder], default=None) a custom component builder; the input is the index of the site
            - components_factory: (Callable[[int], ActionRowBuilder], default=None) a custom components builder; the input is the index of the site
            - disable_component: (bool, default=False) wether or not the component of the paginator should be disabled
            - disable_components: (bool, default=False) wether or not the components of the paginator should be disabled
            - disable_paginator_when_one_site: (bool, default=True) wether or not the pagination should be disabled when the length of the pages is 1
            - listen_to_events: (List[hikari.Event]) events the bot should listen to. These are needed to use them later with the `listener` decorator
            - compact: (bool) display only necessary components
            - download: (str | Callable[[Paginator], str] | bool, default=False)
                - (str) this will be the content of the file
                - (Callable[[Paginator], str]) A function, which takes in `self` and returns the file content as string
                - (bool) If True, the pagination embeds|strings will be automatically convertet into a str; 
                         If False, deactivate download functionallity at all
            - first_message_kwargs: (Dict[str, Any], default) kwargs, which should be added to the first created message
        Note:
        -----
            - the listener is always listening to 2 events:
                - GuildMessageCreateEvent (only when in context with the Paginator)
                - ComponentInteractionEvent (only component interaction, only when in context with the paginator)
                - PaginatorReadyEvent
            - create custom components with:
                either 
                - passing in `component(s)_factory`
                or
                - overriding `build_default_component(s)`; args: self, position (int)
            - to first_message_kwargs: this will add the kwargs, even if the kwargs are already in the method. So this could raise errors
        """
        global count
        count  += 1
        self.count = count
        
        self._pages: Union[List[Embed], List[str]] = page_s
        self._component: Optional[ActionRowBuilder] = None
        self._components: Optional[List[ActionRowBuilder]] = None
        self._disable_components = disable_components
        self._disable_component = disable_component
        if not self._disable_component and not self._disable_components:
            raise RuntimeError(f"Paginator.__init__: disable_component can be False OR disable_components can be False. Not both")
        self._exit_when_one_site = disable_paginator_when_one_site
        self._task: asyncio.Task
        self._message: Message
        self._component_factory = component_factory
        self._components_factory = components_factory
        self._default_site = default_site
        self._download: Union[Callable[[Paginator], str], str, None] = download
        self._first_message_kwargs = first_message_kwargs or {}
        self.bot: lightbulb.BotApp
        self.ctx: Context

        
        self.listener = EventListener(self)
        self.log = log
        self.timeout = timeout
        self.listen_to_events = listen_to_events

        # paginator configuration
        self.pagination = not disable_pagination
        self._stop = False
        if self.pagination:
            self._position: int = 0
        if compact is None:
            self.compact = len(page_s) <= 1
        else:
            self.compact = compact
        

        # register all listeners

        for name, obj in type(self).__dict__.items():
            if isinstance(obj, EventObserver):
                obj = getattr(self, name)
                copy_obj = deepcopy(obj)  
                # why deepcopy?: the `obj` seems to be, no matter if pag is a new instance, always the same obj.
                # so it would add without deepcopy always the same obj with was configured in the first instance of `self.__cls__`
                copy_obj.name = name
                copy_obj.paginator = self
                self.listener.subscribe(copy_obj, copy_obj.event)

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
    def components(self) -> List[ActionRowBuilder]:
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
            self.log.debug("False interaction pred")
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

    def button_factory(
        self,
        disable_when_index_is: Callable[[Optional[int]], bool] = (lambda x: False),
        label: str = "",
        style = ButtonStyle.SECONDARY,
        custom_id: Optional[str] = None,
        emoji: Optional[str] = None,
        action_row_builder: Optional[ActionRowBuilder] = None,
        
    ) -> ActionRowBuilder:
        if action_row_builder is None:
            action_row_builder = ActionRowBuilder()
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

    def _navigation_row(self, position = None) -> Optional[ActionRowBuilder]:
        if not self.pagination:
            return None


        action_row = None
        if not self.compact:
            action_row = self.button_factory(
                custom_id="first", 
                emoji="⏮", 
                disable_when_index_is=lambda p: p == 0
            )
        action_row = self.button_factory(
            custom_id="previous",
            emoji="◀",
            action_row_builder=action_row or ActionRowBuilder(),
            disable_when_index_is=lambda p: p == 0,
        )
        self.button_factory(
            custom_id="stop",
            emoji="✖",
            action_row_builder=action_row,
            style=ButtonStyle.DANGER,
        )
        self.button_factory(
            custom_id="next",
            emoji="▶",
            action_row_builder=action_row,
            disable_when_index_is=lambda p: p == len(self.pages)-1,
        )
        if not self.compact:
            self.button_factory(
                custom_id="last",
                emoji="⏭",
                action_row_builder=action_row,
                disable_when_index_is=lambda p: p == len(self.pages)-1,
            )

        return action_row
    
    def build_default_component(self, position=None) -> Optional[ActionRowBuilder]:
        return self._navigation_row(position)
    
    def build_default_components(self, position=None) -> Optional[List[Optional[ActionRowBuilder]]]:
        action_rows = [self.build_default_component(position)]
        action_row = None
        if not self.compact:
            action_row = self.button_factory(
                custom_id="search",
                emoji="🔍"
            )
            action_rows.append(action_row)        
        return action_rows
    
    @property
    def download(self) -> Optional[str]:
        if not self._download:
            return None
        elif isinstance(self._download, Callable):
            return self._download(self)
        elif isinstance(self._download, str):
            return self._download
        elif isinstance(self._download, bool) and self._download is True:
            return self._pages_to_str()

    def _pages_to_str(self) -> str:
        text = ""
        if isinstance(self._pages, List[Embed]):
            for embed in self._pages:
                text += self._embed_to_md(embed)
        elif isinstance(self._pages, List[str]):
            text = "\n".join(
                line for page in [textwrap.wrap(text, width=100) for page in self._pages] for line in page
            )
        else:
            raise RuntimeError(f"Can't convert `self._pages` of type {type(self._pages)} to str")
        return text

    @staticmethod
    def _embed_to_md(embed: hikari.Embed) -> str:
        text = ""
        if embed.title:
            text += f"# {embed.title}"
        if embed.description:
            text += "\n#### ".textwrap.wrap(embed.description, 100)
        for field in embed.fields:
            text += f"\n## {field.name}"
            text += "\n#### ".textwrap.wrap(field.value, 100)
        text += "\n----------------------------------------\n"
        return text
        



    async def send(self, content: _Sendable, interaction: Optional[ComponentInteraction] = None):
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

        # if self._download:
        #     kwargs["attachments"] = [hikari.Bytes(self.download, "content")]

        if isinstance(content, str):
            kwargs["content"] = content
        elif isinstance(content, Embed):
            kwargs["embed"] = content  
        else:
            raise TypeError(f"<content> can't be an isntance of {type(content).__name__}")

        await update_message(**kwargs)

    async def stop(self):
        self._stop = True
        with suppress(NotFoundError, hikari.ForbiddenError):
            if self.components:
                await self._message.edit(components=[])
            elif self.component:
                await self._message.edit(component=None)    
            # await self._message.remove_all_reactions()

    async def start(self, ctx: Context) -> hikari.Message:
        """
        starts the pagination
        
        Returns:
        -------
            - (hikari.Message) the message, which was used by the paginator
        """
        self.ctx = ctx
        self.bot = ctx.bot
        if len(self.pages) < 1:
            raise RuntimeError("<pages> must have minimum 1 item")
        elif len(self.pages) == 1 and self._exit_when_one_site:
            if isinstance(self.pages[0], Embed):
                msg_proxy = await ctx.respond(
                    embed=self.pages[0],
                    **self._first_message_kwargs
                )
            else:
                msg_proxy = await ctx.respond(
                    content=self.pages[0],
                    **self._first_message_kwargs
                )
            return await msg_proxy.message()

        self._position = 0
        kwargs = self._first_message_kwargs
        if not self._disable_component:
            kwargs["component"] = self.component
        elif not self._disable_components:
            kwargs["components"] = self.components
        if (download := self.download):
            kwargs["attachment"] = hikari.Bytes(download, "content.md")
        if isinstance(self.pages[self._default_site], Embed):
            msg_proxy = await ctx.respond(
                embed=self.pages[0],
                **kwargs
            )
        else:
            msg_proxy = await ctx.respond(
                content=self.pages[self._default_site],
                **kwargs
            )
        self._message = await msg_proxy.message()
        if len(self.pages) == 1 and self._exit_when_one_site:
            return self._message
        self.log.debug("enter loop")
        self._position = 0
        await self.post_start(ctx)
        return self._message

    async def post_start(self, ctx: Context):
        try:
            await self.dispatch_event(PaginatorReadyEvent(self.bot))
            await self.pagination_loop()
        except Exception:
            self.log.error(traceback.format_exc())
        self.log.debug("end of pagination")

    async def pagination_loop(self):
        try:
            # if self.timeout > int(60*15):
            #     raise RuntimeError("<timeout> has a max time of 15 min")
            def create_event(event, predicate: Callable = None):
                if predicate:
                    return self.bot.wait_for(
                        event,
                        timeout=self.timeout,
                        predicate=predicate
                    )
                else:
                    return self.bot.wait_for(
                        event,
                        timeout=self.timeout,
                    )

            while not self._stop:
                self.log.debug("loop")
                try:
                    events = [
                        create_event(InteractionCreateEvent, self.interaction_pred),
                        create_event(GuildMessageCreateEvent, self.message_pred),
                    ]
                    # adding user specific events
                    always_true = lambda _ : True
                    for event in self.listen_to_events:
                        events.append(create_event(event))
                    done, pending = await asyncio.wait(
                        [asyncio.create_task(task) for task in events],
                        return_when=asyncio.FIRST_COMPLETED,
                        timeout=self.timeout
                    )
                except asyncio.TimeoutError:
                    self._stop = True
                    return
                # maybe called from outside
                for e in pending:
                    e.cancel()
                if self._stop:
                    return
                try:
                    event = done.pop().result()
                except Exception:
                    self._stop = True
                    break
                self.log.debug(f"dispatch event | {self.count}")
                await self.dispatch_event(event)
            await self.stop()
        except Exception:
            self.log.error(traceback.format_exc())
            
    async def dispatch_event(self, event: Event):
        if isinstance(event, InteractionCreateEvent) and self.interaction_pred(event):
            await self.paginate(event)
        await self.listener.notify(event)

    async def paginate(self, event: InteractionCreateEvent):
        if not isinstance(event.interaction, ComponentInteraction):
            return
        id = event.interaction.custom_id or None
        last_position = self._position

        if id == "first":
            self._position = 0
        elif id == "previous":
            if self._position == 0:
                return
            self._position -= 1
        elif id == "stop":
            await event.interaction.create_initial_response(
                ResponseType.MESSAGE_UPDATE
            )
            await self.delete_presence()
            await self.stop()
        elif id == "next":
            if self._position == (len(self.pages)-1):
                return
            self._position += 1
        elif id == "last":
            self._position = len(self.pages)-1
        elif id == "search":
            await event.interaction.create_initial_response(
                ResponseType.DEFERRED_MESSAGE_UPDATE
            )
            await self.search()
            return

        if last_position != self._position:
            await self._update_position(interaction=event.interaction)

    async def delete_presence(self):
        """Deletes this message, and invokation message, if invocation was in a guild"""
        if (channel := self.ctx.get_channel()):
            if isinstance(channel, int):
                channel = self.bot.cache.get_guild_channel(channel)
            await channel.delete_messages(
                [self._message]
            )

    async def _update_position(self, interaction: ComponentInteraction):
        await self.send(content=self.pages[self._position], interaction=interaction)
        
    async def search(self):
        bot_message = await self.ctx.respond("What do you want to search ?")
        try:
            message = await self.bot.wait_for(
                MessageCreateEvent,
                90,
                lambda e: e.author_id == self.ctx.author.id and e.channel_id == self.ctx.channel_id
            )
            query = str(message.content)
        except:
            return
        if isinstance(self.pages[0], hikari.Embed):
            site = self._search_embed(query)
        else:
            site = self._search_str(query)
        if site == -1:
            await self._message.respond(f"Nothing with `{query}` found")
            return
        await self.bot.rest.delete_messages(self.ctx.channel_id, [message.message_id, (await bot_message.message()).id])
        self._position = site
        await self.send(content=self.pages[self._position])
            
    def _search_embed(self, query: str) -> int:
        for i, e in enumerate(self.pages):
            if query in str(e.title) or query in str(e.description):
                return i
            for field in e.fields:
                if query in str(field.name) or query in str(field.value):
                    return i
        return -1
    
    def _search_str(self, query: str) -> int:
        for i, s in enumerate(self.pages):
            if query in str(s):
                return i
        return -1
            
            

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
        disable_when_index_is: Callable[[Optional[int]], bool] = (lambda x: False),
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


