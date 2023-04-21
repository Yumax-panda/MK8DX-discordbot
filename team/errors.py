from errors import MyError


class PlayerNotFound(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja':'プレイヤーが見つかりません。'},
            default='Player not found.'
        )


class RoleNotFound(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja':'ロールが見つかりません。'},
            default='Role not found.'
        )


class MessageNotFound(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': 'メッセージが見つかりません。'},
            default='Message not found.'
        )


class NotAuthorized(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': 'この操作をする権限がありません。'},
            default='You cannot do this interaction.'
        )


class AuthorNotFound(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': '作者が見つかりません。'},
            default='Author not found.'
        )


class TooManyPlayers(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': '対象のプレイヤーが多すぎます。'},
            default='Too many players to display.'
        )


class InvalidDatetime(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': '時間は0~23の範囲で指定してください。'},
            default='Hour must be 0~23.'
        )