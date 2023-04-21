from errors import MyError


class EmptyResult(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': '戦績が見つかりません。'},
            default='Result not Found.'
        )


class InvalidScoreInput(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': '得点の入力が不正です。\n`自チーム (敵チーム 任意)`'},
            default='Invalid scores input\n `score (enemy_score; optional)`'
        )


class InvalidIdInput(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': 'IDの入力が不正です。'},
            default='Invalid ID input.'
        )


class IdOutOfRange(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': '存在しないIDが含まれています。'},
            default='This ID does not exist.'
        )


class NotCSVFile(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': 'CSVファイルのみが有効です。'},
            default='Only CSV file is available.'
        )


class NotAcceptableContent(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': 'ファイルの内容が不正です。'},
            default='Not acceptable content.'
        )


class NotMatched(MyError):
    pass