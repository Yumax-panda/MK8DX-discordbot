from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from typing_extensions import Self

from .rank import Rank

if TYPE_CHECKING:
    from .track import Track


class Race:

    __slots__ = (
        '__ranks',
        'track'
    )

    def __init__(
        self,
        ranks: list[Rank],
        track: Optional[Track] = None
    ):
        self.__ranks: list[Rank] = ranks
        self.track: Optional[Track] = track

    @property
    def ranks(self) -> list[Rank]:
        return self.__ranks

    @property
    def scores(self) -> list[int]:
        return [r.score for r in self.ranks]

    def is_valid(self) -> bool:
        return len(self.ranks) == 2

    def loads(self, text: str) -> Self:
        self.__ranks = Rank.get_ranks(text, ranks= self.ranks.copy())
        return self


