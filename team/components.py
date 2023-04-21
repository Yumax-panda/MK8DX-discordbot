from __future__ import annotations
from typing import Optional, Union, TYPE_CHECKING
from datetime import datetime
from discord.utils import format_dt
import discord

from .errors import *
from common import get_integers

if TYPE_CHECKING:
    from discord import (
        Role,
        User,
        Member,
        Message,
        Interaction,
        WebhookMessage
    )
    from discord.ui import Button, Item
    MessageLike = Union[Message, WebhookMessage]
    MemberLike = Union[Member, User]


class VoteView(discord.ui.View):

    def __init__(self, lang: str = 'ja') -> None:
        super().__init__(timeout=None)
        self.clear_items()
        self.set_labels(lang)
        for item in (self.callback, self.mention, self.quit):
            self.add_item(item)


    def set_labels(self, lang: str) -> None:
        flag = lang == 'ja'
        self.mention.label = 'メンション' if flag else 'Mention'
        self.quit.label = '終了' if flag else 'Quit'
        self.callback.options[0].label = '参加'  if flag else 'can'
        self.callback.options[1].label = '補欠'  if flag else 'sub'
        self.callback.options[2].label = '不参加'  if flag else 'drop'


    async def on_error(self, error: Exception, item: Item, interaction: Interaction) -> None:
        content: Optional[str] = None

        if isinstance(error, MyError):
            content = error.localized_content(interaction.locale)

        if content is not None:
            if interaction.response.is_done():
                await interaction.followup.send(content, wait=True, ephemeral=True, delete_after=15.0)
            else:
                await interaction.response.send_message(content, ephemeral=True, delete_after=15.0)
            return
        raise error


    @discord.ui.string_select(
        custom_id ='type',
        placeholder = 'Type',
        options = [
            discord.SelectOption(label='参加', value='can'),
            discord.SelectOption(label='補欠',value='sub'),
            discord.SelectOption(label='不参加',value='drop')
        ])
    async def callback(
        self,
        select: discord.ui.Select,
        interaction: Interaction
    ) -> None:
        await interaction.response.defer()
        vote = Vote.convert(interaction.message)
        vote.role_check(interaction.user)
        vote.can -= {interaction.user}
        vote.sub -= {interaction.user}
        vote.drop -= {interaction.user}
        vote._data[select.values[0]] = ({interaction.user} | vote._data[select.values[0]]) & set(vote.role.members)
        await interaction.message.edit(embed=vote.embed, view=VoteView(vote.lang))
        await interaction.followup.send({'ja': '投票を更新しました'}.get(interaction.locale, 'Updated!'), ephemeral=True)
        return


    @discord.ui.button(label='Mention', custom_id='mention', style=discord.ButtonStyle.primary)
    async def mention(self, button: Button, interaction: Interaction) -> None:
        await interaction.response.defer()
        vote = Vote.convert(interaction.message)
        vote.author_check(interaction.user)
        if vote.unanswered:
            await interaction.followup.send(','.join([m.mention for m in vote.unanswered]))
        else:
            await interaction.followup.send(
                {'ja':'全員が投票を終えています。'}.get(interaction.locale, 'Everyone has answered.')
            )
        return


    @discord.ui.button(label='Quit', custom_id='quit', style=discord.ButtonStyle.danger)
    async def quit(self, button: Button, interaction: Interaction) -> None:
        await interaction.response.defer()
        vote = Vote.convert(interaction.message)
        vote.author_check(interaction.user)
        await interaction.message.edit(
            content = {'ja':'投票を終了しました。'}.get(interaction.locale, 'Finished.'),
            view = None
        )
        return


class Vote:

    __slots__ = (
        '_enemy',
        '_role',
        '_author',
        '_message',
        '_dt',
        '_lang',
        '_data'
    )

    def __init__(
        self,
        enemy: str,
        role: Role,
        author: MemberLike,
        message: Optional[MessageLike] = None,
        dt: Optional[datetime] = None,
        lang: Optional[str] = None,
        data: dict[str, set[Member]] = {},
    ) -> None:
        self._enemy: str = enemy
        self._role: Role = role
        self._author: MemberLike = author
        self._message: Optional[MessageLike] = message
        self._dt: Optional[datetime] = dt
        self._lang: str = lang or 'ja'
        self._data: dict[str, set[Member]] = data


    @property
    def enemy(self) -> str:
        return self._enemy

    @enemy.setter
    def enemy(self, value: str):
        self._enemy = str(value)

    @property
    def role(self) -> Role:
        return self._role

    @property
    def author(self) -> MemberLike:
        return self._author

    @property
    def message(self) -> Optional[MessageLike]:
        return self._message

    @property
    def dt(self) -> Optional[datetime]:
        return self._dt

    @property
    def lang(self) -> str:
        return self._lang

    @property
    def data(self) -> dict[str, set[Member]]:
        return self._data

    @property
    def can(self) -> set[MemberLike]:
        return self._data.get('can') or set()

    @can.setter
    def can(self, value: set[MemberLike]):
        self._data['can'] = value

    @property
    def sub(self) -> set[MemberLike]:
        return self._data.get('sub') or set()

    @sub.setter
    def sub(self, value: set[MemberLike]):
        self._data['sub'] = value

    @property
    def drop(self) -> set[MemberLike]:
        return self._data.get('drop') or set()

    @drop.setter
    def drop(self, value: set[MemberLike]) -> set[MemberLike]:
        self._data['drop'] = value

    @property
    def unanswered(self) -> set[MemberLike]:
        return (set(self.role.members)
                - self.can
                - self.sub
                -self.drop)

    @property
    def embed(self) -> discord.Embed:
        e = discord.Embed(
            title = f'vs {self.enemy}',
            color = discord.Colour.yellow(),
            description = self.role.mention
        )
        e.set_footer(text=f'by {str(self.author)}')
        e.add_field(
            name = '日時' if self.lang == 'ja' else 'Date',
            value = format_dt(self.dt, style='F'),
            inline = False
        )
        if self.can:
            e.add_field(
                name = ('参加 ' if self.lang == 'ja' else 'Participation ') + f'@{6-len(self.can)}',
                value = '> ' + ', '.join([str(m) for m in self.can]),
                inline = False
            )
        if self.sub:
            e.add_field(
                name = '補欠' if self.lang == 'ja' else 'Substitute',
                value = '> ' + ', '.join([str(m) for m in self.sub]),
                inline = False
            )
        if self.drop:
            e.add_field(
                name = '不参加' if self.lang == 'ja' else 'Not participation',
                value = '> ' + ', '.join([str(m) for m in self.drop]),
                inline = False
            )
        if self.unanswered:
            e.add_field(
                name = '未回答' if self.lang == 'ja' else 'Un-answered',
                value = '> ' + ', '.join([str(m) for m in self.unanswered]),
                inline = False
            )
        return e


    def author_check(self, member: MemberLike) -> bool:
        if not member == self.author:
            raise NotAuthorized
        return True


    def role_check(self, member: MemberLike) -> bool:
        if not self.role in member.roles:
            raise NotAuthorized
        return True


    @staticmethod
    def convert(message: MessageLike) -> Vote:
        try:
            if message.embeds:
                pass
            else:
                raise MessageNotFound
        except:
            raise MessageNotFound

        e = message.embeds[0].copy()
        lang = 'ja'
        enemy = e.title[3:]
        data = {}
        role = message.guild.get_role(get_integers(e.description)[0])

        if role is None:
            raise RoleNotFound
        author = message.guild.get_member_named(e.footer.text[3:])

        if author is None:
            raise AuthorNotFound

        for field in e.fields:

            if field.name.startswith(('日時', 'Date')):
                dt = datetime.fromtimestamp(get_integers(field.value)[0])
                if  'Date' in field.name:
                    lang = 'en'
            elif field.name.startswith(('参加','Participation')):
                data['can'] = {message.guild.get_member_named(i) for i in field.value[2:].split(', ')} - {None}
            elif field.name.startswith(('補欠', 'Substitute')):
                data['sub'] = {message.guild.get_member_named(i) for i in field.value[2:].split(', ')} - {None}
            elif field.name.startswith(('不参加','Not participation')):
                data['drop'] = {message.guild.get_member_named(i) for i in field.value[2:].split(', ')} - {None}
        return Vote(
            enemy = enemy,
            role = role,
            author = author,
            message = message,
            dt = dt,
            lang = lang,
            data = data
        )


    @staticmethod
    async def start(
        interaction: Interaction,
        enemy: str,
        role: Role,
        dt: datetime,
        lang: str = 'ja'
        ) -> Vote:
        msg = Vote(enemy=enemy, author=interaction.user, role=role, dt=dt, lang=lang)
        v = VoteView(lang = lang)

        if interaction.response.is_done():
            message = await interaction.followup.send(embed=msg.embed,view=v, wait=True)
            msg._message = message
        else:
            res = await interaction.response.send_message(embed=msg.embed,view=v)
            msg._message = res.message

        return msg