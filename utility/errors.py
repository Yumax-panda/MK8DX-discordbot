from errors import MyError


class IdNotRegistered(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': 'Discord IDが登録されていません。'},
            default='Discord ID is not registered.'
        )