from discord import ApplicationCommandError
from discord.ext.commands import CommandError


class MyError(ApplicationCommandError, CommandError):

    __slots__ = (
        '_content',
        '_default',
        '_message',
    )

    def __init__(
        self,
        content: dict[str, str],
        default: str,
    ):
        self._content: dict[str, str] = content
        self._default = default
        self._message = content['ja'] + '\n' + default

    @property
    def content(self) -> dict[str, str]:
        return self._content

    @property
    def default(self) -> str:
        return self._default

    @property
    def message(self) -> str:
        return self._message

    def localized_content(self, locale: str) -> str:
        return self.content.get(locale, self.default)