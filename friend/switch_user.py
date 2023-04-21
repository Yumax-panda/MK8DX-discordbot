from __future__ import annotations
from typing import (
    TypedDict,
    TYPE_CHECKING,
    Type,
    TypeVar
)

U = TypeVar("U")


class MinimalUserPayload(TypedDict):
    nsa_id: str
    name: str
    fc: str


class SwitchUserPayload(TypedDict):
    id: int
    nsaId: str
    imageUri: str
    name: str
    extras: dict


class MinimalUser:

    __slots__ = (
        'nsa_id',
        'name',
        'fc'
    )

    if TYPE_CHECKING:
        nsa_id: str
        name: str
        fc: str


    def __init__(self, data: MinimalUserPayload):

        for attr in MinimalUser.__slots__:
            setattr(self, attr, data[attr])


    def to_dict(self) -> MinimalUserPayload:
        return {attr: getattr(self, attr) for attr in MinimalUser.__slots__}


    @classmethod
    def from_dict(cls: Type[U], data: MinimalUserPayload) -> U:
        return cls(data)



class SwitchUser:

    __slots__ = (
        'id',
        'nsa_id',
        'image_uri',
        'name',
        'extras',
        'fc'
    )

    if TYPE_CHECKING:
        id: int
        nsa_id: str
        image_uri: str
        name: str
        extras: dict
        fc: str


    def __init__(self, *, data: SwitchUserPayload, fc: str) -> None:
        self._update(data)
        self.fc: str = fc


    def _update(self, data: SwitchUserPayload) -> None:
        self.id = data['id']
        self.nsa_id = data['nsaId']
        self.image_uri = data['imageUri']
        self.name = data['name']
        self.extras = data['extras']


    def to_minimal(self) -> MinimalUser:
        data = {
            "nsa_id": self.nsa_id,
            "name": self.name,
            "fc": self.fc
        }
        return MinimalUser(data)
