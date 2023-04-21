from errors import MyError


class MogiNotFound(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': '実施している即時が見つかりません。'},
            default='Mogi not found'
        )



class InvalidMessage(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': 'メッセージが不正です。'},
            default='Invalid message.'
        )



class InvalidRankInput(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': '順位の入力が不正です。'},
            default='Invalid rank input.'
        )



class NotBackable(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': 'レースを戻すことができません。'},
            default='You cannot go back anymore.'
        )



class NotAddable(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': '既に12レース終了しています。'},
            default='This sokuji has already finished.'
        )



class MogiArchived(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': 'この即時は既に終了しています。'},
            default='This sokuji has already finished.'
        )



class InvalidTag(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': 'タグの名前が不正です。'},
            default='Invalid tag name.'
        )


class OutOfRange(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': '存在しないレース番号です。'},
            default='Invalid race number.'
        )