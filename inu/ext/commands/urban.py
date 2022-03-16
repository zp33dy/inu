import typing
from typing import (
    Union,
    Optional,
    List,
)
import asyncio
import logging

from hikari import ActionRowComponent, Embed, MessageCreateEvent, embeds
from hikari.messages import ButtonStyle
from hikari.impl.special_endpoints import ActionRowBuilder
from hikari.events import InteractionCreateEvent
import lightbulb
import lightbulb.utils as lightbulb_utils
from lightbulb import commands, context
import hikari
from numpy import isin

from core import getLogger, BotResponseError
from utils import Urban, Paginator
# from utils.logging import LoggingHandler
# logging.setLoggerClass(LoggingHandler)



log = getLogger(__name__)

plugin = lightbulb.Plugin("Urban", "Extends the commands with urban commands")

@plugin.command
@lightbulb.option("word", "What do you want to search?")
@lightbulb.command("urban", "Search a word in the urban (city) dictionary")
@lightbulb.implements(commands.PrefixCommand, commands.SlashCommand)
async def urban_search(ctx: context.Context):
    try:
        pag = Paginator(
            page_s=[
                Embed(
                    title=f"Urban - {ctx.options.word}",
                    description=(
                        f"**description for [{ctx.options.word}]({d['permalink']}):**\n"
                        f"{d['definition'].replace('[', '').replace(']', '')}\n\n"
                        f"**example:**\n"
                        f"{d['example'].replace('[', '').replace(']', '')}\n\n"
                    )
                )
                .set_footer(
                    text=f"{d['thumbs_up']}👍 | {d['thumbs_down']}👎"
                )
                for d in await Urban.fetch(ctx.options.word)
            ]
        )
        await pag.start(ctx)
    except BotResponseError as e:
        await ctx.respond(e.bot_message)



def load(bot: lightbulb.BotApp):
    bot.add_plugin(plugin)

