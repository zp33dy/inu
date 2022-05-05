import asyncio
import logging
import typing
from datetime import datetime, timedelta
from typing import *
from numpy import full, isin
import random
from io import BytesIO

import aiohttp
import hikari
import lightbulb
import lightbulb.utils as lightbulb_utils
from dataenforce import Dataset

from fuzzywuzzy import fuzz
from hikari import (
    ActionRowComponent, 
    Embed, 
    MessageCreateEvent, 
    embeds, 
    ResponseType, 
    TextInputStyle
)
from hikari.events import InteractionCreateEvent
from hikari.impl.special_endpoints import ActionRowBuilder, LinkButtonBuilder
from hikari.messages import ButtonStyle
from jikanpy import AioJikan
from lightbulb import OptionModifier as OM
from lightbulb import commands, context
from lightbulb.context import Context
import matplotlib
import matplotlib.pyplot as plt
from typing_extensions import Self
import pandas as pd
import seaborn as sn
import mplcyberpunk



from utils import (
    Colors, 
    Human, 
    Paginator, 
    Reddit, 
    Urban, 
    crumble,
    CurrentGamesManager,
)
from core import (
    BotResponseError, 
    Inu, 
    Table, 
    getLogger
)

log = getLogger(__name__)

plugin = lightbulb.Plugin("Statistics", "Shows statistics about the server")
bot: Inu


@plugin.command
@lightbulb.add_checks(lightbulb.checks.guild_only)
@lightbulb.add_cooldown(1, 1, lightbulb.UserBucket)
@lightbulb.option("app", "The application you want stats for")
@lightbulb.command("app", "Shows, which games are played in which guild", auto_defer=True)
@lightbulb.implements(commands.SlashCommand, commands.PrefixCommand)
async def application(ctx: Context):
    # fetch data
    await CurrentGamesManager.fetch_activities_from_guild(ctx.guild_id, datetime.now() - timedelta(days=30))
    data = await CurrentGamesManager.fetch_activity_from_application(
        ctx.guild_id, 
        "League of Legends", 
        datetime.now() - timedelta(days=30),
    )
    log.debug(f"{data=}")
    now = datetime.now()
    fake_data = []
    for i in range(1, 10): #
        fake_data.append(
            [now + timedelta(days=i), random.randint(0, 100), i-1] #
        )
    fake_data_2 = []
    for i in range(1, 40): #
        fake_data_2.append(
            [random.randint(0, 100), i-1] #
        )

    plt.style.use("dark_background")
    picture_in_bytes = BytesIO()
    df = pd.DataFrame(
        fake_data,
        columns=["date", "amount", "count"]
    )
    df2 = pd.DataFrame(
        fake_data_2,
        columns=["amount", "count"]
    )


    log.debug(f"\n{df}")
    # #Create combo chart
    fig, ax1 = plt.subplots(figsize=(20,6))#
    color = 'tab:green'
    # #bar plot creation
    # ax1.set_title('Avg Playtime in Minutes', fontsize=16)
    # ax1.set_xlabel('date', fontsize=16)
    # ax1.set_ylabel('minutes', fontsize=16)
    p1 = sn.barplot(x='date', y='amount', data = df, palette='summer')
    p1.set_xticklabels([f"{d.day}.{d.month}" for d in df["date"]], rotation=45, horizontalalignment='right')
    # # ax1.tick_params(axis='y')
    # #specify we want to share the same x-axis
    ax2 = p1.twinx()
    # color = 'tab:red'
    # #line plot creation
    # #ax2.set_ylabel('Avg playtime', fontsize=16)

    ax2 = sn.lineplot(x='amount', y='amount', data = df2, color=color, ax=ax2)
    # ax2.tick_params(axis='y', color=color)


    # svm = sn.heatmap(df_cm, annot=True,cmap='coolwarm', linecolor='white', linewidths=1)
    figure = fig.get_figure()    
    #matplotlib.pyplot.show() 
    figure.savefig(picture_in_bytes, dpi=100)
    picture_in_bytes.seek(0)
    await ctx.respond(
        "data",
        attachment=picture_in_bytes
    )


@plugin.command
@lightbulb.add_checks(lightbulb.checks.guild_only)
@lightbulb.add_cooldown(60, 1, lightbulb.UserBucket)
@lightbulb.command("current-games", "Shows, which games are played in which guild", auto_defer=True)
@lightbulb.implements(commands.SlashCommand, commands.PrefixCommand)
async def current_games(ctx: Context):
    # constants

    coding_apps = ["Visual Studio Code", "Visual Studio", "Sublime Text", "Atom", "VSCode"]
    music_apps = ["Spotify", "Google Play Music", "Apple Music", "iTunes", "YouTube Music"]
    double_games = ["Rainbow Six Siege", "PUBG: BATTLEGROUNDS"]  # these will be removed from games too
    max_ranking_num: int = 20

    async def build_embeds() -> List[Embed]:
        bot: Inu = plugin.bot
        embeds: List[hikari.Embed] = []
        # build embed for current guild
        guild: hikari.Guild = ctx.get_guild()  # type: ignore
        activity_records = await CurrentGamesManager.fetch_games(
            guild.id, 
            datetime.now() - timedelta(days=30)
        )
        activity_records.sort(key=lambda g: g['amount'], reverse=True)

        # get smallest first_occurrence
        first_occurrence = datetime.now()
        for record in activity_records:
            if record['first_occurrence'] < first_occurrence:
                first_occurrence = record['first_occurrence']

        embed = (
            hikari.Embed(
                title=f"{guild.name}",
            )
            .set_footer(f"all records I've taken since {first_occurrence.strftime('%d. %B')}")
        )

        field_value = ""
        embeds.append(embed)

        # enuerate all games
        game_records = [g for g in activity_records if g['game'] not in [*coding_apps, *music_apps, *double_games]]
        for i, game in enumerate(game_records):
            if i > 150:
                break
            if i < max_ranking_num:
                field_value += f"{i+1}. {game['game']:<40}{str(timedelta(minutes=int(game['amount']*10)))}\n"
            else:
                field_value += f"{game['game']:<40}{str(timedelta(minutes=int(game['amount']*10)))}\n"
            if i % 10 == 9 and i:
                embeds[-1].description = (
                    f"{f'Top {i+1} games' if i <= max_ranking_num else 'Less played games'}"
                    f"```{field_value[:2000]}```"
                )
                embeds.append(hikari.Embed())
                field_value = ""
        
        # add last remaining games
        if field_value:
            embeds[-1].description = (
                f"Less played games"
                f"```{field_value[:2000]}```"
            )
        else:
            embeds.pop()
        
        # add total played games/time
        embeds[0] = (
            embeds[0]
            .add_field("Total played games", str(len(game_records)), inline=False)
            .add_field("Total gaming time", str(timedelta(minutes=sum(int(game['amount']) for game in game_records)*10)) , inline=True)
        )

        # add total coding time
        coding_time = sum([g["amount"]*10 for g in activity_records if g['game'] in coding_apps])
        if coding_time:
             embeds[0].add_field(
                "Total coding time", 
                str(timedelta(minutes=int(coding_time))), 
                inline=True
            )

        # add total music time
        music_time = sum([g["amount"]*10 for g in activity_records if g['game'] in music_apps])
        if music_time:
            embeds[0].add_field(
                "Total music time", 
                str(timedelta(minutes=int(music_time))), 
                inline=True
            )

        return embeds

    last_month: datetime = datetime.now() - timedelta(days=30)
    picture_buffer, _ = await build_activity_graph(
        ctx.guild_id, 
        since=last_month,
        activities=[
            list(d.keys())[0]
            for d in
            await CurrentGamesManager.fetch_top_games(
                guild_id=ctx.guild_id, 
                since=last_month,
                limit=8,
                remove_activities=[*coding_apps, *music_apps, *double_games]
            )
        ],
    )
    await ctx.respond(attachment=picture_buffer)
    pag = Paginator(
        page_s=await build_embeds(),
        download=picture_buffer,
        download_name="current-games.png",
    )
    await pag.start(ctx)


async def build_activity_graph(
    guild_id: int,
    since: datetime,
    activities: List[str],
) -> Tuple[BytesIO, Dataset]:
    picture_buffer = BytesIO()

    df = await CurrentGamesManager.fetch_activities(
        guild_id=guild_id, 
        since=since,
        activity_filter=activities,
    )

    # optimizing dataframe
    df.set_index(keys="r_timestamp", inplace=True)
    activity_series = df.groupby("game")["hours"].resample("1d").sum()
    df_summarized = activity_series.to_frame().reset_index()

    # style preparations
    color_paletes = ["magma_r", "rocket_r", "mako_r"]
    plt.style.use("cyberpunk")
    sn.set_palette("bright")
    sn.set_context("notebook", font_scale=1.4, rc={"lines.linewidth": 1.5})
    log.debug(f"\n{df_summarized}")
    
    #Create graph
    fig, ax1 = plt.subplots(figsize=(25,8))
    sn.despine(offset=20)
    ax: matplotlib.axes.Axes = sn.lineplot(
        x='r_timestamp', 
        y='hours', 
        data = df_summarized,
        hue="game", 
        legend="full", 
        markers=False,
        palette=random.choice(color_paletes),
    )

    # style graph
    mplcyberpunk.add_glow_effects(ax=ax)
    ax.set_xticklabels([f"{d.day}/{d.month}" for d in df_summarized["r_timestamp"]], rotation=45, horizontalalignment='right')
    ax.set_ylabel("Hours")
    ax.set_xlabel("")

    # save graph
    figure = fig.get_figure()    
    figure.savefig(picture_buffer, dpi=100)
    picture_buffer.seek(0)
    return picture_buffer, df_summarized



def load(inu: lightbulb.BotApp):
    global bot
    bot = inu
    inu.add_plugin(plugin)

