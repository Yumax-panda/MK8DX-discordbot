from typing import Optional
from discord.ext import commands, pages
from discord.utils import get
from discord import (
    File,
    Guild,
    EmbedField,
    TextChannel,
    CheckFailure,
    ApplicationContext,
    ApplicationCommandError
)
from io import StringIO
import traceback
import sys

from errors import *
from common import ErrorEmbed, MyEmbed
from constants import LOG_CHANNEL_ID

from .errors import *


class Admin(commands.Cog, name='Admin', command_attrs=dict(hidden=True)):

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.hide: bool = True
        self.LOG_CHANNEL: TextChannel = None


    async def send_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        e = ErrorEmbed(
            title = error.__class__.__name__,
            description = f'```{error}```',
            fields=[
                EmbedField(
                    name='Command name',
                    value=ctx.command.name,
                    inline=False,
                ),
                EmbedField(
                    name='content',
                    value=f'```{ctx.message.content}```',
                    inline=False
                ),
                EmbedField(
                    name='Channel',
                    value=f'{ctx.channel.name} (`{ctx.channel.id}`)',
                    inline=False
                )
            ]
        )
        e.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        buffer = StringIO()
        t, _, tb = sys.exc_info()
        traceback.print_exception(t, error, tb, file=buffer)
        buffer.seek(0)
        await self.LOG_CHANNEL.send(embed=e, file=File(fp=buffer, filename='traceback.txt'))
        buffer.close()


    async def send_app_error(self, ctx: ApplicationContext, error: ApplicationCommandError) -> None:
        e = ErrorEmbed(
            title = error.__class__.__name__,
            description = f'```{error}```',
            fields=[
                EmbedField(
                    name='Command name',
                    value=ctx.command.qualified_name,
                    inline=False,
                ),
                EmbedField(
                    name='Inputs',
                    value=f'```{ctx.selected_options}```',
                    inline=False
                ),
                EmbedField(
                    name='Channel',
                    value=f'{ctx.channel.name} (`{ctx.channel.id}`)',
                    inline=False
                )
            ]
        )
        e.set_author(name=str(ctx.user), icon_url=ctx.user.display_avatar.url)
        buffer = StringIO()
        t, _, tb = sys.exc_info()
        traceback.print_exception(t, error, tb, file=buffer)
        buffer.seek(0)
        await self.LOG_CHANNEL.send(embed=e, file=File(fp=buffer, filename='traceback.txt'))
        buffer.close()


    @commands.command(
        name='gl',
        aliases=['guilds'],
        description='Show all guilds.',
        brief = '全てのサーバーを表示',
        usage = '!gl',
        hidden = True
    )
    @commands.is_owner()
    async def guild_list(self, ctx: commands.Context) -> None:
        p = commands.Paginator(prefix='', suffix='', max_size=1000)

        for guild in self.bot.guilds:
            p.add_line(f'{guild.name} `({guild.id})`')

        is_compact = len(p.pages) == 1

        await pages.Paginator(
            pages = [
                MyEmbed(
                    title=f'ギルド ({len(self.bot.guilds)})',
                    description = content
                )
                for content in p.pages
            ],
            show_disabled=not is_compact,
            show_indicator= not is_compact,
            author_check=False
        ).send(ctx, target=ctx.author)


    @commands.command(
        name='ul',
        aliases=['users'],
        description='Show all users.',
        brief = '全てのユーザーを表示',
        usage = '!ul',
        hidden = True
    )
    @commands.is_owner()
    async def user_list(self, ctx: commands.Context) -> None:
        p = commands.Paginator(prefix='', suffix='', max_size=1000)

        for user in self.bot.users:
            p.add_line(f'{str(user)} (`{user.id}`)')

        is_compact: bool = len(p.pages) == 1

        await pages.Paginator(
            pages = [
                MyEmbed(
                    title=f'ユーザー ({len(self.bot.users)})',
                    description=content
                    )
                    for content in p.pages
                ],
            show_disabled = not is_compact,
            show_indicator = not is_compact,
            author_check = False
        ).send(ctx, target=ctx.author)


    @commands.command(
        name='user',
        aliases=['u'],
        description='Show user info',
        brief = 'ユーザー情報を表示',
        usage = '!user <ID or name>',
        hidden = True
    )
    @commands.is_owner()
    async def user(self, ctx: commands.Context, user_id: Optional[int] = 0, name: Optional[str] = '') -> None:

        if (user := get(self.bot.users, name=name) or get(self.bot.users, id=user_id)) is None:
            raise NotFoundError

        e = MyEmbed(title=str(user), description='参加サーバー\n')
        e.set_author(name=str(user.id), icon_url=user.display_avatar.url)

        for g in user.mutual_guilds:
            e.description += f'{g.name} (`{g.id}`)\n'

        await ctx.author.send(embed=e)


    @commands.command(
        name='guild',
        aliases=['g', 'server'],
        description='Show guild info',
        brief = 'ギルド情報を表示',
        usage = '!g <ID or name>',
        hidden = True
    )
    @commands.is_owner()
    async def guild(self, ctx: commands.Context, guild_id: Optional[int] = 0, name: Optional[str] = '') -> None:

        if (g := get(self.bot.guilds, name=name) or get(self.bot.guilds, id=guild_id)) is None:
            raise NotFoundError

        header = f'メンバー ({len(g.members)})\n'
        p = commands.Paginator(prefix='', suffix='', max_size = 1000)

        for member in g.members:

            if member == g.owner:
                p.add_line(f'__**{str(member)}**__ (`{member.id}`)')
            else:
                p.add_line(f'{str(member)} (`{member.id}`)')

        is_compact: bool = len(p.pages) == 1
        await pages.Paginator(
            pages = [
                MyEmbed(
                    title = f'{g.name} (`{g.id}`)',
                    description = header + content
                    )
                    for content in p.pages
                ],
            show_disabled = not is_compact,
            show_indicator = not is_compact,
            author_check = False
        ).send(ctx, target=ctx.author)


    @commands.Cog.listener('on_ready')
    async def on_ready(self) -> None:
        self.LOG_CHANNEL: TextChannel = self.bot.get_channel(LOG_CHANNEL_ID)


    @commands.Cog.listener('on_application_command_error')
    async def app_error_handler(self, ctx: ApplicationContext, error: ApplicationCommandError) -> None:
        content: Optional[str] = None

        if isinstance(error, MyError):
            content = error.localized_content(ctx.locale)
        elif isinstance(error, commands.NoPrivateMessage):
            content = {'ja': 'DMでこのコマンドは使えません。'}.get(ctx.locale, 'This command is not available in DM channels.')
        elif isinstance(error, CheckFailure):
            content = {'ja': 'このコマンドは無効です。'}.get(ctx.locale, 'This command is not available.')

        if content is not None:
            await ctx.respond(content, ephemeral=True)
            return

        await self.send_app_error(ctx, error)
        await ctx.respond({'ja': '予期しないエラーが発生しました。'}.get(ctx.locale, 'Unexpected error raised.'))
        await ctx.interaction.delete_original_response()


    @commands.Cog.listener('on_command_error')
    async def command_error_handler(self, ctx: commands.Context, error: commands.CommandError) -> None:
        content: Optional[str] = None

        if isinstance(error, MyError):
            content = error.message
        elif isinstance(error, commands.NoPrivateMessage):
            content = 'DMでこのコマンドは使えません。\nThis command is not available in DM channels.'
        elif isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.NotOwner):
            content = 'これは管理者専用コマンドです。\nThis command is only for owner.'
        elif isinstance(error, commands.UserInputError):
            content = f'コマンドの入力が不正です。\n{ctx.command.usage}'
        elif isinstance(error, commands.BotMissingPermissions):
            content = f'このコマンドを使うにはBotへ以下の権限のください。\n\
                In order to invoke this command, please give me the following permissions\n\
                **{", ".join(error.missing_permissions)}**'
        elif isinstance(error, commands.CheckFailure):
            return

        if content is not None:
            await ctx.send(content)
            return

        await self.send_command_error(ctx, error)
        await ctx.send('予期しないエラーが発生しました。\nUnexpected error raised.')


    @commands.Cog.listener('on_guild_join')
    async def inform_new_guild(self, guild: Guild) -> None:
        e = MyEmbed(
            title=f'Guild join (total: {len(self.bot.guilds)})',
            fields= [
                EmbedField(
                    name='Basic Info',
                    value= f'{guild.name} (`{guild.id}`)',
                    inline=False
                ),
                EmbedField(
                    name=f'Members ({len(guild.members)})',
                    value=f'Owner: {str(guild.owner) if guild.owner else "Not found"}',
                    inline=False
                )
            ]
        )

        if self.LOG_CHANNEL is None:
            self.LOG_CHANNEL = self.bot.get_channel(LOG_CHANNEL_ID)

        await self.LOG_CHANNEL.send(embed=e)



def setup(bot: commands.Bot) -> None:
    bot.add_cog(Admin(bot))
