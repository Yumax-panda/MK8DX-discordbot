from errors import MyError


class TimeNotSelected(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': '時間が選択されていません。'},
            default='Time is not selected.'
        )


class TooManyHours(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': '指定できる時間は25個までです。'},
            default='The maximum number of times that can be set is 25.'
        )


class NotGathering(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': '募集している時間はありません。'},
            default='There is no recruiting.'
        )


class FailedToManageRole(MyError):

    def __init__(self) -> None:
        super().__init__(
            content={'ja': 'ロールを操作できません。\n他のbotの挙手機能を使っている場合、そちらをリセットしてください。'},
            default='I cannot manage role.\n If you are using other bot which can manage roles, please reset that one.'
        )