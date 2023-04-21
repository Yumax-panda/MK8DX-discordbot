from errors import MyError


class NotFoundError(MyError):

    def __init__(self) -> None:
        super().__init__(
            content = {'ja': '見つかりませんでした。'},
            default = 'Not found.'
        )