from typing import *

import hikari


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

def guild_name_or_id(guild_id: int, bot: hikari.CacheAware) -> str:
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

