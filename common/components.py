from __future__ import annotations

from typing import Union, Any, Optional, TypeVar, TYPE_CHECKING, Callable
from discord import EmbedField
from discord.colour import Colour
from discord.ext import commands
from discord.embeds import Embed, _EmptyEmbed, EmptyEmbed
import datetime

from constants import get_rank, RANK_DATA, IGNORE_CHANNELS

if TYPE_CHECKING:
    from discord.types.embed import EmbedType
    T = TypeVar("T")
    F = TypeVar("F")
    MaybeEmpty = Union[T, _EmptyEmbed]


class MyEmbed(Embed):

    def __init__(
        self,
        *,
        color: Union[int, Colour, _EmptyEmbed] = EmptyEmbed,
        title: MaybeEmpty[Any] = EmptyEmbed,
        type: EmbedType = "rich",
        url: MaybeEmpty[Any] = EmptyEmbed,
        description: MaybeEmpty[Any] = EmptyEmbed,
        timestamp: datetime.datetime = None,
        fields: Optional[list[EmbedField]] = None,
    ) -> None:
        super().__init__(
            colour=Colour.yellow() if color is EmptyEmbed else color,
            title=title,
            type=type,
            url=url,
            description=description,
            timestamp=timestamp,
            fields=fields
        )


class ErrorEmbed(Embed):

    def __init__(
        self,
        *,
        color: Union[int, Colour, _EmptyEmbed] = EmptyEmbed,
        title: MaybeEmpty[Any] = EmptyEmbed,
        type: EmbedType = "rich",
        url: MaybeEmpty[Any] = EmptyEmbed,
        description: MaybeEmpty[Any] = EmptyEmbed,
        timestamp: datetime.datetime = None,
        fields: Optional[list[EmbedField]] = None,
    ) -> None:
        super().__init__(
            colour=Colour.red() if color is EmptyEmbed else color,
            title=title,
            type=type,
            url=url,
            description=description,
            timestamp=timestamp,
            fields=fields
        )


class LoungeEmbed(Embed):

    def __init__(
        self,
        mmr: Union[int, float],
        *,
        title: MaybeEmpty[Any] = EmptyEmbed,
        type: EmbedType = "rich",
        url: MaybeEmpty[Any] = EmptyEmbed,
        description: str = '',
        timestamp: datetime.datetime = None,
        fields: Optional[list[EmbedField]] = None,
    ) -> None:
        self.mmr: Union[int, float] = mmr
        rank = get_rank(int(mmr))
        self.rank: str = rank
        super().__init__(
            colour= RANK_DATA[rank.split(' ')[0]]['color'],
            title=title,
            type=type,
            url=url,
            description=description + f'\n**Rank**  {rank}',
            timestamp=timestamp,
            fields=fields
        )
        self.set_thumbnail(url=RANK_DATA[rank.split(' ')[0]]['url'])


def is_allowed_channel() -> Callable[[F], F]:

    async def predicate(ctx: commands.Context) -> bool:
        return ctx.channel.id not in IGNORE_CHANNELS

    return commands.check(predicate)