from discord.ext import commands, pages

class ResultPaginator(pages.Paginator):

    def __init__(
        self,
        title: str = '',
        header: str = '',
        contents: list = [],
        footer: str = '',
    ) -> None:
        self.title: str = title
        self.header: str = header
        self.contents: list[str] = contents
        self.footer: str = footer

        body = commands.Paginator(prefix='', max_size=800)

        for content in contents:
            body.add_line(content)

        is_compact = (len(body.pages) == 1)

        super().__init__(
            pages=[f'{title}```{header}{b}{footer}' for b in body.pages],
            show_indicator=not is_compact,
            show_disabled=not is_compact,
            author_check=False
        )
        self.current_page = self.page_count


def WinOrLose(diff: int) -> str:

    if diff < 0:
        return 'Lose'
    elif diff == 0:
        return 'Draw'
    return 'Win'