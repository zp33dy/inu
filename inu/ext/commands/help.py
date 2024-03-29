import re
from typing import (
    List,
    Sequence,
    Union,
    Optional,
    Mapping,
    Dict,
)

import hikari
import lightbulb
from lightbulb import help_command
from lightbulb.context import Context
from lightbulb.commands import Command, PrefixCommand, PrefixCommandGroup, CommandLike, PrefixSubCommand, PrefixSubGroup

from core import Inu, getLogger
from utils import Paginator, Colors

log = getLogger(__name__)


bot_app: Optional[Inu] = None



class CustomHelp(help_command.BaseHelpCommand):
    def __init__(self, bot: lightbulb.BotApp):
        super().__init__(bot)
        global bot_app
        bot_app = bot
        self.cmds_per_list: int = 5
    async def send_bot_help(self, context: Context):
        commands = list(set(list(command for command in self.bot.prefix_commands.values())))

        dicts_prebuild = self.arbitrary_commands_to_dicts(commands, context, False)
        await self.dicts_to_pagination(dicts_prebuild, context)

    async def send_plugin_help(self, context: Context, plugin):
        pass

    async def send_command_help(self, context: Context, command: Command):
        # Override this method to change the message sent when the help command
        # argument is the name or alias of a command.
        dicts = [[self.command_to_dict(command, context)]]
        await self.dicts_to_pagination(dicts, context)

    async def send_group_help(self, context: Context, group):
        commands = self.group_to_commands(group, context)
        dicts = self.part_up_dicts(self.commands_to_dicts(commands, context))
        await self.dicts_to_pagination(dicts, context)


    async def object_not_found(self, context: Context, obj):
        # Override this method to change the message sent when help is
        # requested for an object that does not exist
        commands = self.search(obj)
        log.debug(commands)
        dicts_prebuild = self.arbitrary_commands_to_dicts(commands, context, resolve_subcommands=True)
        await self.dicts_to_pagination(dicts_prebuild, context)


    def arbitrary_commands_to_dicts(
        self, 
        arb_commands: List[Command],
        ctx: Context, 
        resolve_subcommands: bool = False,
    ) -> List[List[Dict[str, str]]]:
        """
        Build the command dicts from random Commands, where its unknown if they are a group or not 

        Args
        ----
            - commands: (List[Dict[str, str]]) a list with commands which where before converted into dicts
            - ctx: (Context) needed for command prefix
            - resolve_subcommands: (bool, default=False) Wether or not the parent commands of a subcommand should be added
              and fully resolved (you will see all commands of this parent command) in the return value

        Returns
        -------
            - dicts (List[List[Dict[str, str]]]) A list which represents all embeds. The second List represents one embed
              The Dict inside the second List represents one field. It's keys are: `sign`, `description`, `group`.
              `sign` will the the name of the field. The other keys will be in the value
        """
        resolved_commands = []
        groups = []
        commands = []
        for command in arb_commands:
            if isinstance(command, (PrefixCommandGroup, PrefixSubGroup)):
                groups.append(command)
            elif isinstance(command, (PrefixCommand, PrefixSubCommand)):
                commands.append(command)
        for group in groups:
            # get ALL subcommands of a group and add it to resolved_commands
            # for the first, I ll try to put all commands from a group on one site
            resolved = self.part_up_dicts(
                self.commands_to_dicts(
                    self.group_to_commands(group, ctx),
                    ctx
                )
            )
            resolved_commands.extend(resolved)
        if commands:
            parted_commands = self.part_up_dicts(self.commands_to_dicts(commands, ctx))
            resolved_commands.extend(parted_commands)
        return resolved_commands


    def part_up_dicts(self, commands: List[Dict[str, str]], max_above: int = 2) -> List[List[Dict[str, str]]]:
        """
        breaks a list into multiple lists, based on self.cmds_per_list.
        
        Args
        ----
            - commands: (List[Command]) a list with all commands, not allready parted
            - max_above: (int, defualt=2) When <commands> have 7 commands, but cmds_per_list is 5,
              then the list wont be parted, to avaid, that are only one or two commands at the next site
        Returns
        -------
            - List[List[Dict[str, str]]] this list should be extended to an existing list with dicts.
              will also work if not.
        """
        if not commands:
            return []
        if len(commands) <= self.cmds_per_list + max_above:
            return [commands]
        parted_commands = []
        part = []
        for i, command in enumerate(commands):
            if i % self.cmds_per_list == 0 and part:
                parted_commands.append(part)
                part = []
            part.append(command)
        if part:
            parted_commands.append(part)
        if len(parted_commands[-1]) <= max_above and len(parted_commands) >= max_above:
            part = parted_commands.pop()
            parted_commands[-1].extend(part)
        return parted_commands


    def search(self, obj, commands=[], search_deeper: bool = True) -> List[Command]:
        """
        ### Iterates recursivly through the bot commands/groups/subcommands
        
        Returns
        -------
            - (List[Command]) a List with commandlike objects, where the name matches with <`obj`> 

        """
        results = []
        commands = commands or self.bot.prefix_commands.values()
        for command in commands:
            if (
                (obj in command.name or [a for a in command.aliases if obj in a]) 
                and not command in results
            ):
                results.append(command)
            elif isinstance(command, (PrefixSubGroup, PrefixCommandGroup)):
                if (sub_commands := [*command.subcommands.values()]):
                    matching_sub_cmds = self.search(
                        obj, 
                        commands=sub_commands,
                        search_deeper=False,
                    )
                    if matching_sub_cmds:
                        results.extend(matching_sub_cmds)

        if not results and search_deeper:
            return list(set(self.search(obj[:-1])))
        else:
            return list(set(results))


    def group_to_commands(self, group: Union[PrefixCommandGroup, PrefixSubGroup], ctx: Context):
        commands: List[Command] = [group]  # because the group is also a command
        for command in group.subcommands.values():
            if not command in commands:
                commands.append(command)
        for command in commands[1:]:
            if isinstance(command, PrefixSubGroup):
                subcommands = self.group_to_commands(command, ctx)[1:]  # remove group, since the group is already in
                commands.extend(subcommands)
        return commands


    async def dicts_to_pagination(self, dicts: List[List[Dict[str, str]]], ctx: Context) -> None:
        """
        starts the pagination.

        Args
        ----
            - dicts (List[List[Dict[str, str]]]) A list which represents all embeds. The second List represents one embed
              The Dict inside the second List represents one field of the embed (mapping from name: value)
            - ctx: (Context) the context, to send the message(s)
        """
        embeds = self.dicts_to_embeds(dicts)
        pag = Paginator(page_s=embeds, timeout=500)
        await pag.start(ctx)


    def dicts_to_embeds(
        self, 
        dicts: List[List[Dict[str, str]]],
        small: bool = False,
    ) -> List[hikari.Embed]:
        """
        ### converts <`dicts`> to a list with embeds

        Args:
        -----
            - dicts (List[List[Dict[str, str]]]) the dict prebuild
            - small (bool, default=True) wether the embed should have footer and title 
        Returns
        -------
            - (List[Embed]) the list with embeds
        """
        embeds = []
        for i, prebuild in enumerate(dicts):
            name = prebuild[0]["group"]
            embed = hikari.Embed()
            if not small:
                embed.title=f"Help {name}"
                embed.set_footer(text=f"page {i+1}/{len(dicts)}", icon=self.bot.get_me().avatar_url)
            # embed.description = "<...> required - I need it\n[...] optional - I don't need it"
            for field in prebuild:
                embed.add_field(field["sign"], field["description"])
            embed.color = Colors.random_color()
            embeds.append(embed)
        return embeds
            
    
    def commands_to_dicts(self, commands: List[Command], ctx: Context) -> List[Dict[str, str]]:
        group_name = None
        if isinstance(commands[0], PrefixCommandGroup):
            group_name = f"{commands[0].name} "
        return [self.command_to_dict(command, ctx, group_name) for command in commands]


    def command_to_dict(
        self, 
        command: Command, 
        ctx: Context, 
        group_name: str = None,
        with_cmd_docs: bool = False,
    ) -> Dict:
        """returns a string with the command signature, aliases and options"""
        desc = ""
        desc += f"_{command.description}_"
        if (option_info := self._get_command_info(command)):
            desc += f"```{option_info}```"
        return {
            "sign": f"\n{self._get_command_signature(command, ctx)}",
            "description": desc,
            "group": f" for Group: {group_name}" if group_name else ""
        }


    def _remove_defaults(self, cmd_signature: str) -> str:
        """removes defaults and <ctx>"""
        if (i:=cmd_signature.find("<ctx>")) != -1:
            cmd_signature = f"{cmd_signature[:i]}{cmd_signature[i+6:]}"
        start = cmd_signature.find("=")
        if start == -1:
            return cmd_signature
        end = []
        end.append(cmd_signature.find(">", start))
        end.append(cmd_signature.find("]", start))
        while -1 in end:
            end.remove(-1)

        to_remove = cmd_signature[start:min(end)]
        cmd_signature = re.sub(to_remove, '', cmd_signature)

        if "=" in cmd_signature:
            cmd_signature = self._remove_defaults(cmd_signature)
        return cmd_signature


    def _get_command_signature(self, command: Command, ctx: Context):
        full_invoke = command.qualname.replace(command.name, "")
        cmd_sign = self._remove_defaults(command.signature)
        signature = f"{ctx.prefix}{cmd_sign}" #{full_invoke} ..
        return signature
    

    def _get_command_info(
        self, 
        command: Command,
        with_doc_strings: bool = True,
    ) -> str:
        """
        Returns
        -------
            - (str) aliases and option descriptions
        """
        args = ""
        optional = []
        required = []
        cmd_invoke = f"{command.name}"
        if command.aliases:
            args += f"'{cmd_invoke}' is equal to:\n"
            for a in command.aliases:
                args += f"    - {a}\n"
        
        for name, option in command.options.items():
            if option.required:
                required.append(option)
            else:
                optional.append(option)
        if required:
            args += "required:\n"
            for option in required:
                args += f"    - {option.name}: {option.description}\n"
        if optional:
            args += "optional:\n"
            for option in optional:
                args += f"    - {option.name}: {option.description}\n"
        return args

    async def help(self, ctx: Context):
        for name, cmd in self.bot.prefix_commands.items():
            pass


class OutsideHelp:
    bot: Optional[lightbulb.BotApp] = None
    @classmethod
    async def search(
        cls, 
        obj: str, 
        ctx: Context, 
        message: Optional[str] = None,
        only_one_entry: bool = False,
    ) -> None:

        if cls.bot is None:
            log.warning(f"can't execute search because bot is not initialized")
            return

        help = CustomHelp(cls.bot)
        commands = help.search(obj)
        dicts_prebuild = help.arbitrary_commands_to_dicts(commands, ctx)
        def get_matching_entry(dicts_prebuild: List[List[Dict[str, str]]]) -> Optional[List[List[Dict[str, str]]]]:
            complete_invokation = f"{ctx.prefix}{ctx.invoked.qualname}"
            if only_one_entry:
                for embed in dicts_prebuild:
                    for field in embed:
                        log.debug(f"{complete_invokation} in {field['sign']}")
                        if complete_invokation in field["sign"]:
                            return [[field]]
            return None
        if only_one_entry:
            dicts_prebuild = get_matching_entry(dicts_prebuild)
            assert isinstance(dicts_prebuild, list)

        embeds = help.dicts_to_embeds(dicts_prebuild, small=True)
        kwargs = {}
        if message:
            kwargs["content"] = message
        pag = Paginator(page_s=embeds, first_message_kwargs=kwargs)
        await pag.start(ctx)



def load(bot):
    global bot_app
    bot_app = bot
    OutsideHelp.bot = bot
    bot.d.old_help_command = bot.help_command
    bot.help_command = CustomHelp(bot)



def unload(bot):
    bot.help_command = bot.d.old_help_command
    del bot.d.old_help_command