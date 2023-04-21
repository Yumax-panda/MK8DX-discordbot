from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Union, TypeVar, Type
from typing_extensions import Self
from datetime import datetime, timedelta
from copy import copy

from .errors import *
from .plotting import make
from objects import Race, Rank, Track
from common import MyEmbed, get_integers, update_sokuji
from constants import MY_ID, BOT_IDS


if TYPE_CHECKING:
    from collections.abc import Callable
    from discord import Message, WebhookMessage, File
    from discord.abc import Messageable

    MessageLike = Union[Message, WebhookMessage]
    T = TypeVar('T', Callable)


def archive_check(func: Type[T]) -> T:
    def predicate(*args, **kwargs):
        mogi: Mogi = args[0]

        if mogi.is_archive:
            raise MogiArchived
        return func(*args, **kwargs)
    return predicate


class Mogi:

    __slots__ = (
        'races',
        'tags',
        'banner_users',
        'penalty',
        'repick',
        'message',
        'is_archive',
        'is_ja',
        'loaded_track'
    )

    def __init__(
        self,
        races: list[Race] = [],
        tags: Optional[list[str]] = None,
        banner_users: set[str] = set(),
        penalty: list[int] = [0, 0],
        repick: list[int] = [0, 0],
        message: Optional[MessageLike] = None,
        is_archive: bool = False,
        is_ja: bool = True,
        loaded_track: Optional[Track] = None
    ) -> None:
        self.races: list[Race] = races
        self.tags: list[str] = tags
        self.banner_users: set[str] = banner_users
        self.penalty: list[int] = penalty
        self.repick: list[int] = repick
        self.message: MessageLike = message
        self.is_archive: bool = is_archive
        self.is_ja: bool = is_ja
        self.loaded_track: Optional[Track] = loaded_track

    @property
    def total(self) -> list[int]:
        scores = [0, 0]

        for r in self.races:
            scores[0] += r.scores[0]
            scores[1] += r.scores[1]

        scores[0] += self.penalty[0] + self.repick[0]
        scores[1] += self.penalty[1] + self.repick[1]
        return scores

    @staticmethod
    def score_to_string(scores: list[int], compact: bool = False) -> str:
        return ' : '.join(map(str, scores)) + ('({:+})'.format(scores[0]-scores[1]) if not compact else '')


    @property
    def embed(self) -> MyEmbed:
        title = '即時集計 ' if self.is_ja else 'Sokuji '
        title += f'6v6\n{self.tags[0]} - {self.tags[1]}'
        e = MyEmbed(
            title = title,
            description = f'`{Mogi.score_to_string(self.total)} @{12-len(self.races)}`',
        )

        for i, race in enumerate(self.races):
            txt = f'{i+1} '
            if race.track is not None:
                txt += '- '+ (race.track.nick_ja if self.is_ja else race.track.nick_en)
            e.add_field(
                name = txt,
                value = f'`{Mogi.score_to_string(race.scores)}`|`{race.ranks[0]}`',
                inline = False
            )

        if self.penalty != [0, 0]:
            e.add_field(name='Penalty', value=f'`{Mogi.score_to_string(self.penalty, True)}`', inline=False)

        if self.repick != [0, 0]:
            e.add_field(name='Repick', value=f'`{Mogi.score_to_string(self.repick, True)}`', inline=False)

        if self.banner_users:
            e.add_field(name='Members', value='> '+', '.join(map(lambda x: '@'+x, self.banner_users)), inline=False)

        if self.is_archive:
            e.set_author(name="アーカイブ" if self.is_ja else 'Archive' )

        return e


    def convert(self, message: MessageLike) -> Self:
        e = message.embeds[0].copy()
        self.message = message
        self.is_ja = '即時集計' in e.title
        self.tags = e.title.split('\n', maxsplit=1)[-1].split(' - ')
        self.races = []
        self.penalty = [0, 0]
        self.repick = [0, 0]
        self.is_archive = e.author.name in ('Archive', 'アーカイブ')
        self.banner_users = set()

        for field in e.fields:
            numbers = get_integers(field.value)

            if field.name in ('Penalty', 'Repick'):
                old_data: list[int] = getattr(self, field.name.lower()).copy()
                setattr(self, field.name.lower(), [numbers[0]+old_data[0], numbers[1]+old_data[1]])
            elif field.name == 'Members':
                self.banner_users = set(field.value.split('> @', maxsplit=1)[-1].split(', @'))
            else:
                track: Optional[Track] = None
                if '-' in field.name:
                    txt = field.name
                    track = Track.from_nick(txt[txt.find('-')+2:])
                self.races.append(Race([Rank(numbers[-6:]), Rank({i for i in range(1, 13)} - set(numbers[-6:]))], track))

        return self


    @staticmethod
    def is_readable(message: MessageLike) -> bool:
        try:
            return message.embeds[0].title.startswith(('Sokuji','即時集計')) and message.author.id in BOT_IDS
        except:
            return False

    @staticmethod
    def is_valid(message: MessageLike) -> bool:
        try:
            return Mogi.is_readable(message) and message.author.id == MY_ID
        except:
            return False


    @staticmethod
    async def get(messageable: Messageable, include_archive: bool = False) -> Mogi:
        mogi = Mogi()

        async for message in messageable.history(
            after = datetime.now() - timedelta(hours=1),
            oldest_first = False
        ):
            if mogi.loaded_track is None:
                mogi.loaded_track = Track.from_nick(message.content)

            if Mogi.is_valid(message):
                mogi.convert(message)

                if mogi.is_archive:
                    if include_archive:
                        return mogi
                    else:
                        raise MogiArchived
                return mogi

        raise MogiNotFound


    @archive_check
    async def add_race(
        self,
        rank_text: str,
        track_name: Optional[str] = None,
        race_num: Optional[int] = None,
        ) -> None:

        if len(self.races) == 12:
            raise NotAddable

        rank_string = Rank.validate_text(rank_text)
        if not rank_string:
            raise InvalidRankInput

        ranks = Rank.get_ranks(rank_string, [])
        race = Race

        if track_name is None:
            track = copy(self.loaded_track)
        else:
            track = Track.from_nick(track_name)

        race = Race(ranks, track)

        if not race.is_valid():
            raise InvalidRankInput
        self.loaded_track = None

        if race_num is not None:
            try:
                self.races.insert(race_num-1, race)
            except IndexError:
                raise OutOfRange
        else:
            self.races.append(race)

        await self.update_obs()


    @archive_check
    async def back(self, index: int = -1) -> None:

        if not self.races:
            raise NotBackable

        try:
            self.races.pop(index)
        except IndexError:
            raise OutOfRange

        await self.update_obs()



    async def update_obs(self) -> None:

        if not self.banner_users:
            return

        left: int = 12-len(self.races)
        dif = self.total[0]-self.total[1]
        payload = {
            'teams': self.tags.copy(),
            'left': left,
            'win': int(dif>left*40),
            'dif': '{:+}'.format(dif),
            'scores': self.total
        }
        await update_sokuji(payload, self.banner_users.copy())
        return


    def make_result(self) -> File:
        scores: list[list[int]] = [self.penalty.copy(), self.repick.copy()]
        track: Optional[Track] = None

        for race in self.races:
            scores.append(race.scores)
            track = track or race.track

        return make(self.tags, scores, track.nick_en if track else None)


    async def send(
        self,
        messageable: Messageable,
        content: Optional[str] = None,
    ) -> None:
        payload = {}

        if content is not None:
            payload['content'] = content
        e = self.embed.copy()

        if len(self.races) == 12:
            e.set_image(url='attachment://result.png')
            payload['file'] = self.make_result()

        payload['embed'] = e
        message = await messageable.send(**payload)

        if self.message is not None:
            await self.message.delete()

        self.message = message
        return


    async def refresh(self, content: Optional[str] = None) -> None:
        if self.message is None:
            raise MogiNotFound

        payload = {'attachments':[]}

        if content is not None:
            payload['content'] = content
        e = self.embed.copy()

        if len(self.races) == 12:
            e.set_image(url='attachment://result.png')
            payload['file'] = self.make_result()

        payload['embed'] = e
        self.message = await self.message.edit(**payload)


    @staticmethod
    def banner_embed(banner_users: set[str]) -> MyEmbed:
        """Copyright: sheat, GungeeSpla"""
        e = MyEmbed(title="Banner URL")

        for user in banner_users:
            e.add_field(
                name=f'__{user[:-4]}\'s URL__',
                value=f'> https://yumax-panda.github.io/sokuji-view/?user={user}',
                inline=False
            )

        return e


    async def updater_lineup(self) -> MyEmbed:
        await self.update_obs()
        return Mogi.banner_embed(self.banner_users)
