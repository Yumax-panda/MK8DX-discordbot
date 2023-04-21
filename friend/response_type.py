from __future__ import annotations
from typing import Optional
from enum import Enum


class ResponseType(Enum):

    Duplicate = (
        "2回以上申請しています。",
        "Duplicate friend request.",
        "重複",
        "Duplicate",
        False
    )

    RateLimit = (
        "レート制限を超えました。",
        "Rate limit exceeded.",
        "レート制限",
        "Rate limit",
        False
    )

    Already = (
        "既にフレンドです。",
        "Already friend.",
        "既フレ",
        "Friend",
        False
    )

    Unknown = (
        "申請に失敗しました。",
        "Failed to apply.",
        "",
        "",
        False
    )

    Success = (
        "申請に成功しました。",
        "Successfully applied.",
        "成功",
        "Success",
        True
    )

    @staticmethod
    def judge(data: dict) -> ResponseType:
        if "errorMessage" not in data:
            return ResponseType.Success

        if data["status"] == 9437:
            return ResponseType.RateLimit
        elif data["status"] == 9464:
            return ResponseType.Duplicate
        elif data["status"] == 9467:
            return ResponseType.Already
        else:
            return ResponseType.Unknown

    @property
    def description_ja(self) ->str:
        return self.value[0]

    @property
    def description_en(self) ->str:
        return self.value[1]

    @property
    def brief_ja(self) ->str:
        return self.value[2]

    @property
    def brief_en(self) ->str:
        return self.value[3]

    def __bool__(self) -> bool:
        return self.value[4]

    def __eq__(self, other) -> bool:
        return isinstance(other, ResponseType) and other.value[0] == self.value[0]


    def describe(self, locale: Optional[str] = None) -> str:
        return self.description_ja if locale=='ja' else self.description_en

    def brief(self, locale: Optional[str] = None) -> str:
        return self.brief_ja if locale=='ja' else self.brief_en