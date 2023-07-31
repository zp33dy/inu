from typing import *
from abc import ABC, abstractmethod

import hikari
from hikari import TextInputStyle
from lightbulb.context import Context


T = TypeVar("T")

T_STR_LIST = TypeVar("T_STR_LIST", list[str], str)


class InuContext(ABC):
    @abstractmethod
    def from_context(cls: Context, ctx: Context) -> T:
        ...

    @abstractmethod
    def from_event(cls: Context, event: hikari.Event) -> T:
        ...
    
    @property
    @abstractmethod
    def original_message(self) -> hikari.Message:
        ...

    @property
    @abstractmethod
    def bot(self) -> hikari.GatewayBot:
        ...

    @property
    @abstractmethod
    def user(self) -> hikari.User:
        ...

    @property
    @abstractmethod
    def author(self) -> hikari.User:
        ...

    @property
    @abstractmethod
    def channel_id(self) -> int:
        ...

    @abstractmethod
    async def respond(self, *args, **kwargs):
        """
        Create a response for this context. The first time this method is called, the initial
        interaction response will be created by calling
        :obj:`~hikari.interactions.command_interactions.CommandInteraction.create_initial_response` with the response
        type set to :obj:`~hikari.interactions.base_interactions.ResponseType.MESSAGE_CREATE` if not otherwise
        specified.

        Subsequent calls will instead create followup responses to the interaction by calling
        :obj:`~hikari.interactions.command_interactions.CommandInteraction.execute`.

        Args:
            update : bool
                wether or not to update the current interaction message
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
        ...
    @property
    @abstractmethod
    def id(self):
        """used to Compare `InuContext` classes"""
        ...

    @property
    def interaction(self) -> hikari.PartialInteraction | None:
        ...
    
    @abstractmethod
    async def defer(self, background: bool = True):
        """
        Acknowledges the interaction if not rest is used.
        acknowledge with DEFFERED_MESSAGE_UPDATE if self._update is True,
        otherwise acknowledge with DEFFERED_MESSAGE_CREATE

        Args:
        -----
        background : `bool` = True
            wether or not to defer it as background task

        
        Note:
        -----
        A task will be started, so it runs in background and returns instantly
        """
        ...
    
    @abstractmethod
    async def auto_defer(self) -> None:
        """
        Waits the about 3 seconds - REST_SENDING_MARGIN and acks then the
        interaction.

        Note:
        -----
        this runs as task in the background
        """
        ...

    @property
    def is_hashable(self) -> bool:
        """wether or not __hash__ will result in an error"""
        return self.id is not None
    
    
    @abstractmethod
    async def delete_initial_response(self) -> None:
        ...
        
    @abstractmethod
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

    @abstractmethod
    async def ask(
            self, 
            title: str, 
            button_labels: List[str] = ["Yes", "No"], 
            ephemeral: bool = True, 
            timeout: int = 120
    ) -> Tuple[str, "InuContext"]:
        """g
        ask a question with buttons

        Args:
        -----
        title : str
            the title of the message
        button_labels : List[str]
            the labels of the buttons
        ephemeral : bool
            whether or not the message should be ephemeral
        timeout : int
            the timeout in seconds
        
        Returns:
        --------
        Tuple[str, "InteractionContext"]
            the selected label and the new context
        """

    async def ask_with_modal(
            self, 
            title: str, 
            question_s: T_STR_LIST,
            input_style_s: Union[TextInputStyle, List[Union[TextInputStyle, None]]] = TextInputStyle.PARAGRAPH,
            placeholder_s: Optional[Union[str, List[Union[str, None]]]] = None,
            max_length_s: Optional[Union[int, List[Union[int, None]]]] = None,
            min_length_s: Optional[Union[int, List[Union[int, None]]]] = None,
            pre_value_s: Optional[Union[str, List[Union[str, None]]]] = None,
            is_required_s: Optional[Union[bool, List[Union[bool, None]]]] = None,
            timeout: int = 120
    ) -> Tuple[T_STR_LIST, "InuContext"] | None:
        """
        ask a question with buttons

        Args:
        -----
        title : str
            the title of the message
        timeout : int
            the timeout in seconds
        question_s : `Union[List[str], str]`
            The question*s to ask the user
        interaction : `ComponentInteraction`
            The interaction to use for initial response
        placeholder : `str` | `None`
            The placeholder of the input
        max_length : `int` | `None`
            The max length of the input
        min_length : `int` | `None`
            The min length of the input


        Returns:
        --------
        Tuple[str, "InteractionContext"]
            the selected label and the new context
        """
        ...

class InuContextProtocol(Protocol[T]):
    def from_context(cls: Context, ctx: Context) -> T:
        ...
    
    def from_event(cls: Context, event: hikari.Event) -> T:
        ...

    @property
    def original_message(self) -> hikari.Message:
        ...

    @property
    def interaction(self) -> hikari.PartialInteraction | None:
        ...
    
    async def defer(self, background: bool = True):
        """
        Acknowledges the interaction if not rest is used.
        acknowledge with DEFFERED_MESSAGE_UPDATE if self._update is True,
        otherwise acknowledge with DEFFERED_MESSAGE_CREATE

        Args:
        -----
        background : `bool` = True
            wether or not to defer it as background task

        
        Note:
        -----
        A task will be started, so it runs in background and returns instantly
        """
        ...
    
    async def auto_defer(self) -> None:
        """
        Waits the about 3 seconds - REST_SENDING_MARGIN and acks then the
        interaction.

        Note:
        -----
        this runs as task in the background
        """
        ...
    
    @property
    def bot(self) -> hikari.GatewayBot:
        ...

    @property
    def user(self) -> hikari.User:
        ...

    async def respond(self, *args, **kwargs):
        """
        Create a response for this context. The first time this method is called, the initial
        interaction response will be created by calling
        :obj:`~hikari.interactions.command_interactions.CommandInteraction.create_initial_response` with the response
        type set to :obj:`~hikari.interactions.base_interactions.ResponseType.MESSAGE_CREATE` if not otherwise
        specified.

        Subsequent calls will instead create followup responses to the interaction by calling
        :obj:`~hikari.interactions.command_interactions.CommandInteraction.execute`.

        Args:
            update : bool
                wether or not to update the current interaction message
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
        ...

    @property
    def id(self):
        """used to Compare `InuContext` classes"""
        ...
    

    async def auto_defer(self) -> None:
        """
        Waits the about 3 seconds - REST_SENDING_MARGIN and acks then the
        interaction.

        Note:
        -----
        this runs as task in the background
        """
        ...

    @property
    def is_hashable(self) -> bool:
        """wether or not __hash__ will result in an error"""
        return self.id is not None
    
    
    async def delete_inital_response(self) -> None:
        """deletes the initial response"""
        ...
