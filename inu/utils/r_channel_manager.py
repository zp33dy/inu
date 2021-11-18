from typing import (
    Dict,
    Optional,
    List,
    Tuple,
    Union,
    Mapping,
    Any
)
import typing
from copy import deepcopy

import asyncpg
from asyncache import cached
from cachetools import TTLCache, LRUCache
import hikari
from hikari import User, Member
from numpy import column_stack


from .db import Database

class DailyContentChannels:
    db: Database
    
    def __init__(self, key: Optional[str] = None):
        self.key = key

    @classmethod
    def set_db(cls, database: Database):
        cls.db = database

    @classmethod
    async def add_channel(
        cls,
        channel_id: int,
        guild_id: int,
    ):
        """
        Adds the <channel_id> to the channels, where my bot sends frequently content to

        Args:
        -----
            - channel_id: (int) the channel_id
            - guild_id: (int) the id of the guild where the channel is in

        Note:
        -----
            - if the channel_id is already in the list for guild_id, than the channel_id wont be added to it
        
        """
        sql = """
        SELECT * FROM reddit_channels
        WHERE guild_id = $1
        """
        record = await cls.db.row(sql, guild_id)
        if record is None:
            channels = [channel_id]
            sql = """
            INSERT INTO reddit_channels (guild_id, channel_ids)
            VALUES ($1, $2)
            """
        else:
            channels = record["channel_ids"]
            channels.append(guild_id)
            channels = list(set(channels))  # remove duplicates
            sql = """
            UPDATE reddit_channels
            SET channel_ids = $2
            WHERE guild_id = $1
            """
        await cls.db.execute(sql, guild_id, channels)

    @classmethod
    async def remove_channel(
        cls,
        channel_id: int,
        guild_id: int,
    ):
        """
        Removes the <channel_id> from the channels, where my bot sends frequently content to

        Args:
        -----
            - channel_id: (int) the channel_id
            - guild_id: (int) the id of the guild where the channel is in      
        """
        sql = """
        SELECT * FROM reddit_channels
        WHERE guild_id = $1
        """
        record = await cls.db.row(sql, guild_id)
        if record is None:
            return
        else:
            channels = record["channel_ids"]
            try:
                channels.remove(channel_id)
            except ValueError:
                return
            sql = """
            UPDATE reddit_channels
            SET channel_ids = $1
            WHERE guild_id = $2
            """
            await cls.db.execute(sql, channels, guild_id)

    @classmethod
    async def get_channels_from_guild(
        cls,
        guild_id: int,
    ):
        """
        UNFINISHED
        Removes the <channel_id> from the channels, where my bot sends frequently content to

        Args:
        -----
            - channel_id: (int) the channel_id
            - guild_id: (int) the id of the guild where the channel is in      
        """
        sql = """
        SELECT * FROM reddit_channels
        WHERE guild_id = $1
        """
        raise NotImplemented
        record = await cls.db.row(sql, guild_id)

    @classmethod
    async def get_all_channels(cls) -> List[int]:
        """
        Returns:
        --------
            - (List[int]) a list with all channel_ids
        """
        sql = """
        SELECT * FROM reddit_channels
        """
        records = await cls.db.fetch(sql)
        if not records:
            return []
        channel_ids = []
        for r in records:
            channel_ids.extend(r["channel_ids"])
        return channel_ids

class test:
    pass
