from argparse import Action
import asyncio
from datetime import datetime, timedelta
from email.message import Message
import random
from time import time
import traceback
from typing import *

import lightbulb
from lightbulb import ResponseProxy, commands
from lightbulb.context import Context
import hikari
from hikari.impl import ActionRowBuilder
from hikari import ButtonStyle, ComponentInteraction, Embed, ResponseType
from core.bot import Inu, getLogger
from utils.language import Human

from utils import (
    NumericStringParser,
    Multiple, 
    Colors, 
    MathScoreManager, 
    Paginator
)

log = getLogger(__name__)

class CalculationBlueprint:
    def __init__(
        self,
        max_number: int,
        operations: int,
        max_time: int,
        min_number: int = 1,
        allowed_endings: List[str] = [".0"],
        allowed_symbols: List[str] = ["*", "/", "+", "-"],
        allowed_partial_endings: List[str] = [".1", ".2", "0.5"],
        name: str = "",
        max_result_number: Optional[int] = None,

        
    ):
        """
        Args:
        -----
            - max_number (int) The maximum number, which will appear in the end string
            - operations (int) How many operations the calculation will have
            - allowed_endings (`List[str]`, Default = `[".0"]`) allowed endings from the result of the end string
            - allowed_symbols (`List[str]`, Default = `["*", "/", "+", "-"]`) all allowed operations for the calc string
            - allowed_partial_endings (`List[float]`, default = `0.1, 0.2, 0.5]`) allowed endings of interm results 
        """
        nsp = NumericStringParser()
        self._operations = operations
        self.calc = nsp.eval
        self._allowed_endings = allowed_endings
        # add space for optic later on
        self._allowed_symbols = [f" {s} " for s in allowed_symbols]
        self._allowed_partial_endings = allowed_partial_endings
        self._max_number = max_number
        self._min_number = min_number
        self._max_time = max_time
        self.name = name
        self._max_result_number = max_result_number

        # when exeeding 2000 raise error
    @staticmethod
    def get_result(to_calc: str):
        to_calc = to_calc.replace("x", "*").replace(":", "/")
        nsp = NumericStringParser()
        return nsp.eval(to_calc)
    
    def get_task(self) -> str:
        try:
            return self.create_calculation_task()
        except RuntimeError:
            return self.get_task()

    def create_calculation_task(self) -> str:
        creation_trys = 0
        calc_str = str(self.get_rnd_number())
        op = self.get_rnd_symbol()
        num = self.get_rnd_number()
        for x in range(self._operations):
            op = self.get_rnd_symbol()
            num = self.get_rnd_number()
            if x != self._operations:
                while not self.is_allowed(f"{calc_str}{op}{num}"):
                    op = self.get_rnd_symbol()
                    num = self.get_rnd_number()
                    creation_trys += 1
                    if creation_trys > 200:
                        raise RuntimeError(f"Creation not possible with string: {calc_str}{op}{num}")
                calc_str = f"{calc_str}{op}{num}"
            else:
                while not self.is_allowed(f"{calc_str}{op}{num}"):
                    op = self.get_rnd_symbol()
                    num = self.get_rnd_number()
                calc_str = f"{calc_str}{op}{num}"
        return calc_str

    def get_rnd_number(self) -> int:
        return random.randrange(self._min_number, self._max_number + 1)

    def get_rnd_symbol(self):
        return random.choice(self._allowed_symbols)

    def is_allowed(self, calc: str, end: bool = False) -> bool:
        try:    
            result = str(self.get_result(calc))
        except Exception:
            log.error(f"Can't calculate: {calc}")
            log.error(traceback.format_exc())
        if self._max_result_number:
            too_big = float(result) >= self._max_result_number
            if too_big:
                return False
        if end:
            return Multiple.endswith_(result, self._allowed_endings)
        else:
            return Multiple.endswith_(result, [*self._allowed_partial_endings, *self._allowed_endings])

    def __str__(self) -> str:
        text = ""
        text += f"**{self._operations} Operations from** \n{', '.join(f'`{s}`' for s in self._allowed_symbols)}.\n"
        text += f"Numbers from `{self._min_number}` to `{self._max_number}`\n"
        text += f"and `{self._max_time}s/Task` time.\n"
        if self._max_result_number:
            text += f"The will be smaller than `{self._max_result_number}`\n"
        text += f"Example: \n`{self.get_task()}`"
        return text


plugin = lightbulb.Plugin("mind_training", "Contains calcualtion commands")

bot: Optional[Inu] = None
stages = {
    "Stage 1": CalculationBlueprint(
        max_number=9,
        operations=1,
        max_time=10,
        allowed_partial_endings=[],
        allowed_endings=[".0"],
        name="Stage 1",
    ),
    "Stage 2": CalculationBlueprint(
        max_number=9,
        operations=2,
        max_time=20,
        allowed_partial_endings=[],
        allowed_endings=[".0"],
        name="Stage 2",
    ),
    "Stage 3": CalculationBlueprint(
        max_number=15,
        operations=2,
        max_time=25,
        allowed_partial_endings=["0.5"],
        allowed_endings=[".0"],
        name="Stage 3",
        max_result_number=500,
    ),
    "Stage Artur": CalculationBlueprint(
        max_number=1,
        operations=1,
        max_time=99,
        allowed_symbols=["+"],
        allowed_partial_endings=[],
        allowed_endings=[".0"],
        name="Stage Artur",
    ),

}
running_games = {}

@plugin.command
@lightbulb.command("math", "Menu with all calculation tasks I have")
@lightbulb.implements(commands.PrefixCommand)
async def calculation_tasks(ctx: Context):
    embed = Embed(title="Calculation tasks")
    menu = ActionRowBuilder().add_select_menu("calculation_task_menu")
    for stage_name, c in stages.items():
        embed.add_field(f"{stage_name}", str(c), inline=True)
        menu.add_option(f"{stage_name}", f"{stage_name}").add_to_menu()
    menu = menu.add_to_container()
    buttons = ActionRowBuilder().add_button(ButtonStyle.PRIMARY, "math_highscore_btn").set_label("highscores").add_to_container()
    if bot is None:
        raise RuntimeError
    await ctx.respond(embed=embed, components=[menu, buttons])
    stage, _, cmp_interaction = await bot.wait_for_interaction(
        custom_ids=["calculation_task_menu", "math_highscore_btn"], 
        user_id=ctx.user.id, 
        channel_id=ctx.channel_id,
    )
    log.debug(stage)
    await cmp_interaction.create_initial_response(
        ResponseType.MESSAGE_CREATE, 
        f"Well then, let's go!\nIt's not over when you calculate wrong\nYou can always stop with `stop`"
    )
    if not stage:
        return
    elif stage == "math_highscore_btn":
        await show_highscores("guild" if ctx.guild_id else "user", ctx, cmp_interaction)
        return
    else:
        c = stages[stage]
        amount = running_games.get(ctx.guild_id or 0, 0)
        running_games[ctx.guild_id or 0] = amount + 1 
        highscore = await execute_task(ctx, c)
    await MathScoreManager.maybe_set_record(
        ctx.guild_id or 0,
        ctx.user.id,
        c.name,
        highscore,
    )
    

async def _change_embed_color(msg: ResponseProxy, embed: Embed, in_seconds: int):
    await asyncio.sleep(in_seconds)
    await msg.edit(embed=embed)

async def execute_task(ctx: Context, c: CalculationBlueprint) -> int:
    """
    Returns:
    -------
        - (int) the amount of tasks, the user finished 
    """

    if bot is None:
        raise RuntimeError(f"Inu is None") # should never happen
    tasks_done = 0
    resume_task_creation = True
    while resume_task_creation:
        # new task
        log.debug("New task")
        current_task = c.get_task().replace('*', 'x').replace("/", ":")
        log.debug(current_task)
        embed = Embed(title=f"What is {current_task} ?")
        embed.color = Colors.from_name("green")
        msg = await ctx.respond(embed=embed)
        tasks: List[asyncio.Task] = []
        colors = ["yellow", "orange", "red"]
        for x in range(3):
            embed = Embed(title=f"What is {current_task} ?")
            embed.color = Colors.from_name(colors[x])
            when = (x+1) * (c._max_time / 4)
            tasks.append(
                asyncio.create_task(
                    _change_embed_color(msg, embed, when)
                )
            )

        answer = ""
        expire_time = datetime.now() + timedelta(seconds=c._max_time)
        current_task_result = float(c.get_result(current_task))
        
        def time_is_up() -> bool:
            return datetime.now() > expire_time

        while answer != current_task_result and not time_is_up():
            answer, event = await bot.wait_for_message(
                timeout=expire_time.timestamp() - time(),
                channel_id=ctx.channel_id,
                user_id=ctx.user.id,
            )

            # stopped by timeout
            if not event:
                continue

            log.debug(f"{answer=}, {event.author.username=}")
            # stopped by user
            answer = answer.replace(",", ".")
            if answer.strip().lower() == "stop":
                resume_task_creation = False
                break

            # compare
            try:
                answer = float(answer.strip())
                if answer == current_task_result:
                    await event.message.add_reaction("✅")
                else:
                    await event.message.add_reaction("❌")
            except Exception:
                # answer is not a number -> ignore
                pass

        for task in tasks:
            task.cancel()
        if time_is_up() or not resume_task_creation:
            resume_task_creation = False
        else:
            tasks_done += 1
    if tasks_done == 0 and c.name in ["Stage 1", "Stage 2"]:
        await ctx.respond(
            f"You really solved nothing? Stupid piece of shit and waste of my precious time"
        )
    else:
        await ctx.respond(
            f"You solved {tasks_done} {Human.plural_('task', tasks_done)}. The last answer was {Human.number(c.get_result(current_task))}"
        )
    return tasks_done

async def show_highscores(from_: str, ctx: Context):
    show_highscores


def load(inu: Inu):
    inu.add_plugin(plugin)
    global bot
    bot = inu






