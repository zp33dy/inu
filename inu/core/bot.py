import asyncio
import datetime
import os
import traceback
import typing
from typing import (
    Any,
    List,
    Mapping,
    Union,
    Optional
)
import logging


import lightbulb
from lightbulb import context, commands
import hikari
from hikari.snowflakes import Snowflakeish
from dotenv import dotenv_values
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .logging import LoggingHandler
import lavasnek_rs


class Inu(lightbulb.BotApp):
    def __init__(self, *args, **kwargs):
        logging.setLoggerClass(LoggingHandler)
        self.conf: Configuration = Configuration(dotenv_values())
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)
        self._me: Optional[hikari.User] = None
        self.startup = datetime.datetime.now()
        from utils.db import Database
        self.db = Database(self)
        self.data = Data()
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()

        super().__init__(
            *args, 
            prefix=[self.conf.DEFAULT_PREFIX, ""], 
            token=self.conf.DISCORD_TOKEN, 
            **kwargs,
            case_insensitive_prefix_commands=True,

        )
        logging.setLoggerClass(LoggingHandler)
        self.mrest: MaybeRest = MaybeRest(self)
        self.load("inu/ext/commands/")
        self.load("inu/ext/tasks/")

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if not (loop := asyncio.get_running_loop()):
            raise RuntimeError("Eventloop could not be returned")
        return loop

    @property
    def me(self) -> hikari.User:
        if self._me:
            return self._me
        if not (user := self.cache.get_me()):
            raise RuntimeError("Own user can't be accessed from cache")
        return user

    @property
    def user(self) -> hikari.User:
        return self.me

    def load_slash(self):
        for extension in os.listdir(os.path.join(os.getcwd(), "inu/ext/slash")):
            if extension == "__init__.py" or not extension.endswith(".py"):
                continue
            try:
                self.load_extensions(f"ext.slash.{extension[:-3]}")
            except Exception as e:
                self.log.critical(f"slash command {extension} can't load", exc_info=True)

    def load(self, folder_path: str):
        for extension in os.listdir(os.path.join(os.getcwd(), folder_path)):
            if (
                extension == "__init__.py" 
                or not extension.endswith(".py")
                or extension.startswith("_")
            ):
                continue
            try:
                self.load_extensions(f"{folder_path.replace('/', '.')[4:]}{extension[:-3]}")
                self.log.debug(f"loaded plugin: {extension}")
            except Exception:
                self.log.critical(f"can't load {extension}\n{traceback.format_exc()}", exc_info=True)

    def load_task(self):
        for extension in os.listdir(os.path.join(os.getcwd(), "inu/ext/tasks")):
            if (
                extension == "__init__.py" 
                or not extension.endswith(".py")
                or extension.startswith("_")
            ):
                continue
            try:
                self.load_extensions(f"ext.tasks.{extension[:-3]}")
                self.log.debug(f"loaded plugin: {extension}")
            except Exception as e:
                self.log.critical(f"can't load {extension}\n{traceback.format_exc()}", exc_info=True)

    async def init_db(self):
        await self.db.connect()

    #override
    def run(self):
        super().run()

class Data:
    """Global data shared across the entire bot, used to store dashboard values."""

    def __init__(self) -> None:
        self.lavalink: lavasnek_rs.Lavalink = None  # type: ignore

class Configuration():
    """Wrapper for the config file"""
    def __init__(self, config: Mapping[str, Union[str, None]]):
        self.config = config

    def __getattr__(self, name: str) -> str:
        result = self.config[name]
        if result == None:
            raise AttributeError(f"`Configuration` (.env in root dir) has no attribute `{name}`")
        return result


class MaybeRest:
    def __init__(self, bot: lightbulb.BotApp):
        self.bot = bot

    async def fetch_T(self, cache_method: "function", rest_coro: Any , t_ids: List[Snowflakeish]):
        t = cache_method(*t_ids)
        if t:
            return t
        return await rest_coro(*t_ids)

    async def fetch_user(self, user_id) -> Optional[hikari.User]:
        return await self.fetch_T(
            cache_method=self.bot.cache.get_user,
            rest_coro= self.bot.rest.fetch_user,
            t_ids=[user_id],
        )

    async def fetch_member(self, member_id) -> Optional[hikari.Member]:
        return await self.fetch_T(
            cache_method=self.bot.cache.get_member,
            rest_coro= self.bot.rest.fetch_member,
            t_ids=[member_id],
        )