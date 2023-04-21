from discord.ext import commands
from discord import (
    File,
    Guild,
    Option,
    Attachment,
    SlashCommandGroup,
    ApplicationContext
)
from discord.utils import format_dt
from io import BytesIO
import pandas as pd
from team.errors import InvalidDatetime

from .errors import *
from .components import ResultPaginator, WinOrLose
from .plotting import result_graph as plot_result

from common.utils import (
    get_team_name,
    get_results,
    post_result,
    overwrite_results,
    get_dt,
    get_integers
)



class Result(commands.Cog, name = 'Result'):

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.hide: bool = False
        self.description: str = 'Manage Results'
        self.description_localizations: dict[str, str] = {'ja':'戦績管理'}


    result = SlashCommandGroup(name = 'result')
    data = result.create_subgroup(name = 'data')

    @staticmethod
    async def get(guild_id: int) -> pd.DataFrame:
        data =await get_results(guild_id)

        if data:
            df = pd.DataFrame(data)
            df = df.copy()
            df['date'] = pd.to_datetime(df['date'], infer_datetime_format=True)
            return df.sort_values(by='date', ascending=True).reset_index(drop=True)

        raise EmptyResult


    @staticmethod
    async def post_df(guild_id: int, df: pd.DataFrame) -> None:
        df['date'] = df['date'].astype(dtype='str')
        await overwrite_results(guild_id, df.to_dict('records'))


    @staticmethod
    async def export_file(guild: Guild) -> File:
        data = await get_results(guild.id)
        name = await get_team_name(guild.id) or guild.name

        if not data:
            raise EmptyResult

        df = pd.DataFrame(data)
        df.insert(0, 'team', name)
        buffer = BytesIO()
        df.to_csv(
            buffer,
            header=False,
            index=False,
            columns=['team', 'score', 'enemyScore', 'enemy', 'date']
        )
        buffer.seek(0)
        return File(buffer, filename='results.csv')


    @result.command(
        name = 'list',
        description = 'Show all results',
        description_localizations = {'ja': '戦績を全て表示'}
    )
    @commands.guild_only()
    async def result_list(self, ctx: ApplicationContext) -> None:
        await ctx.response.defer()
        df =  await Result.get(ctx.guild_id)
        df['formatted_scores'] = df['score'].astype(str) + ' - ' + df['enemyScore'].astype(str)
        df['diff'] = df['score'] - df['enemyScore']
        lines = df.to_string(
            columns = ['formatted_scores', 'enemy', 'diff'],
            formatters = {'diff': WinOrLose},
            header = ['Scores', 'Enemy', 'Result'],
            justify = 'center'
        ).split('\n')
        win, lose, draw = len(df[df['diff']>0]), len(df[df['diff']<0]), len(df[df['diff']==0])
        await ResultPaginator(
            header=lines[0],
            contents=lines[1:],
            footer=f'__**Win**__:  {win}  __**Lose**__:  {lose}  __**Draw**__:  {draw}  [{len(df)}]'
        ).respond(ctx.interaction)


    @result.command(
        name = 'search',
        description = 'Search results by team name',
        description_localizations = {'ja': 'チーム名で対戦履歴を検索'}
    )
    @commands.guild_only()
    async def result_search(
        self,
        ctx: ApplicationContext,
        name: Option(
            str,
            name = 'enemy',
            name_localizations = {'ja': '相手チーム名'},
            description = 'Enemy team name',
            description_localizations = {'ja': '検索するチーム名'}
        )
    ) -> None:
        await ctx.response.defer()
        d = await Result.get(ctx.guild_id)
        df = d.query(f'enemy=="{name}"').copy()

        if len(df) == 0:
            prefix = name[0].lower()
            lineup = ', '.join([n for n in d['enemy'].unique().tolist() if n[0].lower() == prefix])

            if lineup == '':
                raise EmptyResult
            else:
                raise NotMatched(
                    content={'ja': f'戦績が見つかりませんでした。\n類似した名前:  {lineup}'},
                    default=f'Result not found.\nSimilar name:  {lineup}'
                )

        df['formatted_scores'] = df['score'].astype(str) + ' - ' + df['enemyScore'].astype(str)
        df['diff'] = df['score'] - df['enemyScore']
        df['date']=df['date'].dt.strftime('%Y/%m/%d').copy()
        lines = df.to_string(
            columns = ['date', 'formatted_scores', 'diff'],
            formatters = {'diff': WinOrLose},
            header = ['Date', 'Scores', 'Result'],
            justify = 'center'
        ).split('\n')
        win, lose, draw = len(df[df['diff']>0]), len(df[df['diff']<0]), len(df[df['diff']==0])
        await ResultPaginator(
            title = f'vs.  **{name}**',
            header = lines[0],
            contents= lines[1:],
            footer = f'__**Win**__:  {win}  __**Lose**__:  {lose}  __**Draw**__:  {draw}  [{len(df)}]'
        ).respond(ctx.interaction)


    @result.command(
        name = 'graph',
        description = 'Show result graph',
        description_localizations = {'ja': '戦績グラフを表示'}
    )
    @commands.guild_only()
    async def app_result_graph(self, ctx: ApplicationContext) -> None:
        await ctx.response.defer()
        buffer = plot_result(await Result.get(ctx.guild_id))
        await ctx.respond(file=File(buffer, 'results.png'))


    @commands.command(
        name = 'graph',
        description = 'Show result graph',
        brief = '戦績グラフを表示',
        usage = '!graph',
        hidden = False
    )
    @commands.guild_only()
    async def command_result_graph(self, ctx: commands.Context) -> None:
        buffer = plot_result(await Result.get(ctx.guild.id))
        await ctx.send(file=File(buffer, 'results.png'))


    @result.command(
        name = 'register',
        description = 'Register result',
        description_localizations = {'ja': '戦績を登録'}
    )
    @commands.guild_only()
    async def result_register(
        self,
        ctx: ApplicationContext,
        name: Option(
            str,
            name = 'enemy',
            name_localizations = {'ja': 'チーム名'},
            description = 'Enemy name',
            description_localizations = {'ja': '相手チームの名前'}
        ),
        scores: Option(
            str,
            name = 'scores',
            name_localizations = {'ja': '得点'},
            description = 'TeamScore (EnemyScore)',
            description_localizations = {'ja': '自チームの得点  (相手の得点)'}
        ),
        date: Option(
            str,
            name = 'datetime',
            name_localizations = {'ja': '日時'},
            description = '[year] [month] [day] [hour]',
            description_localizations = {'ja': '[年] [月] [時]'},
            default = ''
        )
    ) -> None:
        await ctx.response.defer()

        try:
            payload = {'enemy': name, 'date': get_dt(date, ctx.locale).strftime('%Y-%m-%d %H:%M:%S')}
        except ValueError:
            raise InvalidDatetime

        numbers = get_integers(scores)

        if len(numbers) == 1:
            payload['score'] = numbers[0]
            payload['enemyScore'] = 984-numbers[0]
        elif len(numbers) >= 2:
            payload['score'] = numbers[0]
            payload['enemyScore'] = numbers[1]
        else:
            raise InvalidScoreInput

        await post_result(ctx.guild_id, **payload)
        msg = f"vs {name}  `{payload['score']} - {payload['enemyScore']}` **{WinOrLose(payload['score']-payload['enemyScore'])}**"
        await ctx.respond({'ja': f'戦績を登録しました。\n{msg}'}.get(ctx.locale, f'Registered\n{msg}'))


    @result.command(
        name = 'delete',
        description = 'Delete results.',
        description_localizations = {'ja': '戦績を削除'},
    )
    @commands.guild_only()
    async def result_delete(
        self,
        ctx: ApplicationContext,
        id: Option(
            str,
            name = 'id',
            description = 'ID (multiple available)',
            description_localizations = {'ja': '削除する戦績のID (複数可)'},
            default = '-1'
        )
    ) -> None:
        await ctx.defer()
        df = await Result.get(ctx.guild_id)
        ids: list[int] = sorted(get_integers(id))

        if not ids:
            raise InvalidIdInput

        try:
            dropped = df.iloc[ids].copy()
        except IndexError:
            raise IdOutOfRange

        dropped['date'] = dropped['date'].dt.strftime('%Y/%m/%d').copy()
        df.drop(
            index = df.index[ids],
            errors = 'raise',
            inplace = True
        )
        dropped['formatted_scores'] = dropped['score'].astype(str) + ' - ' + dropped['enemyScore'].astype(str)
        await Result.post_df(ctx.guild_id, df)
        lines = dropped.to_string(
            columns = ['enemy', 'formatted_scores', 'date'],
            header = ['Enemy', 'Scores', 'Date'],
            justify = 'center'
        ).split('\n')
        await ResultPaginator(
            title = {'ja': '戦績を削除しました。'}.get(ctx.locale, 'Successfully deleted.'),
            header=lines[0],
            contents=lines[1:]
        ).respond(ctx.interaction)


    @result.command(
        name = 'edit',
        description = 'Edit result',
        description_localizations = {'ja': '戦績を編集'}
    )
    @commands.guild_only()
    async def result_edit(
        self,
        ctx: ApplicationContext,
        id: Option(
            int,
            name = 'id',
            description = 'Result ID',
            description_localizations = {'ja': '編集する戦績のID'},
            min_value = 0
        ),
        enemy: Option(
            str,
            name = 'enemy',
            name_localizations = {'ja': 'チーム名'},
            description = 'Enemy name',
            description_localizations = {'ja': '相手チームの名前'},
            default = None
        ),
        scores: Option(
            str,
            name = 'scores',
            name_localizations = {'ja': '得点'},
            description = 'TeamScore (EnemyScore)',
            description_localizations = {'ja': '自チームの得点  (相手の得点)'},
            default = None
        ),
        date: Option(
            str,
            name = 'datetime',
            name_localizations = {'ja': '日時'},
            description = '[year] [month] [day] [hour]',
            description_localizations = {'ja': '[年] [月] [時]'},
            default = None
        )
    ) -> None:
        await ctx.response.defer()
        df = await Result.get(ctx.guild_id)

        try:
            payload: dict = df.to_dict('records')[id].copy()
        except IndexError:
            raise IdOutOfRange

        if scores is not None:
            numbers = get_integers(scores)

            if not 1<= len(numbers) <=2:
                raise InvalidScoreInput

            if len(numbers) >= 1:
                payload['score'] = numbers[0]
            if len(numbers) == 2:
                payload['enemyScore'] = numbers[1]

        if date is not None:
            try:
                payload['date'] = get_dt(date, ctx.locale)
            except ValueError:
                raise InvalidDatetime
        if enemy is not None:
            payload['enemy'] = enemy

        df.loc[id] = payload.copy()
        await Result.post_df(ctx.guild_id, df)
        msg = {'ja': '戦績を編集しました。\n'}.get(ctx.locale, 'Successfully edited result\n')
        await ctx.respond(msg+f"`{id}` {payload['score']} - {payload['enemyScore']} vs.**{payload['enemy']}** {format_dt(payload['date'],'F')}")


    @data.command(
        name = 'export',
        description = 'Export result data',
        description_localizations = {'ja': '保存された戦績ファイルを出力'}
    )
    @commands.guild_only()
    async def result_data_export(self, ctx: ApplicationContext) -> None:
        await ctx.response.defer()
        await ctx.respond(
            {'ja':'ファイルを送信しました。'}.get(ctx.locale, 'Sent result file.'),
            file = await Result.export_file(ctx.guild)
        )
        return


    @data.command(
        name = 'load',
        description = 'Load result file and overwrite',
        description_localizations = {'ja': '戦績ファイルを読み込んで上書き'}
    )
    @commands.guild_only()
    async def result_data_load(
        self,
        ctx: ApplicationContext,
        file: Option(
            Attachment,
            name = 'csv',
            name_localizations = {'ja': 'csvファイル'},
            description = 'File to load',
            description_localizations = {'ja': '戦績が書き込まれたファイル'}
        )
    ) -> None:
        await ctx.response.defer()

        if not file.filename.endswith('.csv'):
            raise NotCSVFile

        buffer = BytesIO()
        await file.save(buffer)

        try:
            df = pd.read_csv(buffer, skipinitialspace=True, header=None).loc[:,[1,2,3,4]]
            df.columns = ['score','enemyScore','enemy','date']
            df = df.copy()
            df['date'] = pd.to_datetime(df['date'], infer_datetime_format = True)
            df.sort_values(by = 'date', ascending = True, inplace = False)
            await Result.post_df(ctx.guild_id, df)
        except Exception:
            raise NotAcceptableContent

        await ctx.respond({'ja':'戦績ファイルを読み込みました。'}.get(ctx.locale, 'Loaded result file.'))


    @commands.command(
        name = 'mload',
        description = 'Load result file and overwrite',
        brief = '戦績ファイルを読み込んで上書き',
        usage = '!mload <csv file>',
        hidden = True
    )
    @commands.is_owner()
    async def mload(
        self,
        ctx: commands.Context,
    ) -> None:

        try:
            attachment = ctx.message.attachments[0]
            guild_id = get_integers(attachment.filename)[0]
        except:
            raise commands.BadArgument

        if not attachment.filename.endswith('csv'):
            raise NotCSVFile

        try:
            guild = self.bot.get_guild(guild_id)
            f = await Result.export_file(guild)
            f.filename = f'{guild.id}.csv'
            await ctx.send(content='上書き前のファイル',file=f)
        except (EmptyResult, AttributeError):
            pass

        buffer = BytesIO()
        await attachment.save(buffer)

        try:
            df = pd.read_csv(buffer, skipinitialspace=True, header=None).loc[:,[1,2,3,4]]
            df.columns = ['score','enemyScore','enemy','date']
            df = df.copy()
            df['date'] = pd.to_datetime(df['date'], infer_datetime_format = True)
            df.sort_values(by = 'date', ascending = True, inplace = False)
            await Result.post_df(guild_id, df)
        except Exception:
            raise NotAcceptableContent

        await ctx.send(f'{guild_id}のデータを上書きしました。')


    @commands.command(
        name = 'mexport',
        aliases = ['me'],
        description = 'Export result file',
        brief = '戦績ファイルを出力',
        usage = '!mexport <guild_id>',
        hidden = True
    )
    @commands.is_owner()
    async def mexport(self, ctx: commands.Context, guild_id: int) -> None:

        if (guild := self.bot.get_guild(guild_id)) is not None:
            f =  await Result.export_file(guild)
            f.filename = f'{guild.id}.csv'
            await ctx.send(
                f'{guild.name}({guild.id})のファイルを出力します。',
                file = f
            )
        else:
            await ctx.send('存在しないサーバーです。')
            return


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Result(bot))