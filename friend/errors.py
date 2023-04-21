from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from errors import MyError

if TYPE_CHECKING:
    from .response_type import ResponseType


class InvalidURL(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': 'URLが間違っています。'},
            default='Invalid URL.'
        )


class TokenNotFound(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': 'ログインがされていません。`/friend setup`でログインしてください。'},
            default='You may not be logged in. Try `/friend setup`.'
        )


class AuthorizationFailure(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': '認証失敗しました。時間をおいて再度試してください。'},
            default='Authorization failed. Try again later.'
        )


class FCNotFound(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': 'フレンドコードが見つかりませんでした。'},
            default='Friend code not found.'
        )


class ParamsNotEnough(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': '入力が不十分です。'},
            default='Insufficient input.'
        )


class TooManyInputs(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': 'フレンドコードの指定は12個までです。'},
            default='You can apply less than 12 friend requests.'
        )


class RequestFailure(MyError):

    def __init__(self, type: Optional[ResponseType]=None) -> None:

        if type is None or type.name=="Unknown":
            super().__init__(
                content={'ja': '申請できませんでした。\n__考えられる原因__\n> 既にフレンドである\n> 自身に申請している\n> 2回目以上の申請である'},
                default="Failed to request.\nExpected...\n> Already a friend\n> Applied to yourself\n> Applying for more than second times."
            )
        else:
            super().__init__(
                content={"ja": type.description_ja},
                default= type.description_en
            )
