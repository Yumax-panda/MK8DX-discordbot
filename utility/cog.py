from typing import Union, Optional
from math import floor, isnan
import pandas as pd

from discord.ext import commands, pages
from discord.utils import get
from discord import (
    Option,
    OptionChoice,
    SlashCommand,
    slash_command,
    ApplicationContext
)
from common import MyEmbed, LoungeEmbed, get_team_name, set_lounge_id, maybe_param
from objects import get_players_by_ids, get_players_by_fc_string, from_records, get_player
from team.errors import PlayerNotFound, TooManyPlayers
from constants import SUPPORT_ID

from .errors import *

ContextLike = Union[commands.Context, ApplicationContext]


async def send_template(
    ctx: ContextLike,
    hour: Union[str, int, None] = None,
    host: bool = False
) -> None:
    name = await get_team_name(ctx.guild.id) or ctx.guild.name
    header = (f'{hour} ' if hour else '') + f'交流戦お相手募集します\nこちら{name}\n'
    body = ('主催持てます\n' if host else '主催持っていただきたいです\n') + 'Sorry, Japanese clan only\n#mkmg'

    if hour is not None and (role := get(ctx.guild.roles, name=str(hour))) is not None:
        temp_players = [p for p in await get_players_by_ids([m.id for m in role.members]) if not p.is_placement]
        name_list = []
        players = []

        for p in temp_players:
            if p.name not in name_list:
                players.append(p)
            else:
                continue

        try:
            if players:
                header += f'平均MMR {500*floor(sum([p.mmr for p in players])/(len(players)*500))}程度\n'
        except:
            pass

    if isinstance(ctx, commands.Context):
        await ctx.send(header+body)
    else:
        await ctx.respond(header+body)


async def fm(
    ctx: ContextLike,
    text: str,
    ascending: Optional[bool] = None,
    view_original: bool = True
) -> None:
    data = await get_players_by_fc_string(text)

    if not any(data):
        raise PlayerNotFound
    if len(data) > 25:
        raise TooManyPlayers

    df = pd.DataFrame([p.to_dict() for p in data])

    if ascending is not None:
        df.sort_values(by='mmr', ascending=ascending, inplace=True)

    average = df['mmr'].mean(skipna=True)

    if isnan(average):
        raise PlayerNotFound

    e = LoungeEmbed(mmr=average, title=f'Average MMR: {average:.1f}')
    description = ''
    count = 0

    for player in from_records(df.to_dict('records')):
        if not player.is_empty:
            count += 1
            description += f'{str(count).rjust(3)}: [{player.name}]({player.mkc_url})' + (f'  ({int(player.mmr)})\n' if player.mmr is not None else '\n')
        else:
            description += f'N/A ({player.switch_fc})\n'

    description += f'\n**Rank**  {e.rank}'
    e.description = description

    if isinstance(ctx, commands.Context):
        await ctx.send(embed=e)
    else:
        await ctx.respond(
            content=text if view_original else None,
            embed=e
        )


async def peak(
    ctx: ContextLike,
    text: str,
    ascending: Optional[bool] = None,
    view_original: bool = True
) -> None:
    data = await get_players_by_fc_string(text)

    if not any(data):
        raise PlayerNotFound
    if len(data) > 25:
        raise TooManyPlayers

    df = pd.DataFrame([p.to_dict() for p in data])

    if ascending is not None:
        df.sort_values(by='max_mmr', ascending=ascending, inplace=True)

    average = df['max_mmr'].mean(skipna=True)

    if isnan(average):
        raise PlayerNotFound

    e = LoungeEmbed(mmr=average, title=f'Average MMR: {average:.1f}')
    description = ''
    count = 0

    for player in from_records(df.to_dict('records')):
        if not player.is_empty:
            count += 1
            description += f'{str(count).rjust(3)}: [{player.name}]({player.mkc_url})' + (f'  ({int(player.max_mmr)})\n' if player.max_mmr is not None else '\n')
        else:
            description += f'N/A ({player.switch_fc})\n'

    description += f'\n**Rank**  {e.rank}'
    e.description = description

    if isinstance(ctx, commands.Context):
        await ctx.send(embed=e)
    else:
        await ctx.respond(
            content= text if view_original else None,
            embed=e
        )


async def link(ctx: ContextLike, discord_id: int, lounge_name: str) -> None:
    p = await get_player(name=lounge_name)

    if p.is_empty:
        raise PlayerNotFound

    if p.discord_id is None:
        raise IdNotRegistered

    await set_lounge_id(discord_id, int(p.discord_id))

    if isinstance(ctx, commands.Context):
        await ctx.send(f'{p.name}と連携しました。')
    else:
        await ctx.respond({'ja': f'**{p.name}**と連携しました。'}.get(ctx.locale, f'Linked to **{p.name}**.'))


class Utility(commands.Cog, name='Utility'):

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.hide: bool = False
        self.description: str = 'Utilities'
        self.description_localizations: dict[str, str] = {'ja':'ユーティリティ'}


    @slash_command(
        name = 'help',
        description = 'Show command help',
        description_localizations = {'ja':'コマンドの使い方'}
    )
    async def help(
        self,
        ctx: ApplicationContext,
        lang: Option(
            str,
            name='language',
            name_localizations = {'ja': '言語'},
            description= 'Languages to display',
            description_localizations = {'ja': 'ヘルプの言語'},
            choices = [
                OptionChoice(name='Japanese', value='ja', name_localizations={'ja': '日本語'}),
                OptionChoice(name='English', value='en', name_localizations={'ja': '英語'})
            ],
            default = None
        )
        ) -> None:
        await ctx.response.defer(ephemeral=True)
        embeds: list[MyEmbed] = []
        locale: str = lang or ctx.locale
        is_ja: bool = locale == 'ja'

        for _, cog in self.bot.cogs.items():

            if cog.hide:
                continue

            e = MyEmbed(title=cog.description_localizations.get(locale, cog.description))
            # e.set_footer(text = '<必須> [任意]' if is_ja else '<Required> [Optional]')

            for command in cog.walk_commands():

                if isinstance(command, SlashCommand):
                    usage = command.description_localizations
                    if usage is not None:
                        usage = usage.get(locale, command.description)
                    e.add_field(
                        name = f'/{command.qualified_name}',
                        value = '> '+ usage or command.description,
                        inline = False
                    )
                elif isinstance(command, commands.Command):
                    continue # these commands no longer available.
                    if command.hidden:
                        continue
                    e.add_field(
                        name = command.usage,
                        value = '> ' + (command.brief if is_ja else command.description),
                        inline = False
                    )

            embeds.append(e)

        try:
            invite = await (self.bot.get_channel(SUPPORT_ID)).create_invite()
            owner = self.bot.get_user(self.bot.owner_id)
            contact_embed = MyEmbed(title='Contact', description=f'Support channel -> [here]({invite.url})')
            contact_embed.set_author(name=str(owner), icon_url=owner.display_avatar.url)
            embeds.append(contact_embed)
        except:
            pass

        await pages.Paginator(pages=embeds, author_check=False).respond(ctx.interaction, ephemeral=True)
        return


    @slash_command(
        name= 'mkmg',
        description = 'Create #mkmg template for twitter',
        description_localizations = {'ja': 'mkmgの外交文を作成'}
    )
    @commands.guild_only()
    async def mkmg(
        self,
        ctx: ApplicationContext,
        hour: Option(
            int,
            name = 'hour',
            name_localizations = {'ja': '時間'},
            description = 'Opening hour of match',
            description_localizations = {'ja': '交流戦の時間'},
            min_value = 0,
            default = None
        ),
        host: Option(
            str,
            name = 'host',
            name_localizations = {'ja': '主催'},
            description = 'Whether or not host',
            description_localizations = {'ja': '主催を持てるかどうか'},
            choices = [
                OptionChoice(name= 'Yes', name_localizations = {'ja': '可能'}, value = 'h'),
                OptionChoice(name= 'No', name_localizations = {'ja': '不可'}, value = '')
            ],
            default = ''
        )
    ) -> None:
        await ctx.response.defer()
        await send_template(ctx, hour, host == 'h')


    @commands.command(
        name = 'mkmg',
        aliases = ['m'],
        description = 'Create #mkmg template for twitter',
        brief = 'mkmgの外交文を作成',
        usage = '!m [hour] [host -> h]',
        hidden = False
    )
    @commands.guild_only()
    async def text_mkmg(
        self,
        ctx: commands.Context,
        hour: Optional[int] = None,
        host: str = ''
    ) -> None:
        await send_template(ctx, hour, host.lower() == 'h')


    @commands.command(
        name = 'fm',
        description = 'Search MMRs by friend codes.',
        brief = 'フレンドコードでMMRを検索',
        usage = '!fm <switch friend codes>',
        hidden = False
    )
    async def fm(self, ctx: commands.Context, *, text: str) -> None:
        await fm(ctx, text, None)


    @commands.command(
        name = 'fmh',
        aliases = ['fh'],
        description = 'Search MMRs by friend codes. (dec)',
        brief = 'フレンドコードでMMRを検索(高い順)',
        usage = '!fmh <switch friend codes>',
        hidden = False
    )
    async def fmh(self, ctx: commands.Context, *, text: str) -> None:
        await fm(ctx, text, False)


    @commands.command(
        name = 'fml',
        aliases = ['fl'],
        description = 'Search MMRs by friend codes. (asc)',
        brief = 'フレンドコードでMMRを検索(低い順)',
        usage = '!fml <switch friend codes>',
        hidden = False
    )
    async def fml(self, ctx: commands.Context, *, text: str) -> None:
        await fm(ctx, text, True)


    @commands.command(
        name = 'peak',
        description = 'Search Peak MMRs by friend codes.',
        brief = 'フレンドコードでPeak MMRを検索',
        usage = '!peak <switch friend codes>',
        hidden = False
    )
    async def peak(self, ctx: commands.Context, *, text: str) -> None:
        await peak(ctx, text, None)


    @commands.command(
        name = 'peakh',
        aliases = ['ph'],
        description = 'Search Peak MMRs by friend codes.(dec)',
        brief = 'フレンドコードでPeak MMRを検索(高い順)',
        usage = '!peakh <switch friend codes>',
        hidden = False
    )
    async def peakh(self, ctx: commands.Context, *, text: str) -> None:
        await peak(ctx, text, False)


    @commands.command(
        name = 'peakl',
        aliases = ['pl'],
        description = 'Search Peak MMRs by friend codes.(asc)',
        brief = 'フレンドコードでPeak MMRを検索(低い順)',
        usage = '!peakl <switch friend codes>',
        hidden = False
    )
    async def peakl(self, ctx: commands.Context, *, text: str) -> None:
        await peak(ctx, text, True)


    @commands.command(
        name='link',
        description = 'Link to another account used in lounge server.',
        brief = 'ラウンジサーバーに入っているアカウントと連携',
        usage = '!link <player_name>',
        hidden = False
    )
    async def text_link(self, ctx: commands.Context, *, name: str) -> None:
        await link(ctx, ctx.author.id, name)


    @slash_command(
        name='link',
        description = 'Link to another account used in lounge server.',
        description_localizations = {'ja': 'ラウンジサーバーに入っているアカウントと連携'}
    )
    async def link(
        self,
        ctx: ApplicationContext,
        name: Option(
            str,
            name = 'player_name',
            name_localizations = {'ja': 'ラウンジ名'},
            description = 'Player name to link to.',
            description_localizations = {'ja': '連携するプレイヤー名'}
        )
    ) -> None:
        await ctx.response.defer()
        await link(ctx, ctx.user.id, name)


    @slash_command(
        name = 'who',
        description = 'Search Lounge name',
        description_localizations = {'ja': 'ラウンジ名を検索'}
    )
    @commands.guild_only()
    async def who(
        self,
        ctx: ApplicationContext,
        input_str: Option(
            str,
            name = 'name',
            name_localizations = {'ja': '名前'},
            description = 'Switch FC, Discord ID, server nick-name and Lounge name are available.',
            description_localizations = {'ja': 'フレコ、Discord ID、ニックネーム、ラウンジ名で検索可能'}
        )
    ) -> None:
        await ctx.response.defer()

        if (member := ctx.guild.get_member_named(input_str)) is not None:
            player = (await get_players_by_ids([member.id]))[0]
        else:
            name, discord_id, fc = maybe_param(input_str)
            player = await get_player(name=name, discord_id=discord_id, switch_fc=fc)

        if player.is_empty:
            raise PlayerNotFound

        msg = f'[{player.name}]({player.lounge_url})'

        if player.linked_id is not None:
            if (user := self.bot.get_user(int(player.linked_id))) is not None:
                msg += f'  ({str(user)})'

        await ctx.respond(msg)


    @commands.command(
        name='mlink',
        description = 'Link to another account used in lounge server.',
        brief = 'ラウンジサーバーに入っているアカウントと連携',
        usage = '!mlink  <user_id> <player_name>',
        hidden = True
    )
    @commands.is_owner()
    async def mlink(self, ctx: commands.Context, user_id: int, *, name: str) -> None:
        await link(ctx, user_id, name)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Utility(bot))
