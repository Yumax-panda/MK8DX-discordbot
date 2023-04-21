from __future__ import annotations
from typing import Optional, Union
from enum import Enum

class TZ(Enum):

    @staticmethod
    def from_locale(locale: Optional[str]) -> TZ:
        if locale is None:
            return TZ.JA

        for timezone in TZ:
            if timezone._value_[0] == locale:
                return timezone

        return TZ.JA

    @property
    def locale(self) -> str:
        return self._value_[0]

    @property
    def offset(self) -> Union[int, float]:
        return self._value_[1]


    ID = ("id", 7)
    DA = ("da", 1)
    DE = ("de", 1)
    EN_GB = ("en-GB", 0)
    EN_ES = ("en-ES", -5)
    FR = ("fr", 1)
    HR = ("hr", 1)
    IT = ("it", 1)
    LT = ("lt", 2)
    HU = ("hu", 1)
    NL = ("nl", 1)
    NO = ("no", 1)
    PL = ("pl", 1)
    PT_BR = ("pt-BR", -3)
    RO = ("ro", 2)
    FI = ("fi", 2)
    SV_SE = ("sv-SE", 1)
    VI = ("vi", 7)
    TR = ("tr", 3)
    CS = ("cs", 1)
    EL = ("el", 2)
    BG = ("bg", 2)
    RU = ("ru", 6)
    UK = ("uk", 2)
    HI = ("hi", 5.5)
    TH = ("th", 7)
    ZH_CH = ("zh-CN", 8)
    JA = ("ja", 9)
    ZH_TH = ("zh-TW", 8)
    KO = ("ko", 9)