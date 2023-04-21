from __future__ import annotations
from typing import Optional, Union, Type, TypeVar
from math import isnan

import aiohttp
import asyncio
import re

from common import get_lounge_ids

T = TypeVar('T')


MKC_URL = 'https://www.mariokartcentral.com/mkc/registry/users/'
LOUNGE_WEB = 'https://www.mk8dx-lounge.com/PlayerDetails/'
API_URL = 'https://www.mk8dx-lounge.com/api/player'
_RE = re.compile(r'[0-9]{4}\-[0-9]{4}\-[0-9]{4}')


class PlayerBase:

    __slots__ = (
        'id',
        'name',
        'mkc_id',
        'discord_id',
        '_linked_id',
        'country_code',
        'switch_fc',
        'is_hidden',
        'mmr',
        'max_mmr',
        'is_empty'
    )

    def __init__(
        self,
        id: Optional[int] = None,
        name: Optional[str] = None,
        mkc_id: Optional[int] = None,
        discord_id: Optional[str] = None,
        linked_id: Optional[str] = None,
        country_code: Optional[str] = None,
        switch_fc: Optional[str] = None,
        is_hidden: bool = False,
        mmr: Optional[int] = None,
        max_mmr: Optional[int] = None,
        is_empty: bool = False
    ) -> None:
        self.id: Optional[int] = id
        self.name: Optional[str] = name
        self.mkc_id: Optional[int] = mkc_id
        self.discord_id: Optional[str] = discord_id
        self._linked_id: Optional[str] = linked_id or discord_id
        self.country_code: Optional[str] = country_code
        self.switch_fc: Optional[str] = switch_fc
        self.is_hidden: bool = is_hidden
        self.mmr: Optional[int] = mmr
        self.max_mmr: Optional[int] = max_mmr
        self.is_empty: bool = is_empty

    def to_dict(self) -> dict:
        data = {attr: getattr(self, attr) for attr in self.__slots__}
        data['linked_id'] = data.pop('_linked_id')
        return data

    @classmethod
    def from_dict(cls: Type[T], data: dict) -> T:
        _data = {}

        for k, v in data.items():
            if  isinstance(v, float) and isnan(v):
                _data[k] = None
            else:
                _data[k] = v

        return cls(**_data)

    @property
    def linked_id(self) -> Optional[str]:
        return self._linked_id

    @linked_id.setter
    def linked_id(self, value) -> None:

        if value is not None:
            self._linked_id = str(value)

    @property
    def is_rich(self) -> bool:
        return (
            not self.is_empty
            and self.mmr is not None
            and self.max_mmr is not None
            and not self.is_hidden
        )

    @property
    def is_placement(self) -> bool:
        return (
            self.is_empty
            or self.is_hidden
            or self.mmr is None
        )


class Player(PlayerBase):
    """
    Attributes
    ----------
    id: :class: `int`
    name: :class: `str`
    mkc_id: :class: `str`
    discord_id: :class: `str | None`
    linked_id: :class: `str | None`
    country_code: :class: `str | None`
    switch_fc: :class: `str | None`
    is_hidden: :class: `bool`
    mmr: :class: `int | None`
    max_mmr: :class: `int | None`
    is_empty: :class: `bool` = False
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def __bool__(self):
        return not self.is_hidden

    @property
    def mkc_url(self) -> str:
        return f'{MKC_URL}{int(self.mkc_id)}'

    @property
    def lounge_url(self) -> str:
        return f'{LOUNGE_WEB}{int(self.id)}'


    @staticmethod
    def loads(data: dict) -> Player:
        return Player(
            id=data['id'],
            name=data['name'],
            mkc_id=data['mkcId'],
            discord_id=data.get('discordId'),
            country_code=data.get('countryCode'),
            switch_fc=data.get('switchFc'),
            is_hidden=data['isHidden'],
            mmr=data.get('mmr'),
            max_mmr=data.get('maxMmr'),
            is_empty = False
        )


class EmptyPlayer(PlayerBase):

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.is_empty: bool = True

    def __bool__(self):
        return False

PlayerLike = Union[Player, EmptyPlayer]

async def get_player(**kwargs) -> PlayerLike:
    """|coro|

    Parameters
    ----------
    name: :class:`str | None`
    mkc_id: :class:`int | None`
    discord_id: :class:`int | None`
    switch_fc: :class:`str | None`

    Returns
    -------
    :class:`Player | EmptyPlayer`
    """

    name = kwargs.get('name')
    mkc_id = kwargs.get('mkc_id')
    discord_id = kwargs.get('discord_id')
    fc = kwargs.get('switch_fc')
    params = {}

    if name is not None:
        params['name'] = name
    elif mkc_id is not None:
        params['mkcId'] = mkc_id
    elif discord_id is not None:
        params['discordId'] = discord_id
    elif fc is not None:
        params['fc'] = fc
    else:
        return EmptyPlayer(**kwargs)

    async with aiohttp.ClientSession() as session:
        async with session.get(url=API_URL, params=params) as response:
            if response.status != 200:
                return EmptyPlayer(**kwargs)
            return Player.loads(await response.json())


async def get_players_by_ids(discord_ids: list[int]) -> list[PlayerLike]:
    linked_ids = await get_lounge_ids()
    lounge_ids = [linked_ids.get(str(i), i) for i in discord_ids]
    tasks = [asyncio.create_task(get_player(discord_id=int(id))) for id in lounge_ids]
    players: list[PlayerLike] = await asyncio.gather(*tasks)

    for p, main_id in zip(players, discord_ids):
        p.linked_id = str(main_id)

    return players


async def get_players_by_fc_string(input_string: str) -> list[PlayerLike]:
    return await asyncio.gather(*[asyncio.create_task(get_player(switch_fc=fc)) for fc in _RE.findall(input_string)])


def from_records(records: list[dict]) -> list[PlayerLike]:
    ret: list[PlayerLike] = []

    for data in records:

        if data['is_empty']:
            ret.append(EmptyPlayer.from_dict(data))
        else:
            ret.append(Player.from_dict(data))

    return ret


