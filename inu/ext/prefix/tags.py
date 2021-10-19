import re
import typing
from typing import (
    Dict,
    Mapping,
    Optional,
    List,
    Union,
    Any

)
import logging
from logging import DEBUG
import asyncio

import hikari
from hikari import ComponentInteraction, Embed, InteractionCreateEvent, ResponseType
from hikari.impl import ActionRowBuilder
from hikari.messages import ButtonStyle
import lightbulb
from lightbulb import Context
from lightbulb.converters import Greedy
import asyncpg

from core import Inu
from utils.tag_mamager import TagIsTakenError, TagManager
from utils import crumble
from utils.colors import Colors
from utils import Paginator
from utils.paginators.common import navigation_row
from utils.paginators import TagHandler

log = logging.getLogger(__name__)
log.setLevel(DEBUG)


class Tags(lightbulb.Plugin):

    def __init__(self, bot: Inu):
        self.bot = bot
        super().__init__(name=self.__class__.__name__)

    @lightbulb.group()
    async def tag(self, ctx: Context, *, key: str = None):
        """Get the tag by `key`
        
        Args:
        ----
            - key: the name of the tag
                - if `key` isn't provided I'll start an interactive tag creation menu
        """
        if key is None:
            taghandler = TagHandler()
            return await taghandler.start(ctx)

        records = await TagManager.get(key, ctx.guild_id or 0)
        record: Optional[Mapping[str, Any]] = None
        # if records are > 1 return the local overridden one
        if len(records) >= 1:
            typing.cast(int, ctx.guild_id)
            for r in records:
                if r["guild_id"] == ctx.guild_id:
                    record = r
                    break
                elif r["guild_id"] is None:
                    record = r
        if record is None:
            return await ctx.respond(f"I can't found a tag named `{key}` in my storage")
        messages = []
        for value in crumble("\n".join(v for v in record["tag_value"])):
            message = f"**{key}**\n\n{value}\n\n`created by {self.bot.cache.get_user(record['creator_id']).username}`"
            messages.append(message)
        pag = Paginator(messages)
        await pag.start(ctx)

    @tag.command()
    async def add(self, ctx: Context, key: str = None, *, value: str = None):
        """Add a tag to my storage
        
        Args:
        -----
            - key: the name the tag should have
            NOTE: the key is the first word you type in! Not more and not less!!!
            - value: that what the tag should return when you type in the name. The value is all after the fist word
        """
        if value is None or key is None:
            taghandler = TagHandler()
            return await taghandler.start(ctx)
        typing.cast(str, value)
        try:
            await TagManager.set(key, value, ctx.member or ctx.author)
        except TagIsTakenError:
            return await ctx.respond("Your tag is already taken")
        return await ctx.respond(f"Your tag `{key}` has been added to my storage")

    @tag.command()
    async def edit(self, ctx: Context, key: str):
        """Add a tag to my storage
        
        Args:
        -----
            - key: the name the tag should have
            NOTE: the key is the first word you type in! Not more and not less!!!
            - value: that what the tag should return when you type in the name. The value is all after the fist word
        """

        raw_results: List[Mapping[str, Any]] = await TagManager.get(key, ctx.guild_id)
        results = []
        for result in raw_results:
            if result["creator_id"] == ctx.author.id:
                results.append(result)
        # case 0: no entry in database
        # case 1: 1 entry in db; check if global or in guild
        # case _: let user select if he wants the global or local one
        if len(results) == 0:
            return await ctx.respond(f"I can't find a tag with the name `{key}` where you are the owner :/")
        elif len(results) == 1:
            taghandler = TagHandler()
            return await taghandler.start(ctx, results[0])
        else:
            #  select between global and local - needs to lookup the results if there are tags of author
            records = {}
            for record in results:
                if record["guild_id"] == ctx.guild_id and record["guild_id"] is None:
                    records["global"] = record
                else:
                    records["local"] = record
            menu = (
                ActionRowBuilder()
                .add_select_menu("menu")
                .add_option(f"{key} - global / everywhere", "global")
                .add_to_menu()
                .add_option(f"{key} - local / guild only", "local")
                .add_to_menu()
                .add_to_container()
            )
            try:
                await ctx.respond("Do you want to edit your local or global tag?", component=menu)
                event = await self.bot.wait_for(
                    InteractionCreateEvent,
                    30,
                )
                if not isinstance(event.interaction, ComponentInteraction):
                    return
                await event.interaction.create_initial_response(ResponseType.DEFERRED_MESSAGE_UPDATE)
                taghandler = TagHandler()
                await taghandler.start(ctx, records[event.interaction.values[0]])

            except asyncio.TimeoutError:
                pass
        # selection menu here
            
        
    @tag.command()
    async def remove(self, ctx: Context, key: str):
        """Remove a tag to my storage
        
        Args:
        -----
            - key: the name of the tag which you want to remove
        """

        raw_results: List[Mapping[str, Any]] = await TagManager.get(key, ctx.guild_id)
        results = []
        for result in raw_results:
            if result["creator_id"] == ctx.author.id:
                results.append(result)
        # case 0: no entry in database
        # case 1: 1 entry in db; check if global or in guild
        # case _: let user select if he wants the global or local one
        if len(results) == 0:
            return await ctx.respond(f"I can't find a tag with the name `{key}` where you are the owner :/")
        elif len(results) == 1:
            taghandler = TagHandler()
            return await taghandler.start(ctx, results[0])
        else:
            #  select between global and local - needs to lookup the results if there are tags of author
            records = {}
            for record in results:
                if record["guild_id"] == ctx.guild_id and record["guild_id"] is None:
                    records["global"] = record
                else:
                    records["local"] = record
            menu = (
                ActionRowBuilder()
                .add_select_menu("menu")
                .add_option(f"{key} - global / everywhere", "global")
                .add_to_menu()
                .add_option(f"{key} - local / guild only", "local")
                .add_to_menu()
                .add_to_container()
            )
            try:
                await ctx.respond("Do you want to edit your local or global tag?", component=menu)
                event = await self.bot.wait_for(
                    InteractionCreateEvent,
                    30,
                )
                if not isinstance(event.interaction, ComponentInteraction):
                    return
                await event.interaction.create_initial_response(ResponseType.DEFERRED_MESSAGE_UPDATE)
                taghandler = TagHandler()
                await taghandler.start(ctx, records[event.interaction.values[0]])

            except asyncio.TimeoutError:
                pass


    async def tag_add_i(self, ctx):
        pass


def load(bot: Inu):
    bot.add_plugin(Tags(bot))
