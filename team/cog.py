from discord.ext import commands, pages
from discord import (
    Role,
    Option,
    slash_command,
    SlashCommandGroup,
    ApplicationContext
)
from math import isnan
import pandas as pd

from common import MyEmbed, LoungeEmbed, get_team_name, set_team_name, get_dt
from objects import get_players_by_ids, PlayerLike, from_records

from .components import Vote
from .errors import *


class Team(commands.Cog, name='Team'):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.hide: bool = False
        self.description: str = 'Manage team info'
        self.description_localizations: dict[str, str] = {'ja':'チーム関連'}

    team = SlashCommandGroup(name='team')
    name = team.create_subgroup(name='name')


    @staticmethod
    async def get_players(role: Role) -> list[PlayerLike]:
        players = await get_players_by_ids([m.id for m in role.members])

        if not any(players):
            raise PlayerNotFound

        return from_records(pd.DataFrame([p.to_dict() for p in players]).sort_values('mmr', ascending=False).drop_duplicates(subset='name', inplace=False).to_dict('records'))


    @slash_command(
        name='vote',
        description='Start voting',
        description_localizations = {'ja':'参加アンケートを開始'}
    )
    @commands.guild_only()
    async def start_voting(
        self,
        ctx: ApplicationContext,
        enemy: Option(
            str,
            name = 'enemy',
            name_localizations = {'ja':'チーム名'},
            description = 'enemy name',
            description_localizations = {'ja':'相手チームの名前'}
        ),
        role: Option(
            Role,
            name = 'role',
            name_localizations = {'ja':'ロール'},
            description = 'target',
            description_localizations = {'ja':'アンケートの対象'}
        ),
        date: Option(
            str,
            name = 'datetime',
            name_localizations = {'ja':'日時'},
            description = 'datetime (only hour is also available.)',
            description_localizations = {'ja':'試合の日時(時刻だけも可能)'},
            default = ''
        )
        ) -> None:
        await ctx.response.defer()
        lineup = '> ' + ', '.join([str(m) for m in role.members])

        if len(lineup) > 1024:
            raise TooManyPlayers

        try:
            await Vote.start(ctx.interaction, enemy=enemy, role=role, dt=get_dt(date), lang=ctx.interaction.locale)
        except ValueError:
            raise InvalidDatetime

    @team.command(
        name = 'mmr',
        description = 'Average MMR',
        description_localizations = {'ja':'チームの平均MMRを計算'}
    )
    @commands.guild_only()
    async def team_mmr(
        self,
        ctx: ApplicationContext,
        role: Option(
            Role,
            name = 'role',
            name_localizations = {'ja':'ロール'}
            )
    ) -> None:
        await ctx.response.defer()
        df = pd.DataFrame([p.to_dict() for p in await Team.get_players(role)])
        average = df['mmr'].mean()

        if isnan(average):
            raise PlayerNotFound

        count = 0
        header= f'**Role**  {role.mention}\n'
        content = commands.Paginator(prefix='', suffix='')

        for player in from_records(df.to_dict('records')):
            if player.is_placement:
                continue
            else:
                count += 1
                content.add_line(f'{str(count).rjust(3)}: [{player.name}]({player.lounge_url}) ({int(player.mmr)})')

        embeds = [LoungeEmbed(
            mmr=average,
            title=f'Team MMR: {average:.1f}',
            description=header+p
        ) for p in content.pages]
        is_compact = len(embeds) == 1

        await pages.Paginator(
            pages=embeds,
            show_disabled=not is_compact,
            show_indicator=not is_compact,
            author_check=False
            ).respond(ctx.interaction)


    @team.command(
        name = 'peak_mmr',
        description = 'Average Peak MMR',
        description_localizations = {'ja':'チームの平均Peak MMRを計算'}
    )
    @commands.guild_only()
    async def team_peak_mmr(
        self,
        ctx: ApplicationContext,
        role: Option(
            Role,
            name = 'role',
            name_localizations = {'ja':'ロール'}
        )
    ) -> None:
        await ctx.response.defer()
        players = await get_players_by_ids([m.id for m in role.members])

        if not any(map(lambda x: x.is_rich, players)):
            raise PlayerNotFound

        df = pd.DataFrame([p.to_dict() for p in players]).sort_values('max_mmr', ascending=False).drop_duplicates(subset='name', inplace=False)
        average = df['max_mmr'].mean()
        count = 0
        header= f'**Role**  {role.mention}\n'
        content = commands.Paginator(prefix='', suffix='')

        for player in from_records(df.to_dict('records')):
            if not player.is_rich:
                continue
            else:
                count += 1
                content.add_line(f'{str(count).rjust(3)}: [{player.name}]({player.lounge_url}) ({int(player.max_mmr)})')

        embeds = [LoungeEmbed(
            mmr=average,
            title=f'Team MMR: {average:.1f}',
            description=header+p
        ) for p in content.pages]
        is_compact = len(embeds) == 1

        await pages.Paginator(
            pages=embeds,
            show_disabled=not is_compact,
            show_indicator=not is_compact,
            author_check=False
            ).respond(ctx.interaction)


    @team.command(
        name = 'mkc',
        description ='Show mkc website url',
        description_localizations ={'ja':'MKCサイトのリンク'}
    )
    @commands.guild_only()
    async def team_mkc(
        self,
        ctx: ApplicationContext,
        role: Option(
            Role,
            name = 'role',
            name_localizations = {'ja':'ロール'}
        )
    ) -> None:
        await ctx.response.defer()
        count = 0
        header= f'**Role**  {role.mention}\n'
        content = commands.Paginator(prefix='', suffix='')

        for player in await Team.get_players(role):

            if player.is_empty:
                continue

            count += 1
            content.add_line(f'{str(count).rjust(3)}: [{player.name}]({player.mkc_url})  {"("+player.switch_fc+")" if player.switch_fc else ""}')

        embeds=[MyEmbed(
            title='MKC Registry',
            description=header+p
        ) for p in content.pages]
        is_compact = len(embeds) == 1
        await pages.Paginator(
            pages=embeds,
            show_disabled=not is_compact,
            show_indicator=not is_compact,
            author_check=False
            ).respond(ctx.interaction)


    @name.command(
        name = 'set',
        description = 'Set team name',
        description_localizations = {'ja':'チーム名を登録'}
    )
    @commands.guild_only()
    async def team_name_set(
        self,
        ctx: ApplicationContext,
        name: Option(
            str,
            name = 'name',
            name_localizations = {'ja':'チーム名'},
            required = True
        )
    ) -> None:
        await ctx.response.defer()
        await set_team_name(ctx.guild_id, name)
        await ctx.respond({'ja':f'チーム名を登録しました  **{name}**'}.get(ctx.locale, f'Set team name **{name}**'))
        return


    @commands.command(
        name='mset',
        description = 'Set team name',
        brief = 'チーム名を登録',
        usage = '!mset  <guild_id> <team_name>',
        hidden = True
    )
    @commands.is_owner()
    async def mset(self, ctx: commands.Context, guild_id: int, *, team_name: str) -> None:
        await set_team_name(guild_id, team_name)
        await ctx.send(f'{guild_id}のチーム名を{team_name}へ変更しました。')
        return


    @name.command(
        name = 'reset',
        description = 'Reset team name',
        description_localizations = {'ja':'チーム名をリセット'}
    )
    @commands.guild_only()
    async def team_name_reset(self, ctx: ApplicationContext) -> None:
        await ctx.response.defer()
        await set_team_name(ctx.guild_id, ctx.guild.name)
        await ctx.respond({'ja':f'{ctx.guild.name}へリセットしました。'}.get(ctx.locale, f'Reset team name to default {ctx.guild.name}'))
        return


    @name.command(
        name = 'show',
        description = 'Show team name',
        description_localizations = {'ja': '登録されているチーム名を表示'}
    )
    @commands.guild_only()
    async def team_name_show(self, ctx: ApplicationContext) -> None:
        await ctx.response.defer()
        await ctx.respond(await get_team_name(ctx.guild_id) or ctx.guild.name)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Team(bot))
