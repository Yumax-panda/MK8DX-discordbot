from typing import Optional, Union, Literal, Callable, TypeVar
from discord.ext import commands
from discord.utils import get
from discord import (
    Role,
    Guild,
    Member,
    Option,
    Message,
    NotFound,
    Forbidden,
    TextChannel,
    OptionChoice,
    slash_command,
    ApplicationContext
)
import asyncio
import random
import re

T = TypeVar('T')

_INT_RE = re.compile(r'\d+')
_FLAG_RE = re.compile(r'[0-9]+-[0-9]+')

from common import MyEmbed, get_gather, post_gather, is_allowed_channel
from constants import MY_ID
from team.errors import PlayerNotFound

from .errors import *

ContextLike = Union[commands.Context, ApplicationContext]

def get_hours(txt: str) -> list[int]:
    integers: list[int] = list(map(int, _INT_RE.findall(txt)))
    sc_inputs: list[str] = _FLAG_RE.findall(txt)

    for sc in sc_inputs:
        nums = list(map(int, _INT_RE.findall(sc)))
        integers += list(range(nums[0], nums[-1]+1))

    integers = sorted(set(integers))

    if not integers:
        raise TimeNotSelected
    if len(integers) >= 26:
        raise TooManyHours

    return integers


def role_check(func) -> Callable[[T], T]:

    async def predicate(*args, **kwargs):

        try:
            await func(*args, **kwargs)
        except Forbidden:
            raise FailedToManageRole

    return predicate



async def get_prev_lineup(channel: TextChannel) -> Optional[Message]:

    async for message in channel.history(limit=20, oldest_first=False):
        try:
            if (
                message.author.id == MY_ID
                and '6v6 War List' in message.embeds[0].title
                and message.embeds[0].author.name != 'Archive'
            ):
                return message
            else:
                continue
        except:
            continue

    return None


async def delete_prev_lineup(channel: TextChannel) -> None:
    msg = await get_prev_lineup(channel)

    if msg is not None:
        try:
            await msg.delete()
        except NotFound:
            pass

    return


def make_lineup(data: dict) -> MyEmbed:

    if not data:
        raise NotGathering

    if len(data) >= 26:
        raise TooManyHours

    e = MyEmbed(title='**6v6 War List**')

    for hour in sorted(map(int, data.keys())):
        is_empty: bool = len(data[str(hour)]['c']) + len(data[str(hour)]['t']) == 0

        if is_empty:
            e.add_field(name=f'{hour}@6', value='> なし', inline=False)
            continue
        else:
            c = [f'<@{id}>' for id in data[str(hour)]['c']]
            t = [f'<@{id}>' for id in data[str(hour)]['t']]
            e.add_field(
                name = f'{hour}@{6-len(c)}' + (f'({len(t)})' if t else ''),
                value = f'> {",".join(c)}' + (f'({",".join(t)})' if t else ''),
                inline = False
            )

    return e


@role_check
async def set_hours(
    guild: Guild,
    hours: list[Union[str, int]],
    members: list[Member]
) -> None:
    roles: list[Role] = []

    try:
        for hour in hours:
            if (role := get(guild.roles, name=str(hour))) is None:
                role = await guild.create_role(name=str(hour), mentionable=True)
            roles.append(role)
    except Forbidden:
        raise FailedToManageRole

    await asyncio.gather(*[asyncio.create_task(member.add_roles(*roles)) for member in members])


@role_check
async def drop_hours(
    guild: Guild,
    hours: list[Union[str, int]],
    members: list[Member]
    ) -> None:
    roles: list[Role] = []

    for hour in hours:
        if (role := get(guild.roles, name=str(hour))) is None:
            continue
        roles.append(role)

    await asyncio.gather(*[asyncio.create_task(member.remove_roles(*roles)) for member in members])


@role_check
async def clear_hours(
    guild: Guild,
    hours: list[Union[str, int]],
) -> None:

    for hour in hours:
        if (role := get(guild.roles, name=str(hour))) is not None:
            await role.delete()
    return


async def participate(
    ctx: ContextLike,
    members: list[Member],
    action: Literal['c', 't'],
    hours_text: str
) -> None:
    hours = get_hours(hours_text)
    ids: list[int] = [m.id for m in members]
    filled_hours: list[str] = []
    data = await get_gather(ctx.guild.id)

    if len(hours) + len(data) > 26:
        raise TooManyHours

    x, y = 'c', 't'

    if action == 't':
        x, y = 't', 'c'

    for hour in hours:
        if (gathering := data.get(str(hour))) is None:
            data[str(hour)] = {x: ids.copy(), y: []}
        else:

            gathering[x] = list(set(gathering[x] + ids))
            gathering[y] = [n for n in gathering[y] if n not in ids]

        if len(data[str(hour)]['c']) >= 6 and action == 'c':
            filled_hours.append(str(hour))

    payload = {'embed': make_lineup(data)}

    if filled_hours:
        txt = ''
        for hour in filled_hours:
            txt += f'**{hour}** {", ".join(map(lambda x: f"<@{x}>", data[hour]["c"]))}\n'
        payload['content'] = txt

    await set_hours(ctx.guild, hours, members)
    await delete_prev_lineup(ctx.channel)
    await post_gather(ctx.guild.id, data)

    if isinstance(ctx, commands.Context):
        await ctx.send(**payload)
    else:
        await ctx.respond(**payload)


async def drop(
    ctx: ContextLike,
    members: list[Member],
    hours_text: str
) -> None:
    data = await get_gather(ctx.guild.id)
    hours = get_hours(hours_text)
    ids: list[int] = [m.id for m in members]

    for hour in hours:
        try:
            data[str(hour)]['c'] = [i for i in data[str(hour)]['c'].copy() if i not in ids]
            data[str(hour)]['t'] = [i for i in data[str(hour)]['t'].copy() if i not in ids]
        except KeyError:
            continue

    e = make_lineup(data)
    await drop_hours(ctx.guild, hours, members)
    await delete_prev_lineup(ctx.channel)
    await post_gather(ctx.guild.id, data)

    if isinstance(ctx, commands.Context):
        await ctx.send(embed=e)
    else:
        await ctx.respond(embed=e)


async def clear(ctx: ContextLike) -> None:
    msg = await get_prev_lineup(ctx.channel)

    if msg is not None:
        e = msg.embeds[0].copy()
        e.color = 0x00bfff # deep sky blue
        e.set_author(name='Archive')
        await msg.edit(embed=e)

    data = await get_gather(ctx.guild.id)
    await clear_hours(ctx.guild, data.keys())
    await post_gather(ctx.guild.id, {})

    if isinstance(ctx, commands.Context):
        await ctx.send('募集をリセットしました。')
    else:
        await ctx.respond({'ja': '募集をリセットしました。'}.get(ctx.locale, 'Cleared.'))


async def now(ctx: ContextLike) -> None:
    e = make_lineup(await get_gather(ctx.guild.id))
    await delete_prev_lineup(ctx.channel)

    if isinstance(ctx, commands.Context):
        await ctx.send(embed=e)
    else:
        await ctx.respond(embed=e)


async def out(ctx: ContextLike, hours_text: str) -> None:
    data = await get_gather(ctx.guild.id)
    hours = get_hours(hours_text)

    for hour in hours:
        try:
            data.pop(str(hour))
        except KeyError:
            pass

    payload = {'content': f'{", ".join(map(str, sorted(set(hours))))}の募集を削除しました。'}

    try:
        payload['embed'] = make_lineup(data)
        await delete_prev_lineup(ctx.channel)
    except NotGathering:
        pass

    await clear_hours(ctx.guild, hours)
    await post_gather(ctx.guild.id, data)

    if isinstance(ctx, commands.Context):
        await ctx.send(**payload)
    else:
        await ctx.respond(**payload)


class Match(commands.Cog, name='Match'):

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.hide: bool = False
        self.description: str = 'Recruitment of Participants'
        self.description_localizations: dict[str, str] = {'ja':'挙手関連'}


    @slash_command(
        name = 'can',
        description = 'Participate in match',
        description_localizations = {'ja': '交流戦の挙手'}
    )
    @is_allowed_channel()
    @commands.guild_only()
    async def match_can(
        self,
        ctx: ApplicationContext,
        hours: Option(
            str,
            name = 'hours',
            name_localizations = {'ja': '時間'},
            description = 'Time to participate (multiple available)',
            description_localizations = {'ja': '参加する時間(複数可)'},
        ),
        action: Option(
            str,
            name = 'type',
            name_localizations = {'ja': 'タイプ'},
            description = 'Participate or tentatively participate.',
            description_localizations = {'ja': '挙手または仮挙手'},
            choices = [
                OptionChoice(name = 'can', value = 'c', name_localizations = {'ja': '挙手'}),
                OptionChoice(name = 'tentatively', value = 't', name_localizations = {'ja': '仮挙手'})
            ],
            default = 'c'
        ),
        member: Option(
            Member,
            name = 'member',
            name_localizations = {'ja': 'メンバー'},
            description = 'Member to participate',
            description_localizations = {'ja': '参加するメンバー'},
            default = None
        )
        ) -> None:
        await ctx.response.defer()
        await participate(ctx, [member or ctx.user], action, hours)


    @commands.command(
        name = 'can',
        aliases = ['c'],
        description = 'Participate in match',
        brief = '交流戦の挙手',
        usage = '!c [@members] <hours>',
        hidden = False
    )
    @is_allowed_channel()
    @commands.guild_only()
    async def can(
        self,
        ctx: commands.Context,
        members: commands.Greedy[Member] = [],
        *,
        hours: str = ''
    ) -> None:
        await participate(ctx, members or [ctx.author], 'c', hours)


    @commands.command(
        name = 'tentatively',
        aliases = ['t', 'maybe', 'rc', 'sub'],
        description = 'Tentatively participate in match',
        brief = '交流戦の仮挙手',
        usage = '!t [@members] <hours>',
        hidden = False
    )
    @is_allowed_channel()
    @commands.guild_only()
    async def tentative(
        self,
        ctx: commands.Context,
        members: commands.Greedy[Member] = [],
        *,
        hours: str = ''
    ) -> None:
        await participate(ctx, members or [ctx.author], 't', hours)


    @slash_command(
        name = 'drop',
        description = 'Cancel participation',
        description_localizations = {'ja': '挙手を取り下げる'}
    )
    @is_allowed_channel()
    @commands.guild_only()
    async def match_drop(
        self,
        ctx: ApplicationContext,
        hours: Option(
            str,
            name = 'hours',
            name_localizations = {'ja': '時間'},
            description = 'Multiple available',
            description_localizations = {'ja': '挙手を取り下げる時間(複数可)'},
        ),
        member: Option(
            Member,
            name = 'member',
            name_localizations = {'ja': 'メンバー'},
            description = 'Member who cancel his participation',
            description_localizations = {'ja': '挙手を取り下げるメンバー'},
            default = None
        )
    ) -> None:
        await ctx.response.defer()
        await drop(ctx, [member or ctx.user], hours)


    @commands.command(
        name = 'drop',
        aliases = ['d', 'dr'],
        description = 'Cancel participation',
        brief = '挙手の取り消し',
        usage = '!d [@members] <hours>',
        hidden = False
    )
    @is_allowed_channel()
    @commands.guild_only()
    async def drop(
        self,
        ctx: commands.Context,
        members: commands.Greedy[Member] = [],
        *,
        hours: str = ''
    ) -> None:
        await drop(ctx, members or [ctx.author], hours)


    @slash_command(
        name = 'out',
        description = 'Delete recruiting',
        description_localizations = {'ja': '募集時間を削除'}
    )
    @is_allowed_channel()
    @commands.guild_only()
    async def match_out(
        self,
        ctx: ApplicationContext,
        hours: Option(
            str,
            name = 'hours',
            name_localizations = {'ja': '時間'},
            description = 'Multiple available',
            description_localizations = {'ja': '削除する時間(複数可)'},
        )
    ) -> None:
        await ctx.response.defer()
        await out(ctx, hours)


    @commands.command(
        name = 'out',
        description = 'Delete recruiting',
        brief = '募集時間を削除',
        usage = '!out <hours>',
        hidden = False
    )
    @is_allowed_channel()
    @commands.guild_only()
    async def out(
        self,
        ctx: commands.Context,
        *,
        hours: str
    ) -> None:
        await out(ctx, hours)


    @slash_command(
        name = 'now',
        description = 'Show recruiting state.',
        description_localizations = {'ja': '募集状況を表示'}
    )
    @is_allowed_channel()
    @commands.guild_only()
    async def match_now(self, ctx: ApplicationContext) -> None:
        await ctx.response.defer()
        await now(ctx)


    @commands.command(
        name = 'now',
        aliases = ['warlist', 'list'],
        description = 'Show recruiting state.',
        brief = '募集状況の表示',
        usage = '!now',
        hidden = False
    )
    @is_allowed_channel()
    @commands.guild_only()
    async def now(self, ctx: commands.Context) -> None:
        await now(ctx)


    @slash_command(
        name = 'clear',
        description = 'Clear war list',
        description_localizations = {'ja': '募集を全てリセット'}
    )
    @is_allowed_channel()
    @commands.guild_only()
    async def match_clear(self, ctx: ApplicationContext):
        await ctx.response.defer()
        await clear(ctx)


    @commands.command(
        name = 'clear',
        description = 'Clear war list',
        brief = '募集を全てリセット',
        usage = '!clear',
        hidden = False
    )
    @is_allowed_channel()
    @commands.guild_only()
    async def clear(self, ctx: commands.Context) -> None:
        await clear(ctx)


    @slash_command(
        name = 'pick',
        description = 'Randomly pick a member.',
        description_localizations = {'ja': 'メンバーをランダムに選択'}
    )
    @is_allowed_channel()
    @commands.guild_only()
    async def pick(
        self,
        ctx: ApplicationContext,
        role: Option(
            Role,
            name = 'role',
            name_localizations = {'ja': 'ロール'},
            description='Members\' role',
            description_localizations = {'ja': 'メンバーのロール'}
        )
    ) -> None:
        await ctx.response.defer()

        try:
            await ctx.respond((random.choice(role.members)).mention)
        except IndexError:
            raise PlayerNotFound


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Match(bot))
