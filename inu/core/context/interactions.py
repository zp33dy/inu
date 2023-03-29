import asyncio
from typing import *
from datetime import datetime, timedelta
import abc
import functools

import hikari
from hikari import ComponentInteraction, ResponseType
from .._logging import getLogger
import lightbulb
from lightbulb.context.base import Context, ResponseProxy

from . import InuContext, InuContextProtocol, InuContextBase, UniqueContextInstance

log = getLogger(__name__)

T = TypeVar("T")
REST_SENDING_MARGIN = 0.6 #seconds
i = 0


class _InteractionContext(Context, InuContext, InuContextProtocol, InuContextBase):
    __slots__ = ("_event", "_interaction", "_default_ephemeral", "_defer_in_progress_event", "log")

    def __init__(
        self, app: lightbulb.app.BotApp, event: hikari.InteractionCreateEvent
    ) -> None:
        super().__init__(app)
        self._event = event
        self._interaction: hikari.ComponentInteraction = event.interaction
        self._default_ephemeral: bool = False
        self._defer_in_progress_event: asyncio.Event = asyncio.Event()
        self._defer_in_progress_event.set()
        global i
        i += 1
        try:    
            self.log = getLogger(__name__, self.__class__.__name__, f"[{self.interaction.id}][{i}]")
        except AttributeError:
            self.log = getLogger(__name__, self.__class__.__name__, f"[{i}]")
        self = UniqueContextInstance.get(self)
        
    @property
    def id(self) -> int:
        return self.event.interaction.id

    @property
    def app(self) -> lightbulb.app.BotApp:
        return self._app

    @property
    def original_message(self) -> hikari.Message:
        return self.event.interaction.message
    
    async def message(self):
        return self.interaction.message

    @property
    def event(self) -> hikari.InteractionCreateEvent:
        return self._event

    @property
    def interaction(self) -> hikari.ComponentInteraction:  #type: ignore
        return self._interaction

    @property
    def channel_id(self) -> hikari.Snowflakeish:
        return self._interaction.channel_id

    @property
    def guild_id(self) -> Optional[hikari.Snowflakeish]:
        return self._interaction.guild_id

    @property
    def attachments(self) -> Sequence[hikari.Attachment]:
        return []

    @property
    def member(self) -> Optional[hikari.Member]:
        return self._interaction.member

    @property
    def author(self) -> hikari.User:
        return self._interaction.user

    def get_channel(self) -> Optional[Union[hikari.GuildChannel, hikari.Snowflake]]:
        if self.guild_id is not None:
            return self.app.cache.get_guild_channel(self.channel_id)
        return self.app.cache.get_dm_channel_id(self.user)

    @classmethod
    def from_context(cls: Context, ctx: Context) -> "_InteractionContext":
        new_ctx = cls(
            event=ctx.event,
            app=ctx.app,
        )
        new_ctx._responses = ctx._responses
        new_ctx._responded = ctx._responded
        return new_ctx

    @classmethod
    def from_event(cls, event: hikari.InteractionCreateEvent):
        return cls(app=event.app, event=event)
    
    async def respond(
        
        self, 
        *args: Any, 
        delete_after: Union[int, float, None] = None, 
        update: bool = False, 
        ephemeral: bool = False, 
        **kwargs: Any
    ) -> ResponseProxy:
        """
        Create a response for this context. The first time this method is called, the initial
        interaction response will be created by calling
        :obj:`~hikari.interactions.command_interactions.CommandInteraction.create_initial_response` with the response
        type set to :obj:`~hikari.interactions.base_interactions.ResponseType.MESSAGE_CREATE` if not otherwise
        specified.

        Subsequent calls will instead create followup responses to the interaction by calling
        :obj:`~hikari.interactions.command_interactions.CommandInteraction.execute`.

        Args:
            *args (Any): Positional arguments passed to ``CommandInteraction.create_initial_response`` or
                ``CommandInteraction.execute``.
            delete_after (Union[:obj:`int`, :obj:`float`, ``None``]): The number of seconds to wait before deleting this response.
            **kwargs: Keyword arguments passed to ``CommandInteraction.create_initial_response`` or
                ``CommandInteraction.execute``.

        Returns:
            :obj:`~ResponseProxy`: Proxy wrapping the response of the ``respond`` call.

        .. versionadded:: 2.2.0
            ``delete_after`` kwarg.
        """
        self.log.debug("IN RESPOND")
        async def _cleanup(timeout: Union[int, float], proxy_: ResponseProxy) -> None:
            await asyncio.sleep(timeout)

            try:
                await proxy_.delete()
            except hikari.NotFoundError:
                pass

        if ephemeral:
            # add ephemeral flag
            kwargs["flags"] = hikari.MessageFlag.EPHEMERAL

        includes_ephemeral: Callable[[Union[hikari.MessageFlag, int],], bool] = (
            lambda flags: (hikari.MessageFlag.EPHEMERAL & flags) == hikari.MessageFlag.EPHEMERAL
        )

        kwargs.pop("reply", None)
        kwargs.pop("mentions_reply", None)
        kwargs.pop("nonce", None)

        # if self._default_ephemeral:
        #     kwargs.setdefault("flags", hikari.MessageFlag.EPHEMERAL)

        if self._responded:
            # followup response
            kwargs.pop("response_type", None)
            if args and isinstance(args[0], hikari.ResponseType):
                args = args[1:]

            async def _ephemeral_followup_editor(
                _: ResponseProxy,
                *args_: Any,
                _wh_id: hikari.Snowflake,
                _tkn: str,
                _m_id: hikari.Snowflake,
                **kwargs_: Any,
            ) -> hikari.Message:
                return await self.app.rest.edit_webhook_message(_wh_id, _tkn, _m_id, *args_, **kwargs_)
            if update:
                proxy = self._responses[-1]
                message = await proxy.edit(*args, **kwargs)
            else:
                log.debug(f"{args=};{kwargs=}")
                message = await self._interaction.execute(*args, **kwargs)
            proxy = ResponseProxy(
                message,
                editor=functools.partial(
                    _ephemeral_followup_editor,
                    _wh_id=self._interaction.webhook_id,
                    _tkn=self._interaction.token,
                    _m_id=message.id,
                ),
                deleteable=not includes_ephemeral(kwargs.get("flags", hikari.MessageFlag.NONE)),
            )
            self._responses.append(proxy)
            self._deferred = False

            if delete_after is not None:
                self.app.create_task(_cleanup(delete_after, proxy))

            return self._responses[-1]

        if args:
            if not isinstance(args[0], hikari.ResponseType):
                kwargs["content"] = args[0]
                kwargs.setdefault("response_type", hikari.ResponseType.MESSAGE_CREATE)
            else:
                kwargs["response_type"] = args[0]
                if len(args) > 1:
                    kwargs.setdefault("content", args[1])
            
        if update:
            kwargs["response_type"] = hikari.ResponseType.MESSAGE_UPDATE
        kwargs.setdefault("response_type", hikari.ResponseType.MESSAGE_CREATE)
        self.log.debug(kwargs)
        self._responded = True
        await self._interaction.create_initial_response(**kwargs)

        # Initial responses are special and need their own edit method defined
        # so that they work as expected for when the responses are ephemeral
        async def _editor(
            rp: ResponseProxy, *args_: Any, inter: hikari.CommandInteraction, **kwargs_: Any
        ) -> hikari.Message:
            await inter.edit_initial_response(*args_, **kwargs_)
            return await rp.message()

        proxy = ResponseProxy(
            fetcher=self._interaction.fetch_initial_response,
            editor=functools.partial(_editor, inter=self._interaction)
            if includes_ephemeral(kwargs.get("flags", hikari.MessageFlag.NONE))
            else None,
        )
        self._responses.append(proxy)
        self._responded = True

        if kwargs["response_type"] in (
            hikari.ResponseType.DEFERRED_MESSAGE_CREATE,
            hikari.ResponseType.DEFERRED_MESSAGE_UPDATE,
        ):
            self._deferred = True

        if delete_after is not None:
            self.app.create_task(_cleanup(delete_after, proxy))

        return self._responses[-1]
    
    async def delete_initial_response(self, after: int | None = None):
        """
        deletes the initial response
        
        Args:
        -----
        after : int
            wait <after> seconds until deleting
        """
        if after:
            await asyncio.sleep(after)
        if self.is_valid:
            return await self.i.delete_initial_response()
        else:
            self.bot.rest.delete_message(self.interaction.message.id)


class InteractionContext(_InteractionContext):
    """
    A wrapper for `hikari.ComponentInteraction`
    """
    def __init__(
        self, 
        event: hikari.InteractionCreateEvent,
        app: lightbulb.app.BotApp,
        ephemeral: bool = False,
        defer: bool = False,
        auto_defer: bool = False,
        update: bool = False,
    ):
        super().__init__(event=event, app=app)
        self._interaction = event.interaction
        self._responded = False
        self._default_ephemeral = ephemeral
        self._deferred: bool = defer
        self._parent_message: hikari.Message | None = None
        self._auto_defer: bool = auto_defer
        self.d: Dict[Any, Any] = {}
        self._update = update
        # this is the last sended message and not the same as self.message
        self._message: hikari.Message | None = None
        

        if defer:
            asyncio.create_task(self._ack_interaction())
        if auto_defer:
            self.auto_defer()
    def set(
        self,
        **kwargs,
    ):
        """
        kwargs:
        ----
        deferred : bool
            set `self._deferred`
        """
        if deferred := kwargs.get("deferred"):
            self._deferred = deferred
        if responded := kwargs.get("responded"):
            self._responded = responded

    def auto_defer(self) -> None:
        """
        Waits the about 3 seconds - REST_SENDING_MARGIN and acks then the
        interaction.

        Note:
        -----
        this runs as task in the background
        """
        asyncio.create_task(self._defer_on_timelimit())

    async def defer(self, background: bool = False) -> None:
        """
        Acknowledges the interaction.
        acknowledge with DEFFERED_MESSAGE_UPDATE if self._update is True,
        otherwise acknowledge with DEFFERED_MESSAGE_CREATE

        Args:
        -----
        background : `bool` = True
            wether or not to defer it as background task
        Note:
        -----
        A task will be started, so it runs in background and returns instantly.
        `self.respond` will wait until defer is finished
        """
        if not self._deferred and not self._responded:
            self.log.debug(f"defer interaction {background=}")
            self._deferred = True
            if background:
                self._defer_in_progress_event.clear()
                asyncio.create_task(self._ack_interaction())
            else:
                await self._ack_interaction()
        else:
            self.log.debug("seems to be deferred already - don't defer")

    async def _maybe_wait_defer_complete(self):
        """wait until defer is done, or return instantly"""
        self.log.debug(f"flag status:{self._defer_in_progress_event.is_set()}")
        await self._defer_in_progress_event.wait()
        # self._defer_in_progress_event.clear()
        # else:
        #     self.log.debug("No defer in progress")

    async def _maybe_defer(self) -> None:
        if self._auto_defer:
            await self.respond(hikari.ResponseType.DEFERRED_MESSAGE_CREATE)

    async def _defer_on_timelimit(self):
        """
        Waits the about 3 seconds - REST_SENDING_MARGIN and acks then the
        interaction.
        """
        respond_at = self.i.created_at + timedelta(seconds=(3 - REST_SENDING_MARGIN))  
        respond_at = respond_at.replace(tzinfo=None)
        self.log.debug(f"maybe defer in {(respond_at - datetime.utcnow()).total_seconds()}")
        await asyncio.sleep(
            (respond_at - datetime.utcnow()).total_seconds()
        )
        if not self._responded:
            
            self._deferred = True
            self.log.debug(f"defer interaction")
            await self._ack_interaction()
            
            
    async def fetch_parent_message(self):
        self.i.delete
        if not self._parent_message:
            self._parent_message = await self.i.fetch_parent_message()

    async def _ack_interaction(self):
        """
        Acknowledges the interaction with deferred update or deferred create,
        if not already done
        """
    
        self._deferred = True
        self._defer_in_progress_event.clear()
        self.log.debug(f"cleared event - set to: {self._defer_in_progress_event.is_set()}")
        if self._update:
            await self.i.create_initial_response(ResponseType.DEFERRED_MESSAGE_UPDATE)
        else:
            await self.i.create_initial_response(ResponseType.DEFERRED_MESSAGE_CREATE)
        
        self._defer_in_progress_event.set()
        self._responded = True
        self.log.debug(f"{self.__class__.__name__} ack for deferred {'update' if self._update else 'create'} done")

    @property
    def i(self) -> hikari.ComponentInteraction:
        return self._interaction

    @property
    def author(self) -> hikari.User:
        return self.interaction.user


    async def delete_webhook_message(self, message: int | hikari.Message, after: int | None = None):
        """
        delete a webhook message

        Args:
        ----
        message : int
            the message to delete. Needs to be created by this interaction
        after : int
            wait <after> seconds, until deleting
        """
        if after:
            await asyncio.sleep(after)
        return await self.i.delete_message(message)
    
    async def execute(self, delete_after: int | None = None, **kwargs) -> hikari.Message:
        """
        execute the webhook and create a message with it

        Args:
        -----
        delete_after : int
            <delete_after> seconds
        **kwargs : Any
            args for the message to create

        Returns:
        --------
        hikari.Message :
            the message object of the created message
        """
        if not self._responded:
            # make inital response instead
            await self.respond(**kwargs)
            if delete_after:
                # start delete timeer
                asyncio.create_task(self.delete_initial_response(after=delete_after))
            # if ensure_return:
            #     # ensure, that a message and not None is returned
            return await self.i.fetch_initial_response()
        else:
            # initial response was made -> actually execute the webhook
            msg = await self.i.execute(**kwargs)
            if delete_after:
                # start delete timer
                asyncio.create_task(self.delete_webhook_message(msg, after=delete_after))
            return msg

    @property
    def custom_id(self) -> str:
        """the custom_id of the current interaction"""
        return self.interaction.custom_id

    @property
    def values(self) -> Sequence[str]:
        """the values of the current interaction"""
        return self.interaction.values

    @property
    def created_at(self) -> datetime:
        """the datetime when the interaction was created"""
        return self.interaction.created_at.replace(tzinfo=None)

    @property
    def is_valid(self) -> bool:
        """wether or not the interaction is valid (timerange of 15 minutes)"""
        return datetime.now() < (self.created_at + timedelta(minutes=14.8))

    @property
    def command(self) -> None:
        return None
    
    @property
    def prefix(self) -> None:  # type: ignore
        return None

    @property
    def invoked_with(self) -> None:  #type: ignore
        return None

    async def initial_response_create(self, **kwargs) -> hikari.Message:
        """Create initial response initially or deffered"""
        self._responded = True
        message = self.interaction.message
        if self._deferred:
            message = await self.interaction.edit_initial_response(
                **kwargs
            )
        else:
            await self.interaction.create_initial_response(
                response_type=ResponseType.MESSAGE_CREATE, 
                **kwargs
            )
        # else:

        self._deferred = False
        return message

        #asyncio.create_task(self._cache_initial_response())
    
    async def _cache_initial_response(self) -> None:
        """cache the initial response message and store it in `self._message`"""
        if not self._message:
            try:
                self._message = True  # to not fetch 2x 
                self._message = await self.i.fetch_initial_response()
            except hikari.NotFoundError:
                return
            self.log.debug(f"{self.__class__.__name__} cached message with id: {self._message.id}")

    async def fetch_response(self) -> hikari.Message:
        """message from initial response or the last execute"""
        if not self._message:
            await self._cache_initial_response()
        return self._message

    async def edit_inital_response(self, **kwargs) -> hikari.Message:
        """update the initial response"""
        self._responded = True
        if not self._deferred:
            await self.i.create_initial_response(
                response_type=ResponseType.MESSAGE_UPDATE, 
                **kwargs
            )
            return self.interaction.message
        else:
            return await self.i.edit_initial_response(
                **kwargs
            )
        
        #asyncio.create_task(self._cache_initial_response())

    async def respond(self, *args, update: bool = False, **kwargs) -> ResponseProxy:
        """
        creates a message with the interaction or REST

        - creates initial response of it wasn't made
        - executes the webhook if initial response was made
        - uses REST to create the message, if the webhook 
        
        """
        self.log.debug(f"{self.is_valid=}, {self._deferred=}, {self._update=}")
        await self._maybe_wait_defer_complete()

        if not kwargs.get("content") and len(args) > 0 and isinstance(args[0], str):  
            # maybe move content from arg to kwarg
            kwargs["content"] = args[0]
            args = args[1:]
        
        if self.is_valid and self._deferred:  
            # interaction deferred
            message: hikari.Message

            if update:
                self.log.debug("deferred message update")
                message = await self.edit_inital_response(**kwargs)
            else:
                self.log.debug("deferred message create")
                message = await self.initial_response_create(**kwargs)

            async def _editor(
                rp: ResponseProxy, *args_: Any, inter: hikari.CommandInteraction, **kwargs_: Any
            ) -> hikari.Message:
                """editor for initial responses"""
                await inter.edit_initial_response(*args_, **kwargs_)
                return await rp.message()

            includes_ephemeral: Callable[[Union[hikari.MessageFlag, int],], bool] = (
                lambda flags: (hikari.MessageFlag.EPHEMERAL & flags) == hikari.MessageFlag.EPHEMERAL
            )

            proxy = ResponseProxy(
                message=message,
                fetcher=self._interaction.fetch_initial_response,
                editor=functools.partial(_editor, inter=self._interaction)
                if includes_ephemeral(kwargs.get("flags", hikari.MessageFlag.NONE))
                else None,
            )
            self.responses.append(proxy)
            return proxy
        
        if not self.is_valid:
            # interaction is unvalid
            message = await (self.last_response).message()
            if update:
                if not message:
                    raise RuntimeError("Interaction run out of time. no message to edit")
                self.log.debug("edit response with rest")
                self._message = await self.app.rest.edit_message(self.channel_id, message.id, **kwargs)
            else:
                self.log.debug("create response with rest")
                self._message = await self.app.rest.create_message(self.channel_id, **kwargs)
            proxy = ResponseProxy(
                self._message,
            )
            self.responses.append(proxy)
            return proxy

        # interaction is valid and not deferred
        self.log.debug("call respond")
        ret_val = await super().respond(*args, update=update, **kwargs)
        # first response was created
        # if old_responded == False and self._responded == True:
            #asyncio.create_task(self._cache_initial_response())
        return ret_val

    respond_with_modal = lightbulb.context.ApplicationContext.respond_with_modal

class CommandInteractionContext(InteractionContext):
    def __init__(self, **kwargs):
        self._initial_response: hikari.Message | None = None
        super().__init__(**kwargs)
        

    async def initial_response_create(self, **kwargs) -> hikari.Message:
        """Create initial response initially or deffered"""
        self._responded = True
        message: hikari.Message

        if self._deferred:
            message = await self.interaction.edit_initial_response(
                **kwargs
            )
        else:
            await self.interaction.create_initial_response(
                response_type=ResponseType.MESSAGE_CREATE, 
                **kwargs
            )
            message = await self.interaction.fetch_initial_response()

        self._initial_response = message
        self._deferred = False
        return message


    async def edit_inital_response(self, **kwargs) -> hikari.Message:
        """update the initial response"""
        hikari.CommandInteraction
        self._responded = True
        message: hikari.Message

        if not self._deferred:
            await self.i.create_initial_response(
                response_type=ResponseType.MESSAGE_UPDATE, 
                **kwargs
            )
            message =  await self.interaction.fetch_initial_response()
        else:
            message = await self.i.edit_initial_response(
                **kwargs
            )
        self._initial_response = message
        return message
    
    async def delete_initial_response(self, after: int | None = None):
        """
        deletes the initial response
        
        Args:
        -----
        after : int
            wait <after> seconds until deleting
        """
        if after:
            await asyncio.sleep(after)
        if self.is_valid:
            return await self.i.delete_initial_response()
        else:
            self.bot.rest.delete_message(self._initial_response.id)
    
    @property
    def interaction(self) -> hikari.CommandInteraction:
        return self._event.interaction
    

    async def message(self) -> hikari.Message:
        if not self._initial_response:
            self._initial_response = await self.interaction.fetch_initial_response()
        return self._initial_response


class MessageInteractionContext(InteractionContext):
    ...

class ModalInteractionContext(InteractionContext):
    ...
        

            


InteractionContext.execute.__doc__ = hikari.ComponentInteraction.execute.__doc__

    