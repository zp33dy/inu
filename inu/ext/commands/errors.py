from contextlib import suppress
import random
import asyncio
from typing import *
import traceback

import hikari
from hikari import Embed
import lightbulb
from lightbulb import events, errors
from lightbulb.context import Context

from core import Inu
from utils.language import Human
from .help import OutsideHelp

from core import getLogger, BotResponseError, Inu

log = getLogger(__name__)
pl = lightbulb.Plugin("Error Handler")
bot: Inu



@pl.listener(hikari.ExceptionEvent)
async def on_exception(event: hikari.ExceptionEvent):
    # not user related error
    try:

        if isinstance(event.exception, events.CommandErrorEvent):
            return
        log.error(f"{''.join(traceback.format_exception(event.exception))}")
    except Exception:
        log.critical(traceback.format_exc())



@pl.listener(events.CommandErrorEvent)
async def on_error(event: events.CommandErrorEvent):
    """
    """
    try:
        ctx: Context | None = event.context

        if not isinstance(ctx, Context):
            log.debug(f"Exception uncaught: {event.__class__}")
            return
        error = event.exception
        log.debug(f"{dir(event)}")
        log.debug(f"{dir(error)}")
        async def message_dialog(error_embed: hikari.Embed):
            error_id = f"{bot.restart_num}-{bot.id_creator.create_id()}-{bot.me.username[0]}"
            component=(
                hikari.impl.ActionRowBuilder()
                .add_button(hikari.ButtonStyle.PRIMARY, "error_send_dev_silent")
                .set_label("🍭 Send report")
                .add_to_container()
                .add_button(hikari.ButtonStyle.PRIMARY, "error_send_dev")
                .set_label("🍭 Add note & send")
                .add_to_container()

            )
            # if pl.bot.conf.bot.owner_id == ctx.user.id:
            #     component = (
            #         component
            #         .add_button(hikari.ButtonStyle.SECONDARY, "error_show")
            #         .set_label("Show error")
            #         .add_to_container()
            #     )
            message = await (await ctx.respond(
                embed=error_embed,
                component=component
            )).message()

            def check(event: hikari.ReactionAddEvent):
                if event.user_id != bot.me.id and event.message_id == message.id:
                    return True
                return False
            
            custom_id, _, interaction = await bot.wait_for_interaction(
                custom_ids=["error_send_dev", "error_show", "error_send_dev_silent"],
                message_id=message.id,
                user_id=ctx.user.id
            )
            # await interaction.delete_message(message)
            embeds: List[Embed] = [Embed(title=f"Bug #{error_id}", description=str(error)[:2000])]
            embeds[0].set_author(
                name=f'Invoked by: {ctx.user.username}',
                icon=ctx.author.avatar_url
            )
            embeds[0].add_field(
                "invoked with", 
                value=(
                    f"Command: {ctx.invoked_with}\n"
                    "\n".join([f"`{k}`: ```\n{v}```" for k, v in ctx.raw_options.items()])
                )[:1000]
            )
            nonlocal event
            traceback_list = traceback.format_exception(*event.exc_info)
            if len(traceback_list) > 0:
                log.warning(str("\n".join(traceback_list)))
            error_embed.add_field(
                name=f'{str(error.__class__)[8:-2]}',
                value=f'Error:\n{error}'[:1024],
            )
            for index, tb in enumerate(traceback_list):
                if index % 20 == 0 and index != 0:
                    embeds.append(Embed(description=f"Bug #{error_id}"))
                embeds[-1].add_field(
                    name=f'Traceback - layer {index + 1}',
                    value=f'```python\n{Human.short_text_from_center(tb, 1000)}```',
                    inline=False
                )
            kwargs: Dict[str, Any] = {"embeds": embeds}
            answer = ""
            if custom_id == "error_show":
                await message.edit(embeds=embeds)
                
            if custom_id == "error_send_dev":
                try:
                    answer, interaction, event = await bot.shortcuts.ask_with_modal(
                        f"Bug report", 
                        question_s="Do you have additional information?", 
                        interaction=interaction,
                        pre_value_s="/",
                    )
                except asyncio.TimeoutError:
                    answer = "/"
                if answer == "/":
                    answer = ""

            kwargs["content"] = f"**{40*'#'}\nBug #{error_id}\n{40*'#'}**\n\n\n{Human.short_text(answer, 1930)}"

            message = await bot.rest.create_message(
                channel=bot.conf.bot.bug_channel_id,
                **kwargs
            )
            if interaction:
                await interaction.create_initial_response(
                    content=(
                        f"**Bug #{error_id}** has been reported.\n"
                        f"You can find the bug report [here]({message.make_link(message.guild_id)})\n"
                        f"If you can't go to this message, or need additional help,\n"
                        f"consider to join the [help server]({bot.conf.bot.guild_invite_url})"

                    ),
                    flags=hikari.MessageFlag.EPHEMERAL,
                    response_type=hikari.ResponseType.MESSAGE_CREATE
                )
            # elif str(e.emoji_name) == '❔':
            #     await OutsideHelp.search(ctx.invoked_with, ctx)
            #     await message.remove_all_reactions()
            return

        # errors which will be handled also without prefix
        if isinstance(error, errors.NotEnoughArguments):
            return await OutsideHelp.search(
                obj=ctx.invoked_with,
                ctx=ctx,
                message=(
                    f"to use the `{ctx.invoked.qualname}` command, "
                    f"I need {Human.list_([o.name for o in error.missing_options], '`')} to use it"
                ),
                only_one_entry=True,
            )
        elif isinstance(error, errors.CommandIsOnCooldown):
            return await ctx.respond(
                f"You have used `{ctx.invoked.qualname}` to often. Retry it in `{error.retry_after:.01f} seconds` again"
            )
        elif isinstance(error, errors.ConverterFailure):
            return await OutsideHelp.search(
                obj=ctx.invoked_with,
                ctx=ctx,
                message=(
                    f"the option `{error.option.name}` has to be {Human.type_(error.option.arg_type, True)}"
                ),
                only_one_entry=True,
            )
        elif isinstance(error, errors.MissingRequiredPermission):
            return await ctx.respond(
                f"You need the `{error.missing_perms.name}` permission, to use `{ctx.invoked_with}`",
                flags=hikari.MessageFlag.EPHEMERAL,
            )
        elif isinstance(error, errors.CheckFailure):
            fails = set(
                str(error)
                .replace("Multiple checks failed: ","")
                .replace("This command", f"`{ctx.invoked_with}`")
                .split(", ")
            )
            if len(fails) > 1:
                str_fails = [f"{i+1}: {e}"
                    for i, e in enumerate(fails)
                ]
                return await ctx.respond(
                    "\n".join(fails)
                )
            else:
                return await ctx.respond(fails.pop())
        elif isinstance(error, errors.CommandInvocationError) and isinstance(error.original, BotResponseError):
            return await ctx.respond(**error.original.kwargs)

        # errors which will only be handled, if the command was invoked with a prefix
        if not ctx.prefix:
            return # log.debug(f"Suppress error of type: {error.__class__.__name__}")
        if isinstance(error, errors.CommandNotFound):
            return await OutsideHelp.search(
                obj=error.invoked_with, 
                ctx=ctx, 
                message=f"There is no command called `{error.invoked_with}`\nMaybe you mean one from the following ones?"
            )
        else:
            error_embed = hikari.Embed()
            error_embed.title = "Oh no! A bug occurred"
            error_embed.description = str(error)[:2000]
            with suppress(hikari.ForbiddenError):
                await message_dialog(error_embed)
    except Exception:
        log.critical(traceback.format_exc())



def load(inu: Inu):
    global bot
    bot = inu
    inu.add_plugin(pl)
