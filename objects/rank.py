from __future__ import annotations

from typing import Optional, Type, TypeVar
from collections.abc import Iterable
import re

from sokuji.errors import InvalidRankInput

_SCORES = (15, 12, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1)
_TRANSLATE_TABLE = dict(zip(map(ord, '１２３４５６７８９０ー＋　'), '1234567890-+ '))
_RE = re.compile(r'[^0-9\-\ +]')

T = TypeVar('T')


class Rank:

    __slots__ = (
        '__data'
    )

    def __init__(self, data: Iterable[int] = []) -> None:
        self.__data = list(data)

    def __str__(self) -> str:
        return ",".join(map(str, sorted(self.__data)))

    def __len__(self) -> int:
        return len(self.data)

    @property
    def data(self) -> list[int]:
        return self.__data

    @property
    def score(self) -> int:
        return sum(map(lambda r: _SCORES[r-1], self.data))

    def validate(self, ranks: list[Rank]) -> bool:
        filled: set[int] = set()
        for rank in ranks:
            filled.update(rank.data)
        for r in filled:
            if r in self.data:
                self.__data.remove(r)
        if len(self) == 6:
            return True
        if len(self) > 6:
            self.__data = self.data[:6]
            return True
        unfilled: set[int] = {r for r in range(1, 13)} - filled - set(self.data)
        if len(unfilled) + len(self) <= 6:
            self.__data.extend(unfilled)
        else:
            while len(self.data) < 6:
                r: int = max(unfilled)
                self.__data.append(r)
                unfilled.remove(r)
        self.__data.sort()
        return len(self) == 6

    @classmethod
    def from_text(cls: Type[T], text: str) -> Optional[T]:
        if ' ' in text:
            return None
        data: list[int] = []
        prev: Optional[int] = None
        next_list: list[int] = []
        loopFlag: bool = False
        while text:
            next_list = []
            if text.startswith('-'):
                loopFlag = True
                text = text[1:]
                if data:
                    prev = data[-1]
                else:
                    prev = 0
            if text.startswith('0'):
                next_list = [10]
                text = text[1:]
            elif text.startswith('+'):
                next_list = [11]
                text = text[1:]
            elif text.startswith('10'):
                next_list = [10]
                text = text[2:]
            elif text.startswith('110'):
                next_list = [1, 10]
                text = text[3:]
            elif text.startswith('1112'):
                next_list = [11, 12]
                text = text[4:]
            elif text.startswith('111'):
                next_list = [1, 11]
                text = text[3:]
            elif text.startswith('112'):
                next_list = [1, 12]
                text = text[3:]
            elif text.startswith('11'):
                next_list = [11]
                text = text[2:]
            elif text.startswith('12'):
                if data:
                    next_list = [12]
                else:
                    next_list = [1, 2]
                text = text[2:]
            elif text:
                try:
                    next_list = [int(text[0], 16)]
                    text = text[1:]
                except ValueError:
                    raise InvalidRankInput

            if loopFlag:
                if not next_list:
                    next_list = [12]
                next = next_list[0]
                while next - prev > 1:
                    data.append(prev+1)
                    prev += 1
                loopFlag = False
            data += next_list
        return cls(data=[r for r in sorted(set(data)) if 0 < r < 13])

    @classmethod
    def get_ranks(cls: Type[T], text: str, ranks: list[T] = []) -> list[T]:
        for t in text.split():
            rank: cls = cls.from_text(t)
            if rank.validate(ranks=ranks):
                ranks.append(rank)
        if len(ranks) == 1:
            rank: cls = cls()
            if rank.validate(ranks=ranks):
                ranks.append(rank)
        return ranks

    @staticmethod
    def validate_text(text: str) -> Optional[str]:
        translated_text = text.translate(_TRANSLATE_TABLE)
        if _RE.search(translated_text) is None:
            return translated_text