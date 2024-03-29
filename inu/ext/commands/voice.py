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
from hikari import ButtonStyle
from hikari.impl.special_endpoints import MessageActionRowBuilder, LinkButtonBuilder
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
# @lightbulb.option(
#     "member", 
#     "a person who is in the current voice channel. normally you", 
#     type=hikari.Member,
#     default=None,
# )
@lightbulb.option(
    "from-voice-channel", 
    "the voice channel where move peaple of",
    type=hikari.GuildChannel,
    default=None,
)
@lightbulb.option(
    "voice-channel", 
    "the voice channel where you want to move to",
    type=hikari.GuildChannel,
)
@lightbulb.command(
    "move-all", 
    "moves all members from a current voice channel into another", 
    aliases=["move"]
)
@lightbulb.implements(commands.SlashCommand, commands.PrefixCommand)
async def move_all(ctx: Context):
    target_channel: hikari.InteractionChannel = ctx.options["voice-channel"]
    if not target_channel.type == hikari.ChannelType.GUILD_VOICE:
        await ctx.respond(f"{target_channel} is not a voice channel", flags=hikari.MessageFlag.EPHEMERAL)
        return None

    if not ctx.options["from-voice-channel"]:
        member = ctx.member
        states = ctx.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
        voice_state = [state for state in states.values() if state.user_id == member.id]

        if not voice_state:
            await ctx.respond(f"{member.display_name} needs to be in a voice channel")
            return None

        channel_id = voice_state[0].channel_id
        user_ids = [state.user_id for state in states.values() if state.channel_id == channel_id]
    else:
        user_ids = [
            state.user_id for state in ctx.bot.cache.get_voice_states_view_for_guild(ctx.guild_id).values()
            if state.channel_id == ctx.options["from-voice-channel"].id
        ]
    
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
    await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
    await ctx.respond(
        f"Moved {Human.list_([f'<@{user_id}>' for user_id in user_ids], with_a_or_an=False)} to `{target_channel.name}`"
    )

@move_all.autocomplete("voice-channel")
async def tag_name_auto_complete(
    option: hikari.AutocompleteInteractionOption, 
    interaction: hikari.AutocompleteInteraction
) -> List[str]:
    vcs = []
    guild = interaction.get_guild()
    if not guild:
        return []
    for ch in guild.get_channels().values():
        if not isinstance(ch, hikari.GuildVoiceChannel):
            continue
        if lightbulb_utils.permissions_in(ch, interaction.member) & hikari.Permissions.CONNECT:
            vcs.append(f"{ch.id} | {ch.name}")
    return vcs[:24]


def load(bot: Inu):
    bot.add_plugin(plugin)
    