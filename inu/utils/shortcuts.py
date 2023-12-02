from typing import *
from datetime import datetime, timedelta
import hikari
from hikari.impl import MessageActionRowBuilder
import aiohttp

from core import Inu

# Pictures
MAGIC_ERROR_MONSTER = "https://media.discordapp.net/attachments/818871393369718824/1106177322069012542/error-monster-1.png?width=1308&height=946"

bot: Inu

def set_bot(bot_: Inu):
    global bot
    bot = bot_


def make_message_link(
    guild_id: int,
    channel_id: int,
    message_id: int,
):
    return f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"


def get_guild_or_channel_id(interaction: hikari.ComponentInteraction) -> int:
    """
    Returns the guild_id if not None, otherwise the (DM) channel_id 
    """
    return interaction.guild_id or interaction.channel_id

def guild_name_or_id(guild_id: int, *args, **kwargs) -> str:
    """
    returns the name of the guild_id if in cache, otherwise the ID as string

    Args:
    -----
    guild_id : int
        the id of the guild
    bot : hikari.CacheAware
        A cache aware bot, to check if guild is in cache
    """
    guild = bot.cache.get_guild(guild_id)
    return guild.name if guild else str(guild_id)


def ts_round(delta: timedelta, round_to: timedelta) -> timedelta:
    total_seconds = delta.total_seconds()
    rounded_seconds = round(total_seconds / round_to.total_seconds()) * round_to.total_seconds()
    return timedelta(seconds=rounded_seconds)



async def check_website(url: str) -> Tuple[int, Optional[str]]:
    """
    Checks if a website is available

    Returns:
    --------
    Tuple[int, Optional[str]]
        the status code and an optional error message
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return response.status, response.reason
    except aiohttp.ClientError as e:
        return 0, str(e)
    
def add_row_when_filled(row: List[MessageActionRowBuilder], position: int = -1, min_empty_slots: int = 1) -> List[MessageActionRowBuilder]:
    """
    Adds a MessageActionRowBuilder to the List if the last one has no free component-slots

    Args:
    -----
    row : List[MessageActionRowBuilder]
        the row inspect
    position : int
        where to insert the new row if possible
    """
    min_empty_slots -= 1
    if not row:
        return [MessageActionRowBuilder()]
    if len(row[-1].components) >= 5 - min_empty_slots:
        if len(row) >= 5:
            raise RuntimeWarning("Can't add more than 5 rows")
        row.insert(MessageActionRowBuilder(), position)
    return row