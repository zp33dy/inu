import typing
from typing import (
    Union,
    Optional,
    List,
)
import asyncio
import logging
from datetime import datetime

from hikari import ActionRowComponent, Embed, MessageCreateEvent, embeds
from hikari.messages import ButtonStyle
from hikari.impl.special_endpoints import ActionRowBuilder, LinkButtonBuilder
from hikari.events import InteractionCreateEvent
import lightbulb
import lightbulb.utils as lightbulb_utils
from lightbulb import commands, context
from lightbulb import OptionModifier as OM
from lightbulb.context import Context
import hikari
from matplotlib.style import available
from numpy import full, isin
from fuzzywuzzy import fuzz

from utils import Colors, Human, Paginator, crumble
from core import getLogger, Inu

log = getLogger(__name__)

plugin = lightbulb.Plugin("Voice commands")

@plugin.command
@lightbulb.add_checks(
    lightbulb.has_role_permissions(hikari.Permissions.MOVE_MEMBERS),
    lightbulb.bot_has_role_permissions(hikari.Permissions.MOVE_MEMBERS),
    lightbulb.guild_only,
)
@lightbulb.option(
    "voice_channel", 
    "the voice channel where you want to move to",
    modifier=OM.CONSUME_REST
)
@lightbulb.option(
    "member", 
    "a person who is in the current voice channel", 
    type=hikari.Member,
)
@lightbulb.command(
    "move-all", 
    "moves all members from a current voice channel into another", 
    aliases=["move"]
)
@lightbulb.implements(commands.SlashCommand, commands.PrefixCommand)
async def move_all(ctx: Context):
    assert(isinstance(ctx.guild_id, int))
    member = ctx.options.member or ctx.author
    states = ctx.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == member.id)]

    if not voice_state:
        await ctx.respond(f"{member.display_name} needs to be in a voice channel")
        return None

    channel_id = voice_state[0].channel_id
    user_ids = [state.user_id async for state in states.iterator().filter(lambda i: i.channel_id == channel_id)]
    channels = await ctx.bot.rest.fetch_guild_channels(ctx.guild_id)
    try:
        target_channel = [
            ch for ch in channels 
            if isinstance(ch, hikari.GuildVoiceChannel) 
            and ch.name == ctx.options.voice_channel.strip()
        ][0]
    except IndexError:
        return await ctx.respond(f"No channel with the name `{ctx.options.voice_channel.strip()}`")
    tasks = [
        asyncio.create_task(
            ctx.bot.rest.edit_member(
                guild=ctx.guild_id, 
                user=user_id, 
                voice_channel=target_channel.id
            )
        )
        for user_id in user_ids
    ]
    asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
    await ctx.respond(
        f"Moved {Human.list_([f'<@{user_id}>' for user_id in user_ids], with_a_or_an=False)} to `{target_channel.name}`"
    )


def load(bot: Inu):
    bot.add_plugin(plugin)
    