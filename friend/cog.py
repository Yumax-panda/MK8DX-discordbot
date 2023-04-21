"""
MIT License

Copyright (c) 2022 mizuyoukan-ao
Copyright (c) 2023-present Yumax-panda

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from discord.ext import commands
from discord import (
    Member,
    Option,
    OptionChoice,
    user_command,
    SlashCommandGroup,
    ApplicationContext
)

from objects.player import get_players_by_ids, get_player
from common.utils import maybe_param
from utility.cog import fm, peak

from .components import (
    send_url,
    search_user,
    RequestEmbed,
    RequestView,
    _multiple_requests
)
from .errors import *


class Friend(commands.Cog, name="Friend"):

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.hide: bool = False
        self.description: str = "Manage friend"
        self.description_localizations: dict[str, str] = {'ja': 'フレンドコード関連'}

    friend = SlashCommandGroup(name="friend")


    async def _send_request_by_fc(
        self,
        ctx: ApplicationContext,
        switch_fc: str,
        ephemeral: bool = True
    ) -> None:
        user = await search_user(ctx.user.id, switch_fc)
        await ctx.respond(
            ephemeral=ephemeral,
            embed=RequestEmbed(user=user, locale=ctx.locale),
            view=RequestView(user.nsa_id, ephemeral, ctx.locale)
        )


    async def _text_send_request_by_fc(
        self,
        ctx: commands.Context,
        switch_fc: str
    ) -> None:
        user = await search_user(ctx.author.id, switch_fc)
        await ctx.send(
            embed=RequestEmbed(user=user, locale='ja'),
            view=RequestView(user.nsa_id, ephemeral=False, locale='ja')
        )


    async def _send_request_by_id(
        self,
        ctx: ApplicationContext,
        discord_id: int,
        ephemeral: bool = True
    ) -> None:
        player = (await get_players_by_ids([discord_id]))[0]

        if player.is_empty or not player.switch_fc:
            raise FCNotFound

        await self._send_request_by_fc(ctx, player.switch_fc, ephemeral)


    async def _text_send_request_by_id(
        self,
        ctx: commands.Context,
        discord_id: int
    ) -> None:
        player = (await get_players_by_ids([discord_id]))[0]

        if player.is_empty or not player.switch_fc:
            raise FCNotFound

        await self._text_send_request_by_fc(ctx, player.switch_fc)


    @user_command(name="Friend Request")
    async def send_request(
        self,
        ctx: ApplicationContext,
        member: Member
    ) -> None:
        await ctx.response.defer(ephemeral=True)
        await self._send_request_by_id(ctx, member.id)


    @friend.command(
        name='setup',
        description='Login Nintendo online',
        description_localizations = {'ja': 'Nintendo Onlineにログイン'}
    )
    async def friend_setup(self, ctx: ApplicationContext) -> None:
        await ctx.response.defer(ephemeral=True)
        await send_url(ctx)


    @friend.command(
        name='request',
        description='Send friend request.',
        description_localizations = {'ja': 'フレンド申請'}
    )
    async def friend_request(
        self,
        ctx: ApplicationContext,
        code: Option(
            str,
            name="friend_code",
            name_localizations={'ja': 'フレンドコード'},
            description="Discord ID and Lounge name are also available.",
            description_localizations={'ja': 'Discord IDやラウンジ名も可能'},
            required = False,
            default = "",
        ),
        is_visible: Option(
            str,
            name='visible',
            name_localizations={'ja': '公開'},
            description="Whether to publish or not",
            description_localizations = {'ja': '他の人も申請できるようにするかどうか'},
            choices=[
                OptionChoice(name='Yes', value="..."),
                OptionChoice(name='No', value="")
            ],
            default = "",
            required = False
        )
    ) -> None:
        ephemeral = not bool(is_visible)
        await ctx.response.defer(ephemeral=ephemeral)

        lounge_name, discord_id, fc = maybe_param(code)

        if not code:
            discord_id = ctx.user.id

        if fc:
            await self._send_request_by_fc(ctx, fc, ephemeral)
            return
        elif discord_id is not None:
            await self._send_request_by_id(ctx, discord_id, ephemeral)
            return
        elif lounge_name:
            player = await get_player(name=lounge_name)

            if player.switch_fc and not player.is_empty:
                await self._send_request_by_fc(ctx, player.switch_fc, ephemeral)
                return
            raise FCNotFound

        raise ParamsNotEnough


    @commands.command(
        name="fr",
        description="Send friend request.",
        brief="フレンド申請",
        usage="!fr <friend_code or name or ID  or @mention>",
        hidden=False
    )
    async def fr(
        self,
        ctx: commands.Context,
        *,
        code: str = ''
    ) -> None:
        lounge_name, discord_id, fc = maybe_param(code)

        if not code:
            discord_id = ctx.author.id

        if fc:
            await self._text_send_request_by_fc(ctx, fc)
            return
        elif discord_id is not None:
            await self._text_send_request_by_id(ctx, discord_id)
            return
        elif lounge_name:
            player = await get_player(name=lounge_name)

            if player.switch_fc and not player.is_empty:
                await self._text_send_request_by_fc(ctx, player.switch_fc)
                return
            raise FCNotFound

        raise ParamsNotEnough


    @friend.command(
        name="member",
        description="Send friend request to member in this guild",
        description_localizations={"ja": "サーバー内のメンバーにフレンド申請"}
    )
    @commands.guild_only()
    async def friend_member(
        self,
        ctx: ApplicationContext,
        member: Option(
            Member,
            name="target",
            name_localizations={'ja': 'メンバー'},
            description="Sending to",
            description_localizations = {'ja': '送信先'},
            default = None,
            required = False
        ),
        is_visible: Option(
            str,
            name='visible',
            name_localizations={'ja': '公開'},
            description="Whether to publish or not",
            description_localizations = {'ja': '他の人も申請できるようにするかどうか'},
            choices=[
                OptionChoice(name='Yes', value="..."),
                OptionChoice(name='No', value="")
            ],
            default = "",
            required = False
        )
    ) -> None:

        if member is None:
            member = ctx.user

        ephemeral = not bool(is_visible)
        await ctx.response.defer(ephemeral=ephemeral)
        await self._send_request_by_id(ctx, member.id, ephemeral)



    @friend.command(
        name='code',
        description='Show your friend code.',
        description_localizations={'ja': '自分のフレンドコードを表示'}
    )
    async def friend_code(
        self,
        ctx: ApplicationContext,
        is_visible: Option(
            str,
            name='visible',
            name_localizations={'ja': '公開'},
            description="Whether to publish or not",
            description_localizations = {'ja': '他の人も申請できるようにするかどうか'},
            choices=[
                OptionChoice(name='Yes', value="..."),
                OptionChoice(name='No', value="")
            ],
            default = "",
            required = False
        )
    ) -> None:
        ephemeral = not bool(is_visible)
        await ctx.response.defer(ephemeral=ephemeral)
        await self._send_request_by_id(ctx, ctx.user.id, ephemeral)
        return


    @friend.command(
        name="multiple",
        description="Apply multiple requests.",
        description_localizations={"ja": "複数のフレンド申請"}
    )
    async def friend_multiple(
        self,
        ctx: ApplicationContext,
        text: Option(
            str,
            name="text",
            name_localizations={"ja": "フレンドコードが含まれる文"},
            description="Only expression like 0000-0000-0000 is valid",
            description_localizations={"ja": "0000-0000-0000の形式のみ読みとります"},
            required=True
        ),
        is_visible: Option(
            str,
            name='visible',
            name_localizations={'ja': '公開'},
            description="Whether to publish or not",
            description_localizations = {'ja': '他の人も申請できるようにするかどうか'},
            choices=[
                OptionChoice(name='Yes', value="..."),
                OptionChoice(name='No', value="")
            ],
            default = "",
            required = False
        )
    ) -> None:
        ephemeral = not bool(is_visible)
        await ctx.response.defer(ephemeral=ephemeral)
        await _multiple_requests(ctx, text, ephemeral)


    @friend.command(
        name="mmr",
        description="Search MMRs by friend codes.",
        description_localizations = {"ja": "フレンドコードでMMRを一括検索"}
    )
    async def friend_mmr(
        self,
        ctx: ApplicationContext,
        text: Option(
            str,
            name="friend_codes",
            name_localizations={"ja": "フレンドコード"},
            description="0000-0000-0000 format will be detected.",
            description_localizations={"ja": "フレンドコードが含まれる文章を入力してください。(0000-0000-0000形式)"},
            required=True,
        ),
        ascending: Option(
            str,
            name="order",
            name_localizations={"ja": "順序"},
            description="Sort according to MMR",
            description_localizations={"ja": "MMRで並び替え"},
            choices=[
                OptionChoice(
                    name="ascending-order",
                    name_localizations={"ja": "高い順"},
                    value="ascending"
                ),
                OptionChoice(
                    name="descending-order",
                    name_localizations={"ja": "低い順"},
                    value="descending"
                ),
                OptionChoice(
                    name="default",
                    name_localizations={"ja": "そのまま"},
                    value=""
                )
            ],
            required=False,
            default=""
        ),
        view_original: Option(
            str,
            name="original_text",
            name_localizations={"ja": "もとのテキスト"},
            description="Whether or not display original text.",
            description_localizations={"ja": "もとのテキストを表示させるかどうか"},
            default="...",
            required=False,
            choices=[
                OptionChoice(name="Yes", name_localizations={"ja": "表示"}, value="..."),
                OptionChoice(name="No", name_localizations={"ja": "非表示"}, value="")
            ]
        )
    ) -> None:
        await ctx.response.defer()
        await fm(ctx, text, None if ascending=="" else ascending=="descending-order", bool(view_original))


    @friend.command(
        name="peak_mmr",
        description="Search Peak MMRs by friend codes.",
        description_localizations = {"ja": "フレンドコードでPeak MMRを一括検索"}
    )
    async def friend_peak_mmr(
        self,
        ctx: ApplicationContext,
        text: Option(
            str,
            name="friend_codes",
            name_localizations={"ja": "フレンドコード"},
            description="0000-0000-0000 format will be detected.",
            description_localizations={"ja": "フレンドコードが含まれる文章を入力してください。(0000-0000-0000形式)"},
            required=True,
        ),
        ascending: Option(
            str,
            name="order",
            name_localizations={"ja": "順序"},
            description="Sort according to MMR",
            description_localizations={"ja": "MMRで並び替え"},
            choices=[
                OptionChoice(
                    name="ascending-order",
                    name_localizations={"ja": "高い順"},
                    value="ascending"
                ),
                OptionChoice(
                    name="descending-order",
                    name_localizations={"ja": "低い順"},
                    value="descending"
                ),
                OptionChoice(
                    name="default",
                    name_localizations={"ja": "そのまま"},
                    value=""
                )
            ],
            required=False,
            default=""
        ),
        view_original: Option(
            str,
            name="original_text",
            name_localizations={"ja": "もとのテキスト"},
            description="Whether or not display original text.",
            description_localizations={"ja": "もとのテキストを表示させるかどうか"},
            default="...",
            required=False,
            choices=[
                OptionChoice(name="Yes", name_localizations={"ja": "表示"}, value="..."),
                OptionChoice(name="No", name_localizations={"ja": "非表示"}, value="")
            ]
        )
    ) -> None:
        await ctx.response.defer()
        await peak(ctx, text, None if ascending=="" else ascending=="descending-order", bool(view_original))


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Friend(bot))

