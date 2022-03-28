from argparse import Action
from typing import *
import akinator
import asyncio
from akinator.async_aki import Akinator
from . import Paginator, listener
import hikari
import lightbulb
from lightbulb.context import Context
from hikari.impl import ActionRowBuilder

from utils import Human
from core import Inu, getLogger

log = getLogger(__name__)

#from akinator.async_aki import Akinator


class AkinatorSI(Paginator):
    def __init__(
        self,
        language: str
    ):
        super().__init__(page_s="..", timeout=240)
        self.aki: Akinator = Akinator()

    async def start(self, ctx: Context):
        #await self.post_start()
        await self.main(ctx)

    async def main(self, ctx: Context):
        win = False
        bot: Inu = ctx.bot
        question = await self.aki.start_game()
        interaction: Optional[hikari.ComponentInteraction] = None
        translate_answer={
            "aki_yes": "yes",
            "aki_maybe_yes": "probably",
            "aki_idk": "i don't know",
            "aki_maybe_no": "probably not",
            "aki_no": "no",
            "aki_back": "<-- back",
            "aki_end": "X exit"
        }
        components=[
            ActionRowBuilder()
            .add_button(hikari.ButtonStyle.SUCCESS, "aki_yes")
            .set_label("✔️ Yes")
            .add_to_container()
            .add_button(hikari.ButtonStyle.DANGER, "aki_no")
            .set_label("❌ No")
            .add_to_container()
            .add_button(hikari.ButtonStyle.PRIMARY, "aki_idk")
            .set_label("❔ I don't know")
            .add_to_container()
            .add_button(hikari.ButtonStyle.SECONDARY, "aki_maybe_yes")
            .set_label("probably")
            .add_to_container()
            .add_button(hikari.ButtonStyle.SECONDARY, "aki_maybe_no")
            .set_label("I don't think so")
            .add_to_container(),
            ActionRowBuilder()
            .add_button(hikari.ButtonStyle.PRIMARY, "aki_back")
            .set_label("◀ Back")
            .add_to_container()
            .add_button(hikari.ButtonStyle.PRIMARY, "aki_end")
            .set_label("You don't get it ⏹")
            .add_to_container()
        ]
        i = 1
        description = ""
        while self.aki.progression <= 80:
            if interaction:
                asyncio.wait(
                    [
                        # await asyncio.create_task(
                        #     msg.edit(components=[])
                        # ),
                        await asyncio.create_task(
                            interaction.edit_message(
                                message=(await msg.message()).id,
                                embed=hikari.Embed(
                                    title=f"{i}.\n{question}",
                                    description=Human.short_text(description, 2000),
                                ),
                                components=components
                            )
                        )
                    ]
                )
            else:
                msg = await ctx.respond(
                    embed=hikari.Embed(
                        title=f"{i}.\n{question}"
                    ),
                    components=components,
                )
            answer, event, interaction = await bot.wait_for_interaction(
                custom_ids=["aki_yes", "aki_maybe_yes", "aki_maybe_no", "aki_no", "aki_back", "aki_idk", "aki_end"],
                user_id=ctx.author.id,
                channel_id=ctx.channel_id,
            )
            await interaction.create_initial_response(
                hikari.ResponseType.DEFERRED_MESSAGE_UPDATE
            )
            description = f"{i}. {question} {translate_answer[answer]}\n{description}"
            if answer == "aki_back":
                try:
                    question = await self.aki.back()
                except akinator.CantGoBackAnyFurther:
                    await bot.rest.create_message(ctx.channel_id, "You can't go back any further")
            elif answer == "aki_end":
                break
            else:
                question = await self.aki.answer(translate_answer[answer])
            i += 1
        if self.aki.progression >= 80:
            await self.aki.win()

            await msg.edit(components=[])
            await ctx.respond(
                embed=hikari.Embed(
                    title=f"I think to {self.aki.progression:.0f}% it's {self.aki.first_guess['name']} ({self.aki.first_guess['description']})!"
                )
                .set_image(self.aki.first_guess['absolute_picture_path']),
            )
        else:
            await self.aki.win()
            await ctx.respond(f"""Well played. These where the last characters I thought of: {', '.join(f"{float(a['proba'])*100:.1f}% {a['name']}" for a in self.aki.guesses)}""")
        # if correct.lower() == "yes" or correct.lower() == "y":
        #     print("Yay\n")
        # else:
        #     print("Oof\n")
        await self.aki.close()