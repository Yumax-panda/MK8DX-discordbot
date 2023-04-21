from typing import Optional, Union
from datetime import timedelta
from copy import copy
from discord.ext import commands
from discord import (
    Role,
    Member,
    Option,
    Message,
    OptionChoice,
    message_command,
    SlashCommandGroup,
    ApplicationContext,
)
from .errors import *
from .components import Mogi

from objects import Rank, Race, Track
from common.utils import get_team_name, post_result
from common.timezones import TZ

ContextLike = Union[commands.Context, ApplicationContext]


class Sokuji(commands.Cog, name='Sokuji'):

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.hide: bool = False
        self.description: str = 'About Sokuji'
        self.description_localizations: dict[str, str] = {'ja':'即時関連'}


    mogi = SlashCommandGroup(name='mogi')
    race = mogi.create_subgroup(name='race')
    penalty = mogi.create_subgroup(name='penalty')
    banner = mogi.create_subgroup('banner', 'Banner')


    @message_command(name='Register Result')
    @commands.guild_only()
    async def register_result(
        self,
        ctx: ApplicationContext,
        message: Message
    ) -> None:
        await ctx.response.defer()

        if Mogi.is_readable(message):
            m = Mogi().convert(message)
            now = message.created_at + timedelta(hours=TZ.from_locale(ctx.locale).offset)
            payload = {
                'enemy': m.tags[1],
                'score': m.total[0],
                'enemyScore':m.total[1],
                'date': now.strftime('%Y-%m-%d %H:%M:%S')
            }
            await post_result(ctx.guild_id, **payload)
            content = f'{m.tags[0]} vs {m.tags[1]}\n`{Mogi.score_to_string(m.total)}`'
            await ctx.respond(('戦績を登録しました。\n'if m.is_ja else 'Result registered.\n') + content)
        else:
            raise InvalidMessage


    @staticmethod
    async def start(ctx: ContextLike, tag: str, role: Optional[Role]=None) -> None:
        name = await get_team_name(ctx.guild.id) or ctx.guild.name
        mogi = Mogi(tags=[name, tag])
        flag = isinstance(ctx, commands.Context)

        if role is not None:
            mogi.banner_users = {f'{m.name}{m.discriminator}' for m in role.members}
            if flag:
                await ctx.send(embed=await mogi.updater_lineup())
            else:
                await ctx.respond(embed=await mogi.updater_lineup())

        if flag:
            await ctx.send(embed=mogi.embed)
        else:
            mogi.is_ja = ctx.locale == 'ja'
            await ctx.respond(embed=mogi.embed)
        return


    @mogi.command(
        name = 'start',
        description = 'Start Mogi',
        description_localizations = {'ja':'即時集計の開始'}
    )
    @commands.guild_only()
    async def mogi_start(
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
            description = 'Member role',
            description_localizations = {'ja':'参加メンバーのロール'},
            default = None
        )
        ) -> None:
        await ctx.response.defer()
        await Sokuji.start(ctx, enemy, role)


    @commands.command(
        name='mogi',
        aliases=['sokuji', 'v', 'vs', 'start'],
        description='Start Mogi.',
        brief='即時集計の開始',
        usage='!v [@role] <enemy>',
        hidden=False
    )
    @commands.guild_only()
    async def text_mogi_start(
        self,
        ctx: commands.Context,
        role: Optional[Role] = None,
        *,
        tag: str
        ) -> None:
        await Sokuji.start(ctx, tag, role)


    @staticmethod
    async def end(ctx: ContextLike) -> None:
        sokuji = await Mogi.get(ctx.channel)
        sokuji.is_archive = True
        await sokuji.refresh()

        if isinstance(ctx, commands.Context):
            await ctx.send('即時を終了しました。' if sokuji.is_ja else 'Finished sokuji.')
        else:
            await ctx.respond('即時を終了しました。' if sokuji.is_ja else 'Finished sokuji.')

        return


    @mogi.command(
        name = 'end',
        description = 'End mogi.',
        description_localizations = {'ja':'即時を終了'}
    )
    @commands.guild_only()
    async def mogi_end(self, ctx: ApplicationContext) -> None:
        await ctx.response.defer()
        await Sokuji.end(ctx)


    @commands.command(
        name='end',
        aliases=['e'],
        description='End Mogi.',
        brief='即時を終了',
        usage='!e',
        hidden=False
    )
    @commands.guild_only()
    async def text_mogi_end(self, ctx: commands.Context) -> None:
        await Sokuji.end(ctx)


    @staticmethod
    async def resume(ctx: ContextLike) -> None:
        sokuji = await Mogi.get(ctx.channel, True)
        sokuji.is_archive = False
        await sokuji.refresh()

        if isinstance(ctx, commands.Context):
            await ctx.send('即時を再開します。' if sokuji.is_ja else 'Resumed sokuji.')
        else:
            await ctx.respond('即時を再開します。' if sokuji.is_ja else 'Resumed sokuji.')
        return


    @mogi.command(
        name = 'resume',
        description = 'Resume sokuji.',
        description_localizations = {'ja':'即時を再開'}
    )
    @commands.guild_only()
    async def mogi_resume(self, ctx: ApplicationContext) -> None:
        await ctx.response.defer()
        await Sokuji.resume(ctx)


    @commands.command(
        name='resume',
        aliases = ['re'],
        description=' Resume sokuji.',
        brief='即時を再開',
        usage='!resume',
        hidden=False
    )
    @commands.guild_only()
    async def text_mogi_resume(self, ctx: commands.Context) -> None:
        await Sokuji.resume(ctx)


    @mogi.command(
        name = 'edit',
        description = 'Edit sokuji setting',
        description_localizations = {'ja': '即時の設定を変更'}
    )
    @commands.guild_only()
    async def mogi_edit(
        self,
        ctx: ApplicationContext,
        enemy: Option(
            str,
            name = 'enemy',
            name_localizations = {'ja':'チーム名'},
            description = 'enemy name',
            description_localizations = {'ja':'相手チームの名前'},
            default = None
        ),
        role: Option(
            Role,
            name = 'role',
            name_localizations = {'ja':'ロール'},
            description = 'Member role',
            description_localizations = {'ja':'参加メンバーのロール'},
            default = None
        ),
        locale: Option(
            str,
            name = 'language',
            name_localizations = {'ja': '言語'},
            choices = [
                OptionChoice(name='Japanese', value='ja', name_localizations={'ja': '日本語'}),
                OptionChoice(name='English', value='en', name_localizations={'ja': '英語'})
            ],
            default = None
        )
    ) -> None:
        await ctx.response.defer()
        payload = {}
        sokuji = await Mogi.get(ctx.channel)
        sokuji.tags[1] = enemy or sokuji.tags[1]

        if role is not None:
            sokuji.banner_users = {f'{m.name}{m.discriminator}' for m in role.members}
            payload['embed'] = (await sokuji.updater_lineup()).copy()

        if locale is not None:
            sokuji.is_ja = locale == 'ja'

        await sokuji.refresh()
        payload['content'] = '即時を編集しました。' if sokuji.is_ja else 'Edited sokuji.'
        await ctx.respond(**payload)


    @race.command(
        name='add',
        description = 'Add race.',
        description_localizations = {'ja':'即時にレースを追加'}
    )
    @commands.guild_only()
    async def mogi_race_add(
        self,
        ctx: ApplicationContext,
        rank: Option(
            str,
            name = 'rank',
            name_localizations = {'ja':'順位'},
            description='Enter without space.',
            description_localizations={'ja': '空白なしで入力'}
        ),
        track: Option(
            str,
            name = 'track',
            name_localizations = {'ja':'コース名'},
            default = None,
            required = False
        ),
        race_num: Option(
            int,
            name = 'race_num',
            name_localizations = {'ja':'レース番号'},
            description= 'If not given, add to last.',
            description_localizations = {'ja':'省略した場合、最後に追加'},
            min_value = 1,
            max_value = 12,
            default = None,
            required = False
        )
    ) -> None:
        await ctx.response.defer()
        sokuji = await Mogi.get(ctx.channel)
        await sokuji.add_race(rank, track, race_num)
        await sokuji.send(ctx.channel)
        await ctx.respond('レースを追加しました。' if sokuji.is_ja else 'Added race.')


    @commands.command(
        name = 'tag',
        description='Change tag',
        brief='タグを変更',
        usage='!tag <name>',
        hidden=False
    )
    @commands.guild_only()
    async def change_tag(self, ctx: commands.Context, *, name: str) -> None:
        sokuji = await Mogi.get(ctx.channel)
        sokuji.tags[-1] = name
        await sokuji.refresh()
        await sokuji.update_obs()
        await ctx.send(f'タグを**{name}**へ変更しました。' if sokuji.is_ja else f'Changed tag **{name}**.')
        return


    @race.command(
        name = 'delete',
        description = 'Delete race.',
        description_localizations = {'ja': 'レースを削除'}
    )
    @commands.guild_only()
    async def mogi_race_delete(
        self,
        ctx: ApplicationContext,
        race_num: Option(
            int,
            name = 'race_num',
            name_localizations = {'ja': 'レース番号'},
            description='If not given, delete the last race.',
            description_localizations = {'ja': '指定しない場合、最後のレースを削除'},
            min_value = 1,
            max_value = 12,
            default = 0,
            required = False
        )
    ) -> None:
        await ctx.response.defer()
        sokuji = await Mogi.get(ctx.channel)
        await sokuji.back(race_num-1)
        await sokuji.refresh()
        await ctx.respond('レースを削除しました。' if sokuji.is_ja else 'Deleted race.')


    @race.command(
        name='edit',
        description = 'Edit race',
        description_localizations = {'ja': 'レースを編集'}
    )
    @commands.guild_only()
    async def mogi_race_edit(
        self,
        ctx: ApplicationContext,
        rank: Option(
            str,
            name = 'rank',
            name_localizations = {'ja':'順位'},
            description='Enter without space.',
            description_localizations={'ja': '空白なしで入力'},
            default = None,
            required = False
        ),
        track: Option(
            str,
            name = 'track',
            name_localizations = {'ja':'コース名'},
            default = '',
            required = False
        ),
        race_num: Option(
            int,
            name = 'race_num',
            name_localizations = {'ja':'レース番号'},
            description= 'If not given, edit the last race.',
            description_localizations = {'ja':'省略した場合、最後のレースを編集'},
            min_value = 1,
            max_value = 12,
            default = 0,
            required = False
        )
    ) -> None:
        await ctx.response.defer()
        sokuji = await Mogi.get(ctx.channel)

        try:
            old_race: Race = copy(sokuji.races[race_num-1])
            sokuji.races[race_num-1] = Race(
                Rank.get_ranks(rank) if rank is not None else old_race.ranks,
                Track.from_nick(track) or old_race.track
            )
        except IndexError:
            raise OutOfRange

        await sokuji.update_obs()
        await sokuji.refresh()
        await ctx.respond('レースを編集しました。' if sokuji.is_ja else 'Edited race.')


    @staticmethod
    async def send_banner_url(ctx: ContextLike, members: set[Member]) -> None:
        sokuji = await Mogi.get(ctx.channel)
        new_users = {f'{member.name}{member.discriminator}' for member in members}
        sokuji.banner_users |= new_users
        await sokuji.refresh()
        await sokuji.update_obs()

        if isinstance(ctx, commands.Context):
            await ctx.send(embed=Mogi.banner_embed(new_users))
        else:
            await ctx.respond(embed=Mogi.banner_embed(new_users))


    @banner.command(
        name='add',
        description='URL for OBS',
        description_localizations={'ja': 'OBS用のバナーURL'}
    )
    @commands.guild_only()
    async def mogi_banner_add(
        self,
        ctx: ApplicationContext,
        member: Option(
            Member,
            name='user',
            name_localizations={'ja': 'ユーザー'},
            description='If not given, adds you to banner users.',
            description_localizations={'ja': '指定がない場合、コマンド使用者を追加'},
            default = None,
        ),
        role: Option(
            Role,
            name='role',
            name_localizations={'ja': 'ロール'},
            description='If given, adds members to banner users.',
            description_localizations={'ja': '指定したロールのメンバーを追加'},
            default = None,
        )
    ) -> None:
        await ctx.response.defer()
        members = {member} if member is not None else {ctx.user}

        if role is not None:
            members.update(role.members)

        await Sokuji.send_banner_url(ctx, members=members)


    @commands.command(
        name='add',
        aliases=['banner', 'o', 'obs'],
        description='Send URL for OBS.',
        brief='バナーの更新を開始',
        usage='!o [@member, ...]',
        hidden=False
    )
    @commands.guild_only()
    async def text_mogi_banner_add(
        self,
        ctx: commands.Context,
        members: commands.Greedy[Member] = []
    ) -> None:
        await Sokuji.send_banner_url(ctx, members=set(members) if members  else {ctx.author})


    @staticmethod
    async def remove_banner_user(ctx: ContextLike, members: set[Member]) -> None:
        sokuji = await Mogi.get(ctx.channel)

        sokuji.banner_users -= {f'{member.name}{member.discriminator}' for member in members}
        await sokuji.update_obs()
        await sokuji.refresh()

        if isinstance(ctx, commands.Context):
            await ctx.send('バナーの更新を停止しました。' if sokuji.is_ja else 'Finished updating banner.')
        else:
            await ctx.respond('バナーの更新を停止しました。' if sokuji.is_ja else 'Finished updating banner.')

        return


    @banner.command(
        name='remove',
        description='Remove banner user',
        description_localizations={'ja': 'バナーの更新を終了'}
    )
    @commands.guild_only()
    async def mogi_banner_remove(
        self,
        ctx: ApplicationContext,
        member: Option(
            Member,
            name='user',
            name_localizations={'ja': 'ユーザー'},
            description='If not given, removes you from banner users.',
            description_localizations={'ja': '指定がない場合、コマンド使用者を削除'},
            default = None,
        ),
        role: Option(
            Role,
            name='role',
            name_localizations={'ja': 'ロール'},
            description='If given, removes members from banner users.',
            description_localizations={'ja': '指定したロールのメンバーを削除'},
            default = None,
        )
    ) -> None:
        await ctx.response.defer()
        members = {member} if member is not None else {ctx.user}

        if role is not None:
            members.update(role.members)

        await Sokuji.remove_banner_user(ctx, members=members)


    @commands.command(
        name='removeBanner',
        aliases=['rb', 'removeobs', 'ro'],
        description='Remove banner user',
        brief='バナーの更新を終了',
        usage='!ro [@member, ...]',
        hidden=False
    )
    @commands.guild_only()
    async def text_mogi_banner_remove(
        self,
        ctx: commands.Context,
        members: commands.Greedy[Member] = []
    ) -> None:
        await Sokuji.remove_banner_user(ctx, members=set(members) if members else {ctx.author})


    @penalty.command(
        name='add',
        description='Add penalty',
        description_localizations = {'ja': '即時にペナルティを追加'}
    )
    @commands.guild_only()
    async def mogi_penalty_add(
        self,
        ctx: ApplicationContext,
        type: Option(
            str,
            name='type',
            name_localizations = {'ja': '種類'},
            description= 'If not given, add repick.',
            description_localizations ={'ja': '選択しない場合はリピック'},
            choices = [
                OptionChoice(name='Repick', value='repick', name_localizations = {'ja': 'リピック'}),
                OptionChoice(name='Penalty', value='penalty', name_localizations = {'ja': 'ペナルティ'})
            ],
            default = 'repick',
            required = False
        ),
        index : Option(
            int,
            name = 'target',
            name_localizations = {'ja': 'チーム'},
            description = 'Team  to add penalty. (default to your team)',
            description_localizations = {'ja': 'ペナルティを追加するチーム(デフォルトは自チーム)'},
            choices = [
                OptionChoice(name='Your team', name_localizations = {'ja':'自チーム'}, value = 0),
                OptionChoice(name='Enemy', name_localizations = {'ja':'敵チーム'}, value = 1)
            ],
            default = 0,
            required = False
        ),
        amount: Option(
            int,
            name = 'amount',
            name_localizations = {'ja': 'ポイント'},
            description= 'default to -15pt.',
            description_localizations = {'ja': '指定しない場合は-15ポイント'},
            default = -15,
            required = False
        )
    ) -> None:
        await ctx.response.defer()
        sokuji = await Mogi.get(ctx.channel)

        if type == 'repick':
            sokuji.repick[index] += amount
        else:
            sokuji.penalty[index] += amount

        await sokuji.refresh()
        await sokuji.update_obs()
        await ctx.respond('ペナルティを追加しました。' if sokuji.is_ja else 'Added penalty.')


    @penalty.command(
        name='clear',
        description='Clear penalty',
        description_localizations = {'ja': 'ペナルティを削除'}
    )
    @commands.guild_only()
    async def mogi_penalty_clear(
        self,
        ctx: ApplicationContext,
        type: Option(
            str,
            name='type',
            name_localizations = {'ja': '種類'},
            description= 'If not given, add repick.',
            description_localizations ={'ja': '選択しない場合はリピック'},
            choices = [
                OptionChoice(name='Repick', value='repick', name_localizations = {'ja': 'リピック'}),
                OptionChoice(name='Penalty', value='penalty', name_localizations = {'ja': 'ペナルティ'})
            ],
            default = 'repick',
            required = False
        )
    ) -> None:
        await ctx.response.defer()
        sokuji = await Mogi.get(ctx.channel)
        setattr(sokuji, type, [0, 0])
        await sokuji.refresh()
        await sokuji.update_obs()
        await ctx.respond('ペナルティを削除しました。' if sokuji.is_ja else 'Cleared penalty.')


    @commands.Cog.listener('on_message')
    async def sokuji_update(self, message: Message) -> None:

        if message.author.bot or message.guild is None:
            return

        try:
            sokuji = await Mogi.get(message.channel)
            if message.content == 'back':
                await sokuji.back()
            else:
                await sokuji.add_race(message.content)
            await sokuji.send(message.channel)
            return
        except (MogiNotFound, MogiArchived, NotAddable, NotBackable, InvalidRankInput):
            return


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Sokuji(bot))
