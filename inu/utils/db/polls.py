from __future__ import annotations
import traceback
from typing import *
import json
import logging
from datetime import timedelta, timezone, datetime
import asyncio
from enum import Enum
import time
import re

import hikari
from hikari.impl import ActionRowBuilder
from hikari.embeds import Embed
import lightbulb
from lightbulb.context import Context
import asyncpg

from core.bot import Inu
from core import Database, Table
from core import getLogger, Table

if TYPE_CHECKING:
    from utils import Poll

log = getLogger(__name__)


# the time in seconds, after the next sql statement, to get further reminders, will be executed
POLL_SYNC_TIME = 5*60

class PollManager:
    bot: Inu
    db: Database
    active_polls: Set[Poll] = set()

    @classmethod
    async def init_bot(cls, bot: Inu):
        cls.bot = bot
        cls.db = bot.db
        loaded_poll_count = 0
        global POLL_SYNC_TIME
        POLL_SYNC_TIME = bot.conf.commands.poll_sync_time
        await cls.delete_old_polls()
        
    @classmethod
    async def delete_old_polls(cls):
        sql = (
            "DELETE FROM polls "
            "WHERE expires < $1"
        )
        table = Table("polls")
        records = await table.fetch(sql, datetime.now())
        log.info(f"Deleted {len(records)} old polls")
        

    @classmethod
    def get_poll(cls, message_id: int, channel_id: int) -> Optional[Poll]:
        for poll in cls.active_polls:
            if poll.message_id == message_id and poll.channel_id == channel_id:
                return poll
        return None

    # poll_id SERIAL PRIMARY KEY,
    # guild_id BIGINT NOT NULL,
    # message_id BIGINT NOT NULL,
    # channel_id BIGINT NOT NULL,
    # creator_id BIGINT NOT NULL,
    # title VARCHAR(255),
    # "description" VARCHAR(2048),
    # starts TIMESTAMP,
    # expires TIMESTAMP NOT NULL,
    # "anonymous" BOOLEAN NOT NULL,
    # "type" INTEGER NOT NULL
    
    @classmethod
    async def add_poll(
        cls,
        guild_id: int,
        message_id: int,
        channel_id: int,
        creator_id: int,
        title: str,
        description: str,
        poll_type: int,
        starts: Optional[datetime] = None,
        expires: Optional[datetime] = None,
        anonymous: bool = False,
    ) -> Optional[int]:
        """add poll to db. returns poll id"""

        table = Table("polls")
        # return await table.insert(
        #     which_columns=[
        #         "guild_id", "message_id", "channel_id", 
        #         "creator_id", "starts", "title", "description", 
        #         "expires", "type", "anonymous"
        #     ],
        #     values=[
        #         poll.guild_id, poll.message_id, poll.channel_id,
        #         poll.creator_id, poll.starts, poll.title, poll.description,
        #         poll.expires, poll.poll_type, poll.anonymous
        #     ],
        #     returning="poll_id"
        # )
        sql = """
            INSERT INTO polls ( 
                guild_id, message_id, channel_id, creator_id, 
                starts, title, description, expires, type, anonymous 
            )
            VALUES ( $1, $2, $3, $4, $5, $6, $7, $8, $9, $10 )
            RETURNING poll_id
        """
        # return values -> List[Dataset["poll_id"]]
        return (await table.fetch(
            sql, 
            guild_id, message_id, channel_id, 
            creator_id, starts, title, 
            description, expires, 
            poll_type, anonymous
        ))[0]["poll_id"]

    @classmethod
    async def remove_poll(cls, poll: Poll):
        """remove poll from db"""
        table = Table("polls")
        await table.delete(
            columns=["poll_id"],
            matching_values=[poll.id]
        )
        cls.active_polls.remove(poll)

    @classmethod
    async def add_vote(cls, poll_id: int, user_id: int, option_id: str):
        table = Table("poll_votes")
        await table.insert(which_columns=["poll_id", "option_id", "user_id"], values=[poll_id, option_id, user_id])

    @classmethod
    async def remove_vote(cls, poll_id: int, user_id: int, option_id: str):
        table = Table("poll_votes")
        await table.delete(columns=["poll_id", "user_id", "option_id"], matching_values=[poll_id, user_id, option_id])

    @classmethod
    async def add_poll_option(cls, poll_id: int, option_name: str, description: str) -> int:
        table = Table("poll_options")
        return await table.insert(
            which_columns=["poll_id", "name", "description"], 
            values=[poll_id, option_name, description],
            returning="option_id"
        )


    @classmethod
    async def remove_poll_options(cls, option_ids: List[int]):
        table = Table("poll_options")
        await table.delete(columns=["option_id"], matching_values=option_ids)

    @classmethod
    async def register_poll(cls, poll: Poll):
        cls.active_polls.add(poll)
